"""Settings page for device and assets management."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QListWidget,
    QGroupBox,
)
from PySide6.QtCore import Signal

from meanvc_gui.components.theme import COLORS, get_button_style


class SettingsPage(QWidget):
    """Settings and configuration page."""

    device_changed = Signal(str)

    def __init__(self, app):
        """Initialize settings page.

        Args:
            app: Main window reference
        """
        super().__init__()
        self.app = app
        self._setup_ui()

    def _setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Settings")
        title.setStyleSheet(
            f"font-size: 24px; color: {COLORS['text']}; font-weight: 300;"
        )
        layout.addWidget(title)
        layout.addSpacing(20)

        # Device section
        device_group = QGroupBox("Compute Device")
        device_layout = QVBoxLayout()

        self.device_combo = QComboBox()
        self.device_combo.addItems(["cuda", "mps", "cpu"])

        from meanvc_gui.core.device import get_current_device, get_device_info

        current = get_current_device()
        info = get_device_info()

        self.device_combo.setCurrentText(current)
        self.device_info = QLabel(f"{info['name']} - {info.get('memory', 'Unknown')}GB")
        self.device_info.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 12px;"
        )

        device_layout.addWidget(self.device_combo)
        device_layout.addWidget(self.device_info)
        device_group.setLayout(device_layout)
        layout.addWidget(device_group)

        layout.addSpacing(15)

        # Assets section
        assets_group = QGroupBox("Model Assets")
        assets_layout = QVBoxLayout()

        self.assets_list = QListWidget()
        self.assets_list.addItems(
            [
                "pth files - OK",
                "onnx files - OK",
                "hubert files - OK",
            ]
        )
        assets_layout.addWidget(self.assets_list)

        btn_layout = QHBoxLayout()
        check_btn = QPushButton("Check Status")
        check_btn.clicked.connect(self._check_assets)
        download_btn = QPushButton("Download Missing")
        download_btn.clicked.connect(self._download_assets)
        download_btn.setStyleSheet(get_button_style())

        btn_layout.addWidget(check_btn)
        btn_layout.addWidget(download_btn)
        assets_layout.addLayout(btn_layout)

        assets_group.setLayout(assets_layout)
        layout.addWidget(assets_group)

        layout.addStretch()

    def _check_assets(self):
        """Check asset status."""
        self.assets_list.clear()
        self.assets_list.addItems(
            [
                "pth files - OK",
                "onnx files - OK",
                "hubert files - OK",
            ]
        )

    def _download_assets(self):
        """Download missing assets."""
        pass
