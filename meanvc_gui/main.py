"""Main MeanVC GUI Application."""

import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QLabel,
    QSplitter,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap

from meanvc_gui.components.theme import COLORS, get_dark_palette, get_nav_style
from meanvc_gui.pages.library import LibraryPage
from meanvc_gui.pages.realtime import RealtimePage
from meanvc_gui.pages.offline import OfflinePage
from meanvc_gui.pages.analysis import AnalysisPage
from meanvc_gui.pages.settings import SettingsPage


class MeanVCWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        """Initialize main window."""
        super().__init__()

        self.setWindowTitle("MeanVC")
        self.setGeometry(100, 100, 1200, 800)

        # Apply dark theme
        self.setPalette(get_dark_palette())
        self.setStyleSheet(self._get_stylesheet())

        # Current active profile for conversion
        self.current_profile = None

        # Setup UI
        self._setup_ui()

        # Show first page
        self._on_nav_change(0)

    def _get_stylesheet(self):
        """Get application stylesheet."""
        return f"""
        QMainWindow {{
            background-color: {COLORS["background"]};
        }}
        QWidget {{
            color: {COLORS["text"]};
        }}
        QGroupBox {{
            border: 1px solid {COLORS["border"]};
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 12px;
            font-weight: bold;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 5px;
            color: {COLORS["text_secondary"]};
        }}
        QLabel {{
            color: {COLORS["text"]};
        }}
        QLineEdit {{
            background-color: {COLORS["surface"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 4px;
            padding: 6px;
            color: {COLORS["text"]};
        }}
        QLineEdit:focus {{
            border: 1px solid {COLORS["primary"]};
        }}
        QComboBox {{
            background-color: {COLORS["surface"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 4px;
            padding: 6px;
            color: {COLORS["text"]};
        }}
        QComboBox::drop-down {{
            border: none;
        }}
        QComboBox QAbstractItemView {{
            background-color: {COLORS["surface"]};
            color: {COLORS["text"]};
            selection-background-color: {COLORS["surface_variant"]};
        }}
        QSlider::groove:horizontal {{
            background: {COLORS["surface_variant"]};
            height: 4px;
            border-radius: 2px;
        }}
        QSlider::handle:horizontal {{
            background: {COLORS["primary"]};
            width: 14px;
            margin: -5px 0;
            border-radius: 7px;
        }}
        QProgressBar {{
            background-color: {COLORS["surface_variant"]};
            border: none;
            border-radius: 4px;
            text-align: center;
            color: {COLORS["text"]};
        }}
        QProgressBar::chunk {{
            background-color: {COLORS["primary"]};
            border-radius: 4px;
        }}
        QListWidget {{
            background-color: {COLORS["surface"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 4px;
            color: {COLORS["text"]};
        }}
        QListWidget::item {{
            padding: 8px;
            border-radius: 4px;
        }}
        QListWidget::item:selected {{
            background-color: {COLORS["primary_dark"]};
            color: {COLORS["text"]};
        }}
        QTableWidget {{
            background-color: {COLORS["surface"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 4px;
            color: {COLORS["text"]};
        }}
        QHeaderView::section {{
            background-color: {COLORS["surface_variant"]};
            color: {COLORS["text"]};
            padding: 6px;
            border: none;
        }}
        QPushButton {{
            background-color: {COLORS["surface_variant"]};
            color: {COLORS["text"]};
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
        }}
        QPushButton:hover {{
            background-color: {COLORS["border"]};
        }}
        """

    def _setup_ui(self):
        """Setup the UI."""
        # Central widget with splitter
        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Navigation sidebar
        self.nav_list = QListWidget()
        self.nav_list.setMaximumWidth(180)
        self.nav_list.addItems(
            ["Library", "Realtime", "Offline", "Analysis", "Settings"]
        )
        self.nav_list.setCurrentRow(0)
        self.nav_list.currentRowChanged.connect(self._on_nav_change)
        self.nav_list.setStyleSheet(get_nav_style())

        layout.addWidget(self.nav_list)

        # Divider
        divider = QWidget()
        divider.setFixedWidth(1)
        divider.setStyleSheet(f"background-color: {COLORS['border']};")
        layout.addWidget(divider)

        # Content area
        self.content_stack = QWidget()
        self.content_layout = QVBoxLayout(self.content_stack)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.content_stack, 1)

        # Initialize pages
        self.pages = [
            LibraryPage(self),
            RealtimePage(self),
            OfflinePage(self),
            AnalysisPage(self),
            SettingsPage(self),
        ]

        # Hide all pages initially
        for page in self.pages:
            page.hide()

    def _on_nav_change(self, index):
        """Handle navigation change.

        Args:
            index: Selected page index
        """
        # Hide all pages
        for page in self.pages:
            page.hide()

        # Show selected page
        if 0 <= index < len(self.pages):
            self.pages[index].show()
            self.content_layout.addWidget(self.pages[index], 1)


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MeanVCWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
