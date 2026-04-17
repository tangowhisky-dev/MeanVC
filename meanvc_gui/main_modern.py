"""Main application window with modern design."""

import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QStackedWidget,
    QLabel,
    QFrame,
)
from PySide6.QtCore import Qt, QSize, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QIcon, QColor, QLinearGradient, QBrush

from meanvc_gui.components.modern_theme import (
    get_theme_stylesheet,
    get_theme_manager,
    _LIGHT_COLORS,
    _DARK_COLORS,
)


class ModernNavItem(QFrame):
    """Modern navigation item with hover effects."""

    clicked = Signal(int)

    def __init__(self, icon: str, text: str, index: int, parent=None):
        super().__init__(parent)
        self._index = index
        self._icon = icon
        self._text = text
        self._selected = False
        self._setup_ui()

    def _setup_ui(self):
        from PySide6.QtWidgets import QHBoxLayout, QLabel
        from PySide6.QtCore import Qt

        self.setFixedHeight(48)
        self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        self.icon_label = QLabel(self._icon)
        self.icon_label.setStyleSheet("font-size: 18px;")
        layout.addWidget(self.icon_label)

        self.text_label = QLabel(self._text)
        self.text_label.setStyleSheet("font-size: 14px; font-weight: 500;")
        layout.addWidget(self.text_label)

        self.setStyleSheet("""
            QFrame {
                background: transparent;
                border-radius: 8px;
            }
        """)

    def set_selected(self, selected: bool):
        self._selected = selected
        self._update_style()

    def _update_style(self):
        colors = _DARK_COLORS  # Would be dynamic based on theme
        if self._selected:
            self.setStyleSheet(f"""
                QFrame {{
                    background: {colors["primary_container"]};
                    color: {colors["primary"]};
                    border-radius: 8px;
                }}
            """)
            self.text_label.setStyleSheet(
                f"font-size: 14px; font-weight: 600; color: {colors['primary']};"
            )
        else:
            self.setStyleSheet("""
                QFrame {
                    background: transparent;
                    border-radius: 8px;
                }
            """)
            self.text_label.setStyleSheet(
                "font-size: 14px; font-weight: 500; color: #a1aaae;"
            )

    def enterEvent(self, event):
        if not self._selected:
            self.setStyleSheet("""
                QFrame {
                    background: #22d3ee1a;
                    border-radius: 8px;
                }
            """)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._update_style()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self.clicked.emit(self._index)


class ModernSidebar(QFrame):
    """Modern sidebar navigation."""

    navigation_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_index = 0
        self._setup_ui()

    def _setup_ui(self):
        from PySide6.QtWidgets import QVBoxLayout, QLabel
        from PySide6.QtCore import Qt

        colors = _DARK_COLORS

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 20, 12, 20)
        layout.setSpacing(4)

        # Logo/Title
        title = QLabel("⬡ MeanVC")
        title.setStyleSheet(f"""
            font-size: 22px;
            font-weight: 700;
            color: {colors["primary"]};
            padding: 8px 16px;
        """)
        layout.addWidget(title)

        layout.addSpacing(24)

        # Navigation items
        nav_items = [
            ("🎤", "Library", 0),
            ("🔴", "Realtime", 1),
            ("📁", "Offline", 2),
            ("📊", "Analysis", 3),
            ("⚙️", "Settings", 4),
        ]

        self.nav_items = []
        for icon, text, idx in nav_items:
            item = ModernNavItem(icon, text, idx)
            item.clicked.connect(self._on_item_clicked)
            self.nav_items.append(item)
            layout.addWidget(item)

        # Select first item
        self.nav_items[0].set_selected(True)

        layout.addStretch()

        # Version info
        version = QLabel("v0.1.0")
        version.setStyleSheet(f"""
            font-size: 11px;
            color: {colors["text_tertiary"]};
            padding: 8px;
        """)
        layout.addWidget(version)

        self.setStyleSheet(f"""
            QFrame {{
                background: {colors["surface_card"]};
                border-right: 1px solid {colors["border"]};
                width: 220px;
            }}
        """)

    def _on_item_clicked(self, index):
        self.nav_items[self._selected_index].set_selected(False)
        self._selected_index = index
        self.nav_items[index].set_selected(True)
        self.navigation_changed.emit(index)


class ModernHeader(QFrame):
    """Modern header with theme toggle."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton
        from PySide6.QtCore import Qt

        colors = _DARK_COLORS

        self.setFixedHeight(60)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 0)

        # Title
        self.title = QLabel("Voice Profiles")
        self.title.setStyleSheet(f"""
            font-size: 20px;
            font-weight: 600;
            color: {colors["text_primary"]};
        """)
        layout.addWidget(self.title)

        layout.addStretch()

        # Theme toggle
        theme_btn = QPushButton("🌙")
        theme_btn.setFixedSize(36, 36)
        theme_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #27272a;
                border-radius: 8px;
                font-size: 16px;
            }
            QPushButton:hover {
                background: #22d3ee1a;
                border-color: #22d3ee;
            }
        """)
        layout.addWidget(theme_btn)

        self.setStyleSheet(f"""
            QFrame {{
                background: {colors["surface_card"]};
                border-bottom: 1px solid {colors["border"]};
            }}
        """)


class MeanVCWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("MeanVC")
        self.setGeometry(100, 100, 1280, 800)
        self.setMinimumSize(900, 600)

        # Apply theme
        self.setStyleSheet(get_theme_stylesheet("dark"))
        self._apply_palette()

        # Setup UI
        self._setup_ui()

        # Initialize pages
        self._init_pages()

    def _apply_palette(self):
        """Apply color palette."""
        colors = _DARK_COLORS
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(colors["bg_primary"]))
        palette.setColor(self.foregroundRole(), QColor(colors["text_primary"]))
        self.setPalette(palette)

    def _setup_ui(self):
        """Setup main UI."""
        from PySide6.QtWidgets import QHBoxLayout

        # Main layout
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Central widget
        central = QWidget()
        central.setLayout(main_layout)
        self.setCentralWidget(central)

        # Sidebar
        self.sidebar = ModernSidebar()
        self.sidebar.navigation_changed.connect(self._on_navigation_changed)
        main_layout.addWidget(self.sidebar)

        # Content area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Header
        self.header = ModernHeader()
        content_layout.addWidget(self.header)

        # Page stack
        self.page_stack = QStackedWidget()
        content_layout.addWidget(self.page_stack)

        main_layout.addWidget(content_widget, 1)

    def _init_pages(self):
        """Initialize page widgets."""
        from meanvc_gui.pages.library import LibraryPage
        from meanvc_gui.pages.realtime import RealtimePage
        from meanvc_gui.pages.offline import OfflinePage
        from meanvc_gui.pages.analysis import AnalysisPage
        from meanvc_gui.pages.settings import SettingsPage

        # Create pages
        self.pages = [
            LibraryPage(self),
            RealtimePage(self),
            OfflinePage(self),
            AnalysisPage(self),
            SettingsPage(self),
        ]

        # Add to stack
        for page in self.pages:
            self.page_stack.addWidget(page)

        # Show first page
        self.page_stack.setCurrentIndex(0)

    def _on_navigation_changed(self, index):
        """Handle navigation change."""
        self.page_stack.setCurrentIndex(index)

        # Update header title
        titles = [
            "Voice Profiles",
            "Realtime Conversion",
            "Offline Conversion",
            "Speaker Analysis",
            "Settings",
        ]
        self.header.title.setText(titles[index])

    def set_theme(self, theme: str):
        """Change theme."""
        self.setStyleSheet(get_theme_stylesheet(theme))


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MeanVCWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
