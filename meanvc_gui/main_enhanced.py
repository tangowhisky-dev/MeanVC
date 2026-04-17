"""
Main application window with enhanced modern design.

Features:
- Consistent 8px spacing grid
- Professional color hierarchy
- Smooth animations and transitions
- Improved visual hierarchy
- Better component proportions
"""

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
    QSplitter,
)
from PySide6.QtCore import Qt, QSize, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QIcon, QColor, QLinearGradient, QBrush

from meanvc_gui.components.enhanced_theme import (
    get_enhanced_stylesheet,
    ThemeManager,
    apply_card_elevation,
    initialize_theme,
    _DARK_COLORS,
)


class EnhancedNavItem(QFrame):
    """Enhanced navigation item with smooth transitions."""
    
    clicked = Signal(int)
    
    def __init__(self, icon: str, text: str, index: int, parent=None):
        super().__init__(parent)
        self._index = index
        self._icon = icon
        self._text = text
        self._selected = False
        self._setup_ui()
    
    def _setup_ui(self):
        colors = _DARK_COLORS
        
        self.setFixedHeight(52)
        self.setCursor(Qt.PointingHandCursor)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(14)
        
        # Icon with proper sizing
        self.icon_label = QLabel(self._icon)
        self.icon_label.setStyleSheet("font-size: 20px;")
        layout.addWidget(self.icon_label)
        
        # Text label
        self.text_label = QLabel(self._text)
        self.text_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 500;
            color: {colors["text_secondary"]};
        """)
        layout.addWidget(self.text_label)
        
        # Frame styling
        self.setStyleSheet(f"""
            QFrame {{
                background: transparent;
                border-radius: 10px;
                transition: background-color 0.2s ease;
            }}
        """)
    
    def set_selected(self, selected: bool):
        self._selected = selected
        self._update_style()
    
    def _update_style(self):
        colors = _DARK_COLORS
        
        if self._selected:
            self.setStyleSheet(f"""
                QFrame {{
                    background: {colors["bg_elevated"]};
                    color: {colors["primary"]};
                    border-radius: 10px;
                }}
            """)
            self.text_label.setStyleSheet(f"""
                font-size: 14px;
                font-weight: 600;
                color: {colors["primary"]};
            """)
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background: transparent;
                    border-radius: 10px;
                }}
            """)
            self.text_label.setStyleSheet(f"""
                font-size: 14px;
                font-weight: 500;
                color: {colors["text_secondary"]};
            """)
    
    def enterEvent(self, event):
        if not self._selected:
            self.setStyleSheet(f"""
                QFrame {{
                    background: {colors["surface_elevated"]};
                    border-radius: 10px;
                }}
            """)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self._update_style()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        self.clicked.emit(self._index)


class EnhancedSidebar(QFrame):
    """Enhanced sidebar with professional styling."""
    
    navigation_changed = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_index = 0
        self._setup_ui()
    
    def _setup_ui(self):
        colors = _DARK_COLORS
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 24, 16, 24)
        layout.setSpacing(6)
        
        # Logo with better styling
        title = QLabel("⬡ MeanVC")
        title.setStyleSheet(f"""
            font-size: 24px;
            font-weight: 700;
            color: {colors["primary"]};
            padding: 12px 20px;
        """)
        layout.addWidget(title)
        
        layout.addSpacing(32)
        
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
            item = EnhancedNavItem(icon, text, idx)
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
            padding: 12px;
            background: {colors["surface_card"]};
            border-radius: 8px;
        """)
        layout.addWidget(version)
        
        self.setStyleSheet(f"""
            QFrame {{
                background: {colors["bg_secondary"]};
                border-right: 1px solid {colors["border_faint"]};
                width: 240px;
            }}
        """)
    
    def _on_item_clicked(self, index):
        self.nav_items[self._selected_index].set_selected(False)
        self._selected_index = index
        self.nav_items[index].set_selected(True)
        self.navigation_changed.emit(index)


class EnhancedHeader(QFrame):
    """Enhanced header with theme toggle and actions."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        colors = _DARK_COLORS
        
        self.setFixedHeight(72)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 0)
        
        # Title with better typography
        self.title = QLabel("Voice Profiles")
        self.title.setStyleSheet(f"""
            font-size: 22px;
            font-weight: 600;
            color: {colors["text_primary"]};
            letter-spacing: -0.02em;
        """)
        layout.addWidget(self.title)
        
        layout.addStretch()
        
        # Theme toggle with better design
        theme_btn = QLabel("🌙")
        theme_btn.setFixedSize(40, 40)
        theme_btn.setStyleSheet(f"""
            QLabel {{
                background: {colors["surface_elevated"]};
                border: 1px solid {colors["border"]};
                border-radius: 10px;
                font-size: 18px;
                color: {colors["text_secondary"]};
                transition: all 0.2s ease;
            }}
            QLabel:hover {{
                background: {colors["surface_highlight"]};
                border-color: {colors["border_focus"]};
                color: {colors["text_primary"]};
            }}
        """)
        layout.addWidget(theme_btn)
        
        self.setStyleSheet(f"""
            QFrame {{
                background: {colors["bg_secondary"]};
                border-bottom: 1px solid {colors["border_faint"]};
            }}
        """)


class MeanVCWindow(QMainWindow):
    """
    Main application window with enhanced design.
    
    Features:
    - Consistent spacing grid (8px base)
    - Professional color hierarchy
    - Smooth animations
    - Improved visual hierarchy
    - Better proportions
    """
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("MeanVC - Voice Conversion")
        self.setGeometry(100, 100, 1344, 960)
        self.setMinimumSize(1024, 768)
        
        # Initialize theme
        self.theme_manager = ThemeManager()
        self.theme_manager.current_theme = "dark"
        colors = _DARK_COLORS
        
        # Apply global styles
        self.setStyleSheet(get_enhanced_stylesheet("dark"))
        self._apply_palette(colors)
        
        # Setup UI
        self._setup_ui()
        
        # Initialize pages
        self._init_pages()
    
    def _apply_palette(self, colors):
        """Apply color palette."""
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(colors["bg_primary"]))
        palette.setColor(self.foregroundRole(), QColor(colors["text_primary"]))
        self.setPalette(palette)
    
    def _setup_ui(self):
        """Setup main UI with consistent proportions."""
        from PySide6.QtWidgets import QHBoxLayout, QSplitter
        
        # Use a splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        
        # Sidebar
        sidebar = EnhancedSidebar()
        sidebar.navigation_changed.connect(self._on_navigation_changed)
        splitter.addWidget(sidebar)
        
        # Main content area
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header
        header = EnhancedHeader()
        main_layout.addWidget(header)
        
        # Page stack
        self.page_stack = QStackedWidget()
        main_layout.addWidget(self.page_stack)
        
        splitter.addWidget(main_widget)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        
        splitter.setSizes([240, None])
        splitter.setStyleSheet("")
        
        self.setCentralWidget(splitter)
    
    def _init_pages(self):
        """Initialize page widgets."""
        from meanvc_gui.pages.library import LibraryPage
        from meanvc_gui.pages.realtime import RealtimePage
        from meanvc_gui.pages.offline import OfflinePage
        from meanvc_gui.pages.analysis import AnalysisPage
        from meanvc_gui.pages.settings import SettingsPage
        
        # Create pages with enhanced styling
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
        self.theme_manager.current_theme = theme
        self.setStyleSheet(get_enhanced_stylesheet(theme))


def main():
    """Main entry point."""
    # Set application style
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Set high DPI scale factor for retina displays
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # Create and show window
    window = MeanVCWindow()
    window.show()
    
    # Apply window effects for better aesthetics
    window.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
