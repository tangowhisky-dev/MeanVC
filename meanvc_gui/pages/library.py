"""Library page — voice profile management.

Full CRUD: create, rename, delete profiles; upload audio with WavLM
embedding extraction; set default reference; export/import zip.
"""

from __future__ import annotations

import os

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from meanvc_gui.components.theme import (
    COLORS,
    CardFrame,
    DangerButton,
    PrimaryButton,
    SecondaryButton,
    SecondaryLabel,
    SectionTitle,
    StatusBadge,
)
from meanvc_gui.core.device import get_current_device
from meanvc_gui.core.profile_manager import EmbeddingWorker, get_profile_manager


# ---------------------------------------------------------------------------
# Profile card widget
# ---------------------------------------------------------------------------

class ProfileCard(QFrame):
    """Clickable card showing profile summary."""

    selected = Signal(str)

    def __init__(self, profile: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.profile = profile
        self._selected = False
        self._build()

    def _build(self) -> None:
        self.setFixedHeight(88)
        self.setCursor(Qt.PointingHandCursor)
        self._apply_style(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(6)

        # Row 1: name + duration badge
        row1 = QHBoxLayout()
        name = QLabel(self.profile.get("name", "Untitled"))
        name.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {COLORS['text']}; background: transparent;")
        row1.addWidget(name)
        row1.addStretch()
        duration = self.profile.get("total_audio_duration", 0)
        dur_lbl = QLabel(f"🕐 {duration:.0f}s")
        dur_lbl.setStyleSheet(
            f"font-size: 11px; color: {COLORS['text_secondary']}; "
            f"background: {COLORS['surface_variant']}; "
            "border-radius: 4px; padding: 2px 6px;"
        )
        row1.addWidget(dur_lbl)
        layout.addLayout(row1)

        # Row 2: file count + created date
        row2 = QHBoxLayout()
        n_files = self.profile.get("num_audio_files", 0)
        files_lbl = SecondaryLabel(f"📁 {n_files} file{'s' if n_files != 1 else ''}")
        row2.addWidget(files_lbl)
        row2.addStretch()
        created = self.profile.get("created_at", "")[:10]
        date_lbl = SecondaryLabel(created)
        row2.addWidget(date_lbl)
        layout.addLayout(row2)

    def _apply_style(self, selected: bool) -> None:
        if selected:
            self.setStyleSheet(f"""
                QFrame {{
                    background: rgba(132, 220, 198, 0.15);
                    border: 1px solid {COLORS['primary']};
                    border-radius: 10px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background: {COLORS['surface']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 10px;
                }}
            """)

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._apply_style(selected)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        self.selected.emit(self.profile["id"])
        super().mousePressEvent(event)


# ---------------------------------------------------------------------------
# Library page
# ---------------------------------------------------------------------------

class LibraryPage(QWidget):
    """Voice profile library page."""

    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        self.pm = get_profile_manager()
        self.current_profile: dict | None = None
        self._active_workers: list[EmbeddingWorker] = []
        self._build()
        self._load_profiles()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build(self) -> None:
        # ── Standard outer shell (matches every other page) ────────────
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        # Page title row — same as Offline/Realtime/Analysis/Settings
        title_row = QHBoxLayout()
        title_row.addWidget(SectionTitle("Voice Profiles"))
        title_row.addStretch()
        import_btn = QPushButton("Import")
        import_btn.setFixedHeight(32)
        import_btn.clicked.connect(self._import_profile)
        title_row.addWidget(import_btn)
        add_btn = PrimaryButton("+ New")
        add_btn.setFixedHeight(32)
        add_btn.clicked.connect(self._new_profile)
        title_row.addWidget(add_btn)
        root.addLayout(title_row)

        # ── Body: left sidebar + right detail ──────────────────────────
        body = QHBoxLayout()
        body.setSpacing(16)

        # ---- Left sidebar: scrollable profile card list ----
        sidebar = CardFrame()
        sidebar.setFixedWidth(280)
        sv = QVBoxLayout(sidebar)
        sv.setContentsMargins(12, 12, 12, 12)
        sv.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self._cards_container = QWidget()
        self._cards_container.setStyleSheet("background: transparent;")
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(8)
        self._cards_layout.addStretch()

        scroll.setWidget(self._cards_container)
        sv.addWidget(scroll, 1)
        body.addWidget(sidebar)

        # ---- Right detail area ----
        right = QVBoxLayout()
        right.setSpacing(16)

        # Profile detail card
        detail_card = CardFrame()
        dc = QVBoxLayout(detail_card)
        dc.setContentsMargins(16, 14, 16, 14)
        dc.setSpacing(12)

        detail_header = QHBoxLayout()
        detail_header.addWidget(QLabel("Profile Details"))
        detail_header.addStretch()
        self._export_btn = SecondaryButton("Export")
        self._export_btn.setFixedHeight(30)
        self._export_btn.clicked.connect(self._export_profile)
        self._export_btn.setEnabled(False)
        detail_header.addWidget(self._export_btn)
        self._rename_btn = SecondaryButton("Rename")
        self._rename_btn.setFixedHeight(30)
        self._rename_btn.clicked.connect(self._rename_profile)
        self._rename_btn.setEnabled(False)
        detail_header.addWidget(self._rename_btn)
        self._delete_btn = DangerButton("Delete")
        self._delete_btn.setFixedHeight(30)
        self._delete_btn.clicked.connect(self._delete_profile)
        self._delete_btn.setEnabled(False)
        detail_header.addWidget(self._delete_btn)
        dc.addLayout(detail_header)

        self._detail_rows = QVBoxLayout()
        self._detail_rows.setSpacing(8)
        dc.addLayout(self._detail_rows)

        self._use_btn = PrimaryButton("Use for Conversion")
        self._use_btn.setEnabled(False)
        self._use_btn.clicked.connect(self._use_profile)
        dc.addWidget(self._use_btn)
        right.addWidget(detail_card)

        # Audio files card
        audio_card = CardFrame()
        ac = QVBoxLayout(audio_card)
        ac.setContentsMargins(16, 14, 16, 14)
        ac.setSpacing(12)

        audio_header = QHBoxLayout()
        audio_title = QLabel("Audio Files")
        audio_title.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {COLORS['text']}; background: transparent;")
        audio_header.addWidget(audio_title)
        audio_header.addStretch()
        self._add_audio_btn = PrimaryButton("+ Add Audio")
        self._add_audio_btn.setFixedHeight(30)
        self._add_audio_btn.setEnabled(False)
        self._add_audio_btn.clicked.connect(self._add_audio)
        audio_header.addWidget(self._add_audio_btn)
        ac.addLayout(audio_header)

        self._audio_list = QListWidget()
        self._audio_list.setMinimumHeight(160)
        self._audio_list.itemDoubleClicked.connect(self._on_audio_double_click)
        ac.addWidget(self._audio_list)

        # Per-file action buttons
        file_btns = QHBoxLayout()
        self._set_default_btn = SecondaryButton("Set as Default ★")
        self._set_default_btn.setEnabled(False)
        self._set_default_btn.clicked.connect(self._set_default)
        file_btns.addWidget(self._set_default_btn)
        self._remove_audio_btn = DangerButton("Remove File")
        self._remove_audio_btn.setEnabled(False)
        self._remove_audio_btn.clicked.connect(self._remove_audio)
        file_btns.addWidget(self._remove_audio_btn)
        file_btns.addStretch()
        ac.addLayout(file_btns)
        right.addWidget(audio_card)

        right.addStretch()
        body.addLayout(right, 1)
        root.addLayout(body, 1)

        # Enable per-file buttons when selection changes
        self._audio_list.itemSelectionChanged.connect(self._on_audio_selection)

    # ------------------------------------------------------------------
    # Profile list management
    # ------------------------------------------------------------------

    def _load_profiles(self) -> None:
        """Reload profile cards from DB."""
        # Remove old cards (except the trailing stretch)
        while self._cards_layout.count() > 1:
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        profiles = self.pm.list_profiles()
        for p in profiles:
            card = ProfileCard(p)
            card.selected.connect(self._on_profile_selected)
            self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)

        if profiles:
            if self.current_profile:
                # Re-select same profile if it still exists
                ids = [p["id"] for p in profiles]
                if self.current_profile["id"] in ids:
                    self._on_profile_selected(self.current_profile["id"])
                    return
            self._on_profile_selected(profiles[0]["id"])
        else:
            self.current_profile = None
            self._refresh_detail()
            self._refresh_audio_list()

    def _on_profile_selected(self, profile_id: str) -> None:
        # Update card highlight
        for i in range(self._cards_layout.count()):
            w = self._cards_layout.itemAt(i).widget()
            if isinstance(w, ProfileCard):
                w.set_selected(w.profile["id"] == profile_id)

        self.current_profile = self.pm.get_profile(profile_id)
        self._refresh_detail()
        self._refresh_audio_list()

    # ------------------------------------------------------------------
    # Detail panel
    # ------------------------------------------------------------------

    def _refresh_detail(self) -> None:
        # Clear rows — must handle both widget items and layout items
        while self._detail_rows.count():
            item = self._detail_rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # Clear child widgets from the sub-layout then delete it
                sub = item.layout()
                while sub.count():
                    child = sub.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
                sub.deleteLater()

        has = self.current_profile is not None
        self._export_btn.setEnabled(has)
        self._rename_btn.setEnabled(has)
        self._delete_btn.setEnabled(has)
        self._use_btn.setEnabled(has)
        self._add_audio_btn.setEnabled(has)

        if not has:
            self._detail_rows.addWidget(SecondaryLabel("Select a profile to view details."))
            return

        p = self.current_profile
        for label, value in [
            ("Name",       p.get("name", "")),
            ("Files",      str(p.get("num_audio_files", 0))),
            ("Duration",   f"{p.get('total_audio_duration', 0):.1f}s"),
            ("Created",    p.get("created_at", "")[:19].replace("T", " ")),
        ]:
            row = QHBoxLayout()
            lbl = SecondaryLabel(label)
            lbl.setFixedWidth(80)
            row.addWidget(lbl)
            val = QLabel(value)
            val.setStyleSheet(f"font-size: 13px; color: {COLORS['text']}; background: transparent;")
            row.addWidget(val)
            row.addStretch()
            self._detail_rows.addLayout(row)

    # ------------------------------------------------------------------
    # Audio files panel
    # ------------------------------------------------------------------

    def _refresh_audio_list(self) -> None:
        self._audio_list.clear()
        if not self.current_profile:
            return

        for af in self.current_profile.get("audio_files", []):
            name     = af.get("filename", "unknown")
            dur      = af.get("duration", 0)
            default  = " ★" if af.get("is_default") else ""
            has_emb  = bool(af.get("embedding_path") and os.path.isfile(af["embedding_path"]))
            status   = "ready" if has_emb else "pending"

            item = QListWidgetItem(f"🎵  {name}  ({dur:.1f}s){default}   [{status}]")
            item.setData(Qt.UserRole, af["id"])
            item.setForeground(
                __import__("PySide6.QtGui", fromlist=["QColor"]).QColor(
                    COLORS["success"] if has_emb else COLORS["text_muted"]
                )
            )
            self._audio_list.addItem(item)

    def _on_audio_selection(self) -> None:
        has = len(self._audio_list.selectedItems()) > 0
        self._set_default_btn.setEnabled(has)
        self._remove_audio_btn.setEnabled(has)

    def _on_audio_double_click(self, item: QListWidgetItem) -> None:
        """Double-click on an audio item → set as default."""
        file_id = item.data(Qt.UserRole)
        if file_id:
            self.pm.set_default_audio(file_id)
            self.current_profile = self.pm.get_profile(self.current_profile["id"])
            self._refresh_audio_list()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _new_profile(self) -> None:
        name, ok = QInputDialog.getText(self, "New Profile", "Profile name:")
        if not ok or not name.strip():
            return
        desc, _ = QInputDialog.getText(self, "New Profile", "Description (optional):")
        profile = self.pm.create_profile(name.strip(), desc.strip())
        self._load_profiles()
        self._on_profile_selected(profile["id"])

    def _rename_profile(self) -> None:
        if not self.current_profile:
            return
        name, ok = QInputDialog.getText(
            self, "Rename Profile", "New name:",
            text=self.current_profile["name"],
        )
        if not ok or not name.strip():
            return
        self.pm.update_profile(self.current_profile["id"], name=name.strip())
        self._load_profiles()

    def _delete_profile(self) -> None:
        if not self.current_profile:
            return
        reply = QMessageBox.question(
            self, "Delete Profile",
            f"Delete '{self.current_profile['name']}'? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.pm.delete_profile(self.current_profile["id"])
            self.current_profile = None
            self._load_profiles()

    def _use_profile(self) -> None:
        if not self.current_profile:
            return
        self.app.current_profile = self.current_profile
        # Emit cross-page signal
        from meanvc_gui.main import bus
        bus.profile_selected.emit(self.current_profile)
        QMessageBox.information(
            self, "Profile Set",
            f"'{self.current_profile['name']}' is now the active profile for conversion.",
        )

    def _add_audio(self) -> None:
        if not self.current_profile:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Audio File", "",
            "Audio Files (*.wav *.mp3 *.flac *.ogg *.m4a)",
        )
        if not path:
            return

        is_default = self.current_profile.get("num_audio_files", 0) == 0

        worker = EmbeddingWorker(
            profile_id=self.current_profile["id"],
            source_path=path,
            is_default=is_default,
            device=get_current_device(),
        )
        self._active_workers.append(worker)
        self._add_audio_btn.setEnabled(False)
        self._add_audio_btn.setText("Extracting…")

        worker.finished.connect(self._on_embed_done)
        worker.error.connect(self._on_embed_error)
        worker.start()

    def _on_embed_done(self, audio_file: dict) -> None:
        self._add_audio_btn.setEnabled(True)
        self._add_audio_btn.setText("+ Add Audio")
        self.current_profile = self.pm.get_profile(self.current_profile["id"])
        self._refresh_detail()
        self._refresh_audio_list()
        # Reload cards to update stats
        self._load_profiles()

    def _on_embed_error(self, msg: str) -> None:
        self._add_audio_btn.setEnabled(True)
        self._add_audio_btn.setText("+ Add Audio")
        QMessageBox.warning(self, "Embedding Failed", f"Could not process audio:\n{msg}")

    def _set_default(self) -> None:
        items = self._audio_list.selectedItems()
        if not items:
            return
        file_id = items[0].data(Qt.UserRole)
        self.pm.set_default_audio(file_id)
        self.current_profile = self.pm.get_profile(self.current_profile["id"])
        self._refresh_audio_list()

    def _remove_audio(self) -> None:
        items = self._audio_list.selectedItems()
        if not items:
            return
        file_id = items[0].data(Qt.UserRole)
        reply = QMessageBox.question(
            self, "Remove Audio",
            "Remove this audio file from the profile?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.pm.delete_audio(file_id)
            self.current_profile = self.pm.get_profile(self.current_profile["id"])
            self._refresh_detail()
            self._refresh_audio_list()
            self._load_profiles()

    def _export_profile(self) -> None:
        if not self.current_profile:
            return
        name = self.current_profile["name"].replace(" ", "_")
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Profile", f"{name}.zip",
            "Zip Archives (*.zip)",
        )
        if not path:
            return
        try:
            self.pm.export_profile(self.current_profile["id"], path)
            QMessageBox.information(self, "Exported", f"Profile exported to:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))

    def _import_profile(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Profile", "", "Zip Archives (*.zip)"
        )
        if not path:
            return
        try:
            profile = self.pm.import_profile(path)
            self._load_profiles()
            self._on_profile_selected(profile["id"])
            QMessageBox.information(self, "Imported", f"Profile '{profile['name']}' imported.")
        except Exception as exc:
            QMessageBox.critical(self, "Import Failed", str(exc))
