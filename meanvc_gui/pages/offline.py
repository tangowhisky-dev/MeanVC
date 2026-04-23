"""Offline conversion page — file-to-file voice conversion."""

from __future__ import annotations

import os

from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPlainTextEdit,
    QPushButton,
    QSlider,
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
    get_button_style,
)
from meanvc_gui.core.engine import get_engine
from meanvc_gui.core.profile_manager import get_profile_manager

# Project root for default output dir
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))


# ---------------------------------------------------------------------------
# Background conversion worker
# ---------------------------------------------------------------------------

class ConversionWorker(QThread):
    """Runs engine.convert() off the Qt main thread."""

    progress  = Signal(int, str)   # percent, message
    finished  = Signal(str)        # output path
    error     = Signal(str)        # error message

    def __init__(
        self,
        source_path: str,
        ref_path: str,
        steps: int,
        output_dir: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.source_path = source_path
        self.ref_path    = ref_path
        self.steps       = steps
        self.output_dir  = output_dir
        self._cancelled  = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            engine = get_engine()
            output = engine.convert(
                source_path   = self.source_path,
                ref_path      = self.ref_path,
                steps         = self.steps,
                output_dir    = self.output_dir,
                progress_cb   = lambda pct, msg: self.progress.emit(pct, msg),
                cancelled_cb  = lambda: self._cancelled,
            )
            self.finished.emit(output)
        except Exception as exc:
            self.error.emit(str(exc))


# ---------------------------------------------------------------------------
# Offline page
# ---------------------------------------------------------------------------

class OfflinePage(QWidget):
    """File-based offline voice conversion page."""

    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        self.source_path    = ""
        self.ref_path       = ""
        self.output_path    = ""
        self._worker: ConversionWorker | None = None
        self._player        = QMediaPlayer()
        self._audio_out     = QAudioOutput()
        self._player.setAudioOutput(self._audio_out)
        self._build()
        self._subscribe()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        root.addWidget(SectionTitle("Offline Conversion"))

        # ---- Profile picker ----
        profile_card = CardFrame()
        pc = QVBoxLayout(profile_card)
        pc.setContentsMargins(16, 14, 16, 14)
        pc.setSpacing(8)
        pc.addWidget(QLabel("Target Profile"))
        profile_row = QHBoxLayout()
        self._profile_combo = QComboBox()
        self._profile_combo.setPlaceholderText("Select a voice profile…")
        profile_row.addWidget(self._profile_combo, 1)
        refresh_btn = QPushButton("↺")
        refresh_btn.setFixedSize(32, 32)
        refresh_btn.setToolTip("Refresh profile list")
        refresh_btn.clicked.connect(self._populate_profiles)
        profile_row.addWidget(refresh_btn)
        pc.addLayout(profile_row)
        root.addWidget(profile_card)

        # ---- File inputs ----
        files_card = CardFrame()
        fc = QVBoxLayout(files_card)
        fc.setContentsMargins(16, 14, 16, 14)
        fc.setSpacing(10)
        fc.addWidget(QLabel("Source Audio"))

        # Source
        src_row = QHBoxLayout()
        self._src_label = QLabel("No file selected")
        self._src_label.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent;")
        src_row.addWidget(self._src_label, 1)
        src_btn = QPushButton("Browse…")
        src_btn.clicked.connect(self._pick_source)
        src_row.addWidget(src_btn)
        fc.addLayout(src_row)
        root.addWidget(files_card)

        # ---- Settings ----
        settings_card = CardFrame()
        sc = QVBoxLayout(settings_card)
        sc.setContentsMargins(16, 14, 16, 14)
        sc.setSpacing(10)

        # Steps
        steps_row = QHBoxLayout()
        steps_row.addWidget(QLabel("Denoising Steps"))
        self._steps_slider = QSlider(Qt.Horizontal)
        self._steps_slider.setMinimum(1)
        self._steps_slider.setMaximum(4)
        self._steps_slider.setValue(2)
        self._steps_slider.setTickPosition(QSlider.TicksBelow)
        self._steps_slider.setTickInterval(1)
        steps_row.addWidget(self._steps_slider, 1)
        self._steps_label = QLabel("2")
        self._steps_label.setFixedWidth(20)
        steps_row.addWidget(self._steps_label)
        self._steps_slider.valueChanged.connect(
            lambda v: self._steps_label.setText(str(v))
        )
        sc.addLayout(steps_row)

        # Output directory
        out_row = QHBoxLayout()
        default_out = os.path.join(_PROJECT_ROOT, "meanvc_out")
        self._out_label = QLabel(default_out)
        self._out_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; background: transparent;")
        out_row.addWidget(QLabel("Output Dir"))
        out_row.addWidget(self._out_label, 1)
        out_pick = QPushButton("…")
        out_pick.setFixedSize(32, 32)
        out_pick.clicked.connect(self._pick_output_dir)
        out_row.addWidget(out_pick)
        sc.addLayout(out_row)
        self._output_dir = default_out
        root.addWidget(settings_card)

        # ---- Action buttons ----
        action_row = QHBoxLayout()
        self._convert_btn = PrimaryButton("Convert")
        self._convert_btn.clicked.connect(self._start_conversion)
        action_row.addWidget(self._convert_btn)
        self._cancel_btn = SecondaryButton("Cancel")
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._cancel_conversion)
        action_row.addWidget(self._cancel_btn)
        action_row.addStretch()
        root.addLayout(action_row)

        # ---- Progress ----
        self._progress_bar = QProgressBar()
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(6)
        root.addWidget(self._progress_bar)

        # Log area — selectable, copy-pasteable
        log_header = QHBoxLayout()
        log_header.setSpacing(8)
        log_header.addWidget(QLabel("Logs:"))
        self._clear_log_btn = QPushButton("Clear")
        self._clear_log_btn.setMaximumWidth(60)
        self._clear_log_btn.clicked.connect(lambda: self._log_edit.clear())
        log_header.addWidget(self._clear_log_btn)
        log_header.addStretch()
        root.addLayout(log_header)

        self._log_edit = QPlainTextEdit()
        self._log_edit.setReadOnly(True)
        self._log_edit.setMinimumHeight(60)
        self._log_edit.setMaximumHeight(200)
        self._log_edit.setStyleSheet(
            "font-size: 12px; font-family: monospace; background: transparent; color: #aaa; border: none; padding: 4px;"
        )
        self._log_edit.setPlaceholderText("Conversion logs will appear here…")
        root.addWidget(self._log_edit)
        self._phase_label = SecondaryLabel("")
        root.addWidget(self._phase_label)

        # ---- Result card ----
        self._result_card = CardFrame()
        self._result_card.hide()
        rc = QVBoxLayout(self._result_card)
        rc.setContentsMargins(16, 14, 16, 14)
        rc.setSpacing(10)
        rc.addWidget(QLabel("Conversion Complete ✓"))
        self._result_path_label = SecondaryLabel("")
        rc.addWidget(self._result_path_label)
        play_row = QHBoxLayout()
        self._play_btn = PrimaryButton("▶ Play")
        self._play_btn.clicked.connect(self._toggle_play)
        play_row.addWidget(self._play_btn)
        self._send_analysis_btn = SecondaryButton("→ Analysis")
        self._send_analysis_btn.setToolTip("Open in Analysis page for similarity check")
        self._send_analysis_btn.clicked.connect(self._send_to_analysis)
        play_row.addWidget(self._send_analysis_btn)
        play_row.addStretch()
        rc.addLayout(play_row)
        root.addWidget(self._result_card)

        root.addStretch()

        # Connect player state to button text
        self._player.playbackStateChanged.connect(self._on_playback_state)

    def _subscribe(self) -> None:
        """Subscribe to cross-page bus events."""
        try:
            from meanvc_gui.main import bus
            bus.profile_selected.connect(self._on_profile_selected)
        except Exception:
            pass
        self._populate_profiles()

    # ------------------------------------------------------------------
    # Profile combo
    # ------------------------------------------------------------------

    def _populate_profiles(self) -> None:
        pm = get_profile_manager()
        profiles = pm.list_profiles()
        self._profile_combo.clear()
        for p in profiles:
            self._profile_combo.addItem(p["name"], p["id"])
        # Pre-select app.current_profile if set
        if hasattr(self.app, "current_profile") and self.app.current_profile:
            pid = self.app.current_profile["id"]
            for i in range(self._profile_combo.count()):
                if self._profile_combo.itemData(i) == pid:
                    self._profile_combo.setCurrentIndex(i)
                    break

    def _on_profile_selected(self, profile: dict) -> None:
        pid = profile["id"]
        for i in range(self._profile_combo.count()):
            if self._profile_combo.itemData(i) == pid:
                self._profile_combo.setCurrentIndex(i)
                return
        # Not yet in combo — refresh
        self._populate_profiles()

    # ------------------------------------------------------------------
    # File pickers
    # ------------------------------------------------------------------

    def _pick_source(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Source Audio", "",
            "Audio Files (*.wav *.mp3 *.flac *.ogg *.m4a)",
        )
        if path:
            self.source_path = path
            self._src_label.setText(os.path.basename(path))
            self._src_label.setStyleSheet(f"color: {COLORS['text']}; background: transparent;")

    def _pick_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if path:
            self._output_dir = path
            self._out_label.setText(path)

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    def _get_ref_path(self) -> str | None:
        """Return reference audio path from selected profile."""
        idx = self._profile_combo.currentIndex()
        if idx < 0:
            return None
        profile_id = self._profile_combo.itemData(idx)
        pm = get_profile_manager()
        ref = pm.get_default_reference(profile_id)
        if ref and ref.get("file_path") and os.path.isfile(ref["file_path"]):
            return ref["file_path"]
        return None

    def _start_conversion(self) -> None:
        if not self.source_path:
            self._phase_label.setText("Please select a source audio file.")
            return

        ref_path = self._get_ref_path()
        if not ref_path:
            self._phase_label.setText("Please select a profile with at least one audio file.")
            return

        self.ref_path = ref_path
        steps = self._steps_slider.value()

        self._convert_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)
        self._progress_bar.setValue(0)
        self._result_card.hide()
        self._log_edit.appendPlainText("[INFO] Starting conversion…")

        self._worker = ConversionWorker(
            source_path = self.source_path,
            ref_path    = self.ref_path,
            steps       = steps,
            output_dir  = self._output_dir,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _cancel_conversion(self) -> None:
        if self._worker:
            self._worker.cancel()
        self._convert_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._phase_label.setText("Cancelled.")

    def _on_progress(self, pct: int, msg: str) -> None:
        self._progress_bar.setValue(pct)
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_edit.appendPlainText(f"[{ts}] {pct}% — {msg}")
        self._phase_label.setText(msg)
        # Auto-scroll to bottom
        scrollbar = self._log_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_finished(self, output_path: str) -> None:
        self.output_path = output_path
        self._convert_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._progress_bar.setValue(100)
        self._phase_label.setText("Complete ✓")
        self._result_path_label.setText(output_path)
        self._result_card.show()
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_edit.appendPlainText(f"[{ts}] 100% — Complete ✓")
        # Emit to analysis page
        try:
            from meanvc_gui.main import bus
            bus.analysis_requested.emit(output_path)
        except Exception:
            pass

    def _on_error(self, msg: str) -> None:
        self._convert_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._phase_label.setText(f"Error: {msg}")
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_edit.appendPlainText(f"[{ts}] ERROR: {msg}")

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------

    def _toggle_play(self) -> None:
        if self._player.playbackState() == QMediaPlayer.PlayingState:
            self._player.pause()
        else:
            if self.output_path and os.path.isfile(self.output_path):
                self._player.setSource(QUrl.fromLocalFile(self.output_path))
            self._player.play()

    def _on_playback_state(self, state) -> None:
        if state == QMediaPlayer.PlayingState:
            self._play_btn.setText("⏸ Pause")
        else:
            self._play_btn.setText("▶ Play")

    def _send_to_analysis(self) -> None:
        if self.output_path:
            try:
                from meanvc_gui.main import bus
                bus.analysis_requested.emit(self.output_path)
                bus.navigate_to.emit(3)  # Analysis page index
            except Exception:
                pass
