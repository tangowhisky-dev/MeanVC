"""Settings page — device config and asset management."""

from __future__ import annotations

import os
import subprocess
import sys

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from meanvc_gui.components.theme import (
    COLORS,
    CardFrame,
    PrimaryButton,
    SecondaryLabel,
    SectionTitle,
)
from meanvc_gui.core.device import get_current_device, get_device_info
from meanvc_gui.core.engine import check_assets

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))


# ---------------------------------------------------------------------------
# Download worker
# ---------------------------------------------------------------------------

class DownloadWorker(QThread):
    """Runs download_ckpt.py in a subprocess, forwarding output lines."""

    line     = Signal(str)
    finished = Signal()
    error    = Signal(str)

    def run(self) -> None:
        script = os.path.join(_PROJECT_ROOT, "download_ckpt.py")
        try:
            proc = subprocess.Popen(
                [sys.executable, script],
                cwd=_PROJECT_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            for line in proc.stdout:  # type: ignore[union-attr]
                self.line.emit(line.rstrip())
            proc.wait()
            if proc.returncode != 0:
                self.error.emit(f"download_ckpt.py exited with code {proc.returncode}")
            else:
                self.finished.emit()
        except Exception as exc:
            self.error.emit(str(exc))


# ---------------------------------------------------------------------------
# Settings page
# ---------------------------------------------------------------------------

class SettingsPage(QWidget):
    """Device and asset settings page."""

    device_changed = Signal(str)

    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        self._downloader: DownloadWorker | None = None
        self._build()
        self._refresh_assets()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        root.addWidget(SectionTitle("Settings"))

        # ---- Compute Device ----
        device_card = CardFrame()
        dc = QVBoxLayout(device_card)
        dc.setContentsMargins(16, 14, 16, 14)
        dc.setSpacing(8)
        dc.addWidget(QLabel("Compute Device"))

        info = get_device_info()
        current_device = get_current_device()

        device_row = QHBoxLayout()
        self._device_combo = QComboBox()
        self._device_combo.addItems(["auto", "cuda", "mps", "cpu"])
        self._device_combo.setCurrentText(current_device)
        device_row.addWidget(self._device_combo, 1)
        apply_btn = QPushButton("Apply")
        apply_btn.setFixedWidth(80)
        apply_btn.clicked.connect(self._apply_device)
        device_row.addWidget(apply_btn)
        dc.addLayout(device_row)

        dev_name = info.get("name", current_device)
        mem = info.get("memory")
        mem_str = f" — {mem:.1f} GB" if isinstance(mem, float) else ""
        dc.addWidget(SecondaryLabel(f"{dev_name}{mem_str}"))
        root.addWidget(device_card)

        # ---- Model Assets ----
        assets_card = CardFrame()
        ac = QVBoxLayout(assets_card)
        ac.setContentsMargins(16, 14, 16, 14)
        ac.setSpacing(10)

        assets_header = QHBoxLayout()
        assets_header.addWidget(QLabel("Model Assets"))
        assets_header.addStretch()
        refresh_btn = QPushButton("↺ Refresh")
        refresh_btn.setFixedHeight(30)
        refresh_btn.clicked.connect(self._refresh_assets)
        assets_header.addWidget(refresh_btn)
        self._download_btn = PrimaryButton("Download Missing")
        self._download_btn.setFixedHeight(30)
        self._download_btn.clicked.connect(self._start_download)
        assets_header.addWidget(self._download_btn)
        ac.addLayout(assets_header)

        self._assets_list = QListWidget()
        self._assets_list.setMaximumHeight(180)
        ac.addWidget(self._assets_list)

        # Download log
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(120)
        self._log.setStyleSheet(
            f"background: {COLORS['surface_variant']}; color: {COLORS['text_muted']}; "
            f"font-family: monospace; font-size: 11px; border: none;"
        )
        self._log.hide()
        ac.addWidget(self._log)

        root.addWidget(assets_card)
        root.addStretch()

    # ------------------------------------------------------------------
    # Asset status
    # ------------------------------------------------------------------

    def _refresh_assets(self) -> None:
        self._assets_list.clear()
        results = check_assets()
        any_missing = False

        for name, info in results.items():
            exists  = info["exists"]
            size    = f" ({info['size_mb']:.0f} MB)" if exists else ""
            status  = "✓" if exists else "✗ missing"
            desc    = info["description"]
            text    = f"{status}  {desc}{size}"

            item = QListWidgetItem(text)
            item.setForeground(
                __import__("PySide6.QtGui", fromlist=["QColor"]).QColor(
                    COLORS["success"] if exists else COLORS["error"]
                )
            )
            self._assets_list.addItem(item)
            if not exists:
                any_missing = True

        self._download_btn.setEnabled(any_missing)

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    def _start_download(self) -> None:
        if self._downloader and self._downloader.isRunning():
            return
        self._log.clear()
        self._log.show()
        self._download_btn.setEnabled(False)
        self._download_btn.setText("Downloading…")

        self._downloader = DownloadWorker()
        self._downloader.line.connect(self._on_download_line)
        self._downloader.finished.connect(self._on_download_done)
        self._downloader.error.connect(self._on_download_error)
        self._downloader.start()

    def _on_download_line(self, line: str) -> None:
        self._log.appendPlainText(line)
        # Scroll to bottom
        sb = self._log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_download_done(self) -> None:
        self._download_btn.setText("Download Missing")
        self._log.appendPlainText("\n✓ Download complete.")
        self._refresh_assets()

    def _on_download_error(self, msg: str) -> None:
        self._download_btn.setEnabled(True)
        self._download_btn.setText("Download Missing")
        self._log.appendPlainText(f"\n✗ Error: {msg}")
        self._refresh_assets()
        QMessageBox.warning(self, "Download Failed", msg)

    # ------------------------------------------------------------------
    # Device
    # ------------------------------------------------------------------

    def _apply_device(self) -> None:
        device = self._device_combo.currentText()
        import os
        os.environ["MEANVC_DEVICE"] = device
        self.device_changed.emit(device)
        QMessageBox.information(
            self, "Device Updated",
            f"Device set to '{device}'. Restart the app for changes to take full effect.",
        )
