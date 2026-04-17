"""
Enhanced theme system for MeanVC GUI.

Features:
- Modern color palette with subtle gradients
- Improved depth through layered shadows
- Consistent 4px spacing grid
- Professional typography hierarchy
- Smooth hover/active states
"""

from PySide6.QtCore import QObject, Signal, Property, QRect
from PySide6.QtGui import QColor, QPalette, QFont, QFontDatabase, QLinearGradient, QBrush
from PySide6.QtWidgets import QStyle


class ThemeManager(QObject):
    """Theme manager with enhanced light/dark/system support."""
    
    theme_changed = Signal(str)
    colors_updated = Signal(dict)
    
    def __init__(self):
        super().__init__()
        self._theme = "dark"
        self._custom_colors = {}
        self._font_family = QFontDatabase.applicationFontFamilies(
            QFontDatabase.applicationFontFamilyName("Inter")
        )
    
    @Property(str)
    def current_theme(self):
        return self._theme
    
    @current_theme.setter
    def current_theme(self, theme):
        if theme in ["light", "dark", "system"]:
            self._theme = theme
            self.theme_changed.emit(theme)
            self.colors_updated.emit(self.colors())
    
    def colors(self):
        """Get color palette for current theme."""
        return _LIGHT_COLORS if self._theme == "light" else _DARK_COLORS
    
    def get_gradient(self, start_color: str, end_color: str, angle: float = 45):
        """Create a smooth linear gradient."""
        start = QColor(start_color)
        end = QColor(end_color)
        gradient = QLinearGradient(
            QRect(0, 0, 100, 100).centerPoint(),
            angle
        )
        gradient.setColorAt(0, start)
        gradient.setColorAt(1, end)
        return gradient
    
    def get_shadow(self, offset_x: int, offset_y: int, blur: int, color: str = "black"):
        """Create a subtle shadow for cards and elements."""
        from PySide6.QtGui import QDropShadowEffect
        shadow = QDropShadowEffect()
        shadow.setBlurRadius(blur)
        shadow.setOffset(offset_x, offset_y)
        shadow.setColor(QColor(color))
        return shadow


# =============================================================================
# DARK THEME - Professional, Modern, Deep
# =============================================================================

_DARK_COLORS = {
    # Primary background - very deep, almost black
    "bg_primary": "#0a0a0c",
    "bg_secondary": "#111114",
    "bg_tertiary": "#16161a",
    "bg_elevated": "#1c1c21",
    
    # Surface layers - creates depth
    "surface": "#18181b",
    "surface_elevated": "#1f1f26",
    "surface_highlight": "#25252d",
    "surface_card": "#151518",
    "surface_card_elevated": "#1f1f26",
    
    # Primary accent - cyan with subtle purple undertone
    "primary": "#22d3ee",
    "primary_darker": "#1ba2b8",
    "primary_light": "#4fd1e5",
    "primary_muted": "#22d3ee33",
    "primary_container": "#22d3ee1a",
    "primary_glow": "#22d3ee2a",
    
    # Secondary accent - violet/lavender
    "secondary": "#a78bfa",
    "secondary_darker": "#8b5cf6",
    "secondary_light": "#c4b5fd",
    
    # Text hierarchy - carefully calibrated for readability
    "text_primary": "#f4f4f5",
    "text_primary_subtle": "#e4e4e5",
    "text_secondary": "#a1a1aa",
    "text_tertiary": "#71717a",
    "text_disabled": "#52525b",
    "text_inverse": "#0a0a0c",
    
    # Semantic colors - muted for dark theme
    "success": "#34d399",
    "success_bg": "#34d3991a",
    "warning": "#fbbf24",
    "warning_bg": "#fbbf241a",
    "error": "#f87171",
    "error_bg": "#f871711a",
    "info": "#60a5fa",
    "info_bg": "#60a5fa1a",
    
    # Borders and dividers - subtle, barely visible
    "border": "#27272a",
    "border_faint": "#1f1f23",
    "border_focus": "#22d3ee",
    "border_highlight": "#3f3f46",
    
    # Dividers - ultra-subtle
    "divider": "#1f1f23",
    "divider_strong": "#27272a",
    
    # Selection and highlights
    "selection": "#22d3ee1a",
    "selection_text": "#f4f4f5",
    "selection_strong": "#22d3ee33",
    
    # Focus ring - for accessibility
    "focus_ring": "#22d3ee",
    "focus_ring_inner": "#22d3ee66",
}


# =============================================================================
# LIGHT THEME - Clean, Airy, Professional
# =============================================================================

_LIGHT_COLORS = {
    # Primary background - pure white to off-white
    "bg_primary": "#ffffff",
    "bg_secondary": "#fafafa",
    "bg_tertiary": "#f5f5f5",
    "bg_elevated": "#ffffff",
    
    # Surface layers
    "surface": "#ffffff",
    "surface_elevated": "#f9f9f9",
    "surface_highlight": "#f2f2f2",
    "surface_card": "#fafafa",
    "surface_card_elevated": "#f5f5f5",
    
    # Primary accent - teal/cyan
    "primary": "#0891b2",
    "primary_darker": "#0e7490",
    "primary_light": "#22d3ee",
    "primary_muted": "#0891b233",
    "primary_container": "#0891b21a",
    "primary_glow": "#0891b22a",
    
    # Secondary accent - violet
    "secondary": "#7c3aed",
    "secondary_darker": "#6d28d9",
    "secondary_light": "#a78bfa",
    
    # Text hierarchy
    "text_primary": "#18181b",
    "text_primary_subtle": "#3f3f46",
    "text_secondary": "#52525b",
    "text_tertiary": "#71717a",
    "text_disabled": "#a1a1a1",
    "text_inverse": "#ffffff",
    
    # Semantic colors - standard for light theme
    "success": "#059669",
    "success_bg": "#0596691a",
    "warning": "#d97706",
    "warning_bg": "#d977061a",
    "error": "#dc2626",
    "error_bg": "#dc26261a",
    "info": "#2563eb",
    "info_bg": "#2563eb1a",
    
    # Borders and dividers
    "border": "#e4e4e7",
    "border_faint": "#f4f4f5",
    "border_focus": "#0891b2",
    "border_highlight": "#d4d4d8",
    
    # Dividers
    "divider": "#f4f4f5",
    "divider_strong": "#e4e4e7",
    
    # Selection and highlights
    "selection": "#0891b21a",
    "selection_text": "#18181b",
    "selection_strong": "#0891b233",
    
    # Focus ring
    "focus_ring": "#0891b2",
    "focus_ring_inner": "#0891b266",
}


# =============================================================================
# STYLESHEET - Complete QSS for all Qt widgets
# =============================================================================

def get_enhanced_stylesheet(theme: str = "dark") -> str:
    """
    Get complete enhanced stylesheet with professional styling.
    
    Features:
    - Consistent 8px border radius across components
    - Subtle shadows for depth
    - Smooth gradients for backgrounds
    - Professional typography
    - Accessible focus states
    - Consistent spacing (4px, 8px, 12px, 16px, 24px)
    """
    colors = _LIGHT_COLORS if theme == "light" else _DARK_COLORS
    
    # Build color map for substitutions
    color_map = {k: v for k, v in colors.items()}
    
    stylesheet = f"""
    /* ============================================================
       GLOBAL RESET & BASE STYLES
       ============================================================ */
    * {{
        border-radius: 8px;
        outline: none;
    }}
    
    QMainWindow {{
        background-color: {color_map["bg_primary"]};
        font-size: 13px;
    }}
    
    QWidget {{
        color: {color_map["text_primary"]};
        font-family: "Inter", "SF Pro Display", -apple-system, "Segoe UI", sans-serif;
        font-weight: 400;
        background-color: {color_map["surface"]};
    }}
    
    /* ============================================================
       LAYOUT SPACING
       ============================================================ */
    QScrollArea, QFrame, QWidget {{
        background-color: {color_map["surface"]};
    }}
    
    /* ============================================================
       SCROLLBARS - Minimal, Clean
       ============================================================ */
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {color_map["border"]};
        border-radius: 4px;
        min-height: 48px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {color_map["text_tertiary"]};
    }}
    QScrollBar::handle:vertical:pressed {{
        background: {color_map["primary_darker"]};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    
    QScrollBar:horizontal {{
        background: transparent;
        height: 8px;
        margin: 0px;
    }}
    QScrollBar::handle:horizontal {{
        background: {color_map["border"]};
        border-radius: 4px;
        min-width: 48px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {color_map["text_tertiary"]};
    }}
    QScrollBar::handle:horizontal:pressed {{
        background: {color_map["primary_darker"]};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}
    
    /* ============================================================
       MAIN WINDOW & CONTENT AREA
       ============================================================ */
    QFrame {{
        background-color: {color_map["surface"]};
    }}
    
    /* ============================================================
       SIDEBAR - Navigation Panel
       ============================================================ */
    ModernSidebar, Sidebar {{
        background-color: {color_map["bg_secondary"]};
        border-right: 1px solid {color_map["border_faint"]};
        width: 240px;
    }}
    
    /* ============================================================
       SIDEBAR NAVIGATION ITEMS
       ============================================================ */
    ModernNavItem {{
        height: 48px;
        font-size: 14px;
        border-radius: 8px;
        transition: background-color 0.15s ease;
    }}
    ModernNavItem:hover:not(:selected) {{
        background-color: {color_map["surface_elevated"]};
    }}
    ModernNavItem:selected {{
        background-color: {color_map["bg_elevated"]};
        color: {color_map["primary"]};
        font-weight: 600;
    }}
    
    /* ============================================================
       HEADER - Top Bar
       ============================================================ */
    ModernHeader, Header {{
        height: 64px;
        background-color: {color_map["bg_secondary"]};
        border-bottom: 1px solid {color_map["border_faint"]};
    }}
    
    /* ============================================================
       CARDS - Elevated Content Containers
       ============================================================ */
    Card, ProfileCard, DetailsCard {{
        background-color: {color_map["surface_card"]};
        border: 1px solid {color_map["border_faint"]};
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08),
                    0 1px 2px rgba(0, 0, 0, 0.04);
    }}
    Card:hover {{
        border-color: {color_map["border"]};
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1),
                    0 2px 4px rgba(0, 0, 0, 0.06);
    }}
    Card:elevated {{
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.12),
                    0 4px 8px rgba(0, 0, 0, 0.08);
    }}
    
    /* ============================================================
       BUTTONS - Primary, Secondary, Text
       ============================================================ */
    QPushButton {{
        padding: 10px 20px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 500;
        border: 1px solid transparent;
        transition: all 0.15s ease;
    }}
    
    /* Secondary button - outlined style */
    QPushButton[secondary="true"] {{
        background-color: transparent;
        border-color: {color_map["border"]};
        color: {color_map["text_primary"]};
    }}
    QPushButton[secondary="true"]:hover {{
        background-color: {color_map["surface_elevated"]};
        border-color: {color_map["border_focus"]};
    }}
    
    /* Primary button - filled with accent color */
    QPushButton[primary="true"] {{
        background-color: {color_map["primary"]};
        color: {color_map["text_inverse"]};
        border: none;
    }}
    QPushButton[primary="true"]:hover {{
        background-color: {color_map["primary_light"]};
        box-shadow: 0 4px 12px {color_map["primary_glow"]};
    }}
    QPushButton[primary="true"]:pressed {{
        background-color: {color_map["primary_darker"]};
    }}
    QPushButton[primary="true"]:disabled {{
        background-color: {color_map["border"]};
        color: {color_map["text_disabled"]};
    }}
    
    /* Danger button - for destructive actions */
    QPushButton[danger="true"] {{
        background-color: {color_map["error_bg"]};
        color: {color_map["error"]};
        border: 1px solid {color_map["error"]};
    }}
    QPushButton[danger="true"]:hover {{
        background-color: {color_map["error"]};
        color: {color_map["text_inverse"]};
    }}
    
    /* Icon button - minimal, for toolbars */
    QPushButton[iconOnly="true"] {{
        background: transparent;
        border: none;
        padding: 8px;
        border-radius: 8px;
    }}
    QPushButton[iconOnly="true"]:hover {{
        background-color: {color_map["surface_elevated"]};
    }}
    
    /* ============================================================
       INPUT FIELDS - Text, Search, Password
       ============================================================ */
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {color_map["bg_primary"]};
        color: {color_map["text_primary"]};
        border: 1px solid {color_map["border"]};
        padding: 12px 14px;
        border-radius: 8px;
        font-size: 13px;
        transition: border-color 0.15s ease;
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border-color: {color_map["border_focus"]};
        box-shadow: 0 0 0 3px {color_map["selection"]};
    }}
    QLineEdit:hover:not(:focus) {{
        border-color: {color_map["border_highlight"]};
    }}
    QLineEdit::placeholder, QTextEdit::placeholder, QPlainTextEdit::placeholder {{
        color: {color_map["text_disabled"]};
    }}
    QLineEdit[readonly] {{
        background-color: {color_map["surface_elevated"]};
    }}
    
    /* ============================================================
       COMBOBOX - Dropdown Selection
       ============================================================ */
    QComboBox {{
        background-color: {color_map["surface"]};
        color: {color_map["text_primary"]};
        border: 1px solid {color_map["border"]};
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 13px;
    }}
    QComboBox:hover {{
        border-color: {color_map["border_focus"]};
    }}
    QComboBox:focus {{
        border-color: {color_map["border_focus"]};
        box-shadow: 0 0 0 3px {color_map["selection"]};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 32px;
    }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {color_map["text_tertiary"]};
    }}
    QComboBox QListView {{
        background-color: {color_map["surface"]};
        border: 1px solid {color_map["border"]};
        border-radius: 8px;
        padding: 4px;
    }}
    QComboBox QListView::item {{
        padding: 10px 14px;
        border-radius: 6px;
    }}
    QComboBox QListView::item:selected {{
        background-color: {color_map["selection"]};
        color: {color_map["text_primary"]};
    }}
    QComboBox QListView::item:hover {{
        background-color: {color_map["surface_elevated"]};
    }}
    
    /* ============================================================
       SLIDERS - Range Sliders
       ============================================================ */
    QSlider::groove:horizontal {{
        background: {color_map["border"]};
        height: 4px;
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {color_map["primary"]};
        width: 20px;
        height: 20px;
        margin: -8px 0;
        border-radius: 10px;
        border: 2px solid {color_map["bg_primary"]};
    }}
    QSlider::handle:horizontal:hover {{
        background: {color_map["primary_light"]};
    }}
    QSlider::handle:horizontal:pressed {{
        background: {color_map["primary_darker"]};
    }}
    QSlider::sub-page:horizontal {{
        background: {color_map["primary"]};
        border-radius: 2px;
    }}
    
    /* Vertical slider */
    QSlider::groove:vertical {{
        background: {color_map["border"]};
        width: 4px;
        border-radius: 2px;
    }}
    QSlider::handle:vertical {{
        background: {color_map["primary"]};
        width: 20px;
        height: 20px;
        margin: 0 -8px;
        border-radius: 10px;
        border: 2px solid {color_map["bg_primary"]};
    }}
    
    /* ============================================================
       PROGRESS BAR
       ============================================================ */
    QProgressBar {{
        background-color: {color_map["border"]};
        border: none;
        border-radius: 4px;
        height: 6px;
        text-align: center;
        font-size: 11px;
        color: {color_map["text_tertiary"]};
    }}
    QProgressBar::chunk {{
        background: {color_map["primary"]};
        border-radius: 4px;
    }}
    QProgressBar::chunk:indeterminate {{
        background: {color_map["border_focus"]};
    }}
    
    /* ============================================================
       LIST WIDGET - For profiles, items, etc.
       ============================================================ */
    QListWidget {{
        background: transparent;
        border: none;
        outline: none;
    }}
    QListWidget::item {{
        background: transparent;
        color: {color_map["text_primary"]};
        padding: 12px 16px;
        border-radius: 8px;
        margin: 2px 0;
    }}
    QListWidget::item:selected {{
        background: {color_map["selection"]};
        color: {color_map["text_primary"]};
    }}
    QListWidget::item:hover {{
        background: {color_map["surface_elevated"]};
    }}
    QListWidget::item:pressed {{
        background: {color_map["bg_elevated"]};
    }}
    
    /* ============================================================
       TABLE WIDGET - For data grids
       ============================================================ */
    QTableWidget, QTreeWidget {{
        background: transparent;
        border: none;
        gridline-color: {color_map["divider"]};
    }}
    QTableWidget::item, QTreeWidget::item {{
        padding: 10px 14px;
        border: none;
    }}
    QTableWidget::item:selected, QTreeWidget::item:selected {{
        background: {color_map["selection"]};
        color: {color_map["text_primary"]};
    }}
    QHeaderView::section {{
        background: transparent;
        color: {color_map["text_secondary"]};
        font-weight: 500;
        font-size: 12px;
        padding: 10px 14px;
        border: none;
        border-bottom: 1px solid {color_map["divider"]};
    }}
    
    /* ============================================================
       GROUP BOX - Section Headers
       ============================================================ */
    QGroupBox {{
        background: {color_map["surface_card"]};
        border: 1px solid {color_map["border_faint"]};
        border-radius: 12px;
        margin-top: 24px;
        padding-top: 16px;
        font-weight: 500;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 16px;
        padding: 0 12px;
        color: {color_map["text_secondary"]};
        font-size: 13px;
    }}
    
    /* ============================================================
       MENU - Context menus, dropdowns
       ============================================================ */
    QMenu {{
        background: {color_map["surface_card_elevated"]};
        color: {color_map["text_primary"]};
        border: 1px solid {color_map["border"]};
        border-radius: 10px;
        padding: 6px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
    }}
    QMenu::item {{
        padding: 10px 36px 10px 14px;
        border-radius: 6px;
    }}
    QMenu::item:selected {{
        background: {color_map["selection"]};
    }}
    QMenu::separator {{
        height: 1px;
        background: {color_map["divider"]};
        margin: 6px 0;
    }}
    
    /* ============================================================
       TOOLTIP - Help text
       ============================================================ */
    QToolTip {{
        background: {color_map["bg_elevated"]};
        color: {color_map["text_primary"]};
        border: 1px solid {color_map["border"]};
        padding: 8px 12px;
        border-radius: 8px;
        font-size: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }}
    
    /* ============================================================
       CHECKBOX & RADIOBUTTON - Custom Styles
       ============================================================ */
    QCheckBox, QRadioButton {{
        color: {color_map["text_primary"]};
        spacing: 10px;
        font-size: 13px;
    }}
    QCheckBox::indicator, QRadioButton::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 1px solid {color_map["border"]};
        background: {color_map["bg_primary"]};
        transition: all 0.15s ease;
    }}
    QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
        border-color: {color_map["border_focus"]};
    }}
    QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
        background: {color_map["primary"]};
        border-color: {color_map["primary"]};
    }}
    QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {{
        opacity: 0.5;
    }}
    
    /* ============================================================
       SPINBOX - Number Input
       ============================================================ */
    QSpinBox, QDoubleSpinBox {{
        background-color: {color_map["bg_primary"]};
        color: {color_map["text_primary"]};
        border: 1px solid {color_map["border"]};
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 13px;
    }}
    QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {color_map["border_focus"]};
        box-shadow: 0 0 0 3px {color_map["selection"]};
    }}
    
    /* ============================================================
       TAB WIDGET - Tabbed Content
       ============================================================ */
    QTabWidget::pane {{
        background: {color_map["surface"]};
        border: none;
    }}
    QTabBar::tab {{
        background: transparent;
        color: {color_map["text_secondary"]};
        padding: 10px 16px;
        border: none;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        color: {color_map["primary"]};
        background: {color_map["surface_elevated"]};
    }}
    QTabBar::tab:hover {{
        color: {color_map["text_primary"]};
        background: {color_map["surface_elevated"]};
    }}
    QTabBar::tab:first:top {{
        margin-left: 0;
    }}
    QTabBar::tab:last:top {{
        margin-right: 0;
    }}
    
    /* ============================================================
       STATUSBAR - Bottom status bar
       ============================================================ */
    QStatusBar {{
        background: {color_map["bg_secondary"]};
        color: {color_map["text_secondary"]};
        border-top: 1px solid {color_map["border_faint"]};
        padding: 6px 12px;
        font-size: 12px;
    }}
    
    /* ============================================================
       PLACEHOLDER TEXT - Empty state
       ============================================================ */
    QLabel[placeholder="true"] {{
        color: {color_map["text_disabled"]};
        padding: 24px;
        font-style: italic;
    }}
    
    /* ============================================================
       SEPARATOR - Horizontal dividers
       ============================================================ */
    QFrame[separator="true"] {{
        background: {color_map["divider"]};
        height: 1px;
        margin: 16px 0;
    }}
    
    /* ============================================================
       AVATAR - User profile images
       ============================================================ */
    QLabel[avatar="true"] {{
        border-radius: 999px;
        background: {color_map["bg_elevated"]};
        padding: 4px;
        border: 2px solid {color_map["bg_primary"]};
    }}
    
    /* ============================================================
       BADGE - Small status indicators
       ============================================================ */
    QLabel[badge="true"] {{
        background: {color_map["surface_elevated"]};
        color: {color_map["text_secondary"]};
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 11px;
        border: 1px solid {color_map["border_faint"]};
    }}
    
    /* ============================================================
       LOADING SPINNER - Custom spinner
       ============================================================ */
    QLabel[spinner="true"] {{
        background: transparent;
        border: 2px solid {color_map["border"]};
        border-top-color: {color_map["primary"]};
        border-radius: 999px;
        width: 20px;
        height: 20px;
        animation: spin 0.8s linear infinite;
    }}
    @keyframes spin {{
        from {{ transform: rotate(0deg); }}
        to {{ transform: rotate(360deg); }}
    }}
    
    /* ============================================================
       GLOW EFFECT - For highlighted elements
       ============================================================ */
    QLabel[glow="true"] {{
        color: {color_map["primary"]};
        text-shadow: 0 0 8px {color_map["primary_glow"]};
    }}
    
    /* ============================================================
       GRADIENT BACKGROUND - For decorative elements
       ============================================================ */
    QLabel[gradient="true"] {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                   stop:0 {color_map["primary_darker"]},
                                   stop:1 {color_map["secondary_darker"]});
        border-radius: 8px;
        padding: 16px;
    }}
    
    /* ============================================================
       HOVER GLOW - For interactive elements
       ============================================================ */
    QFrame:hover[glow="true"] {{
        box-shadow: 0 0 20px {color_map["primary_glow"]};
    }}
    
    /* ============================================================
       ACCESSIBILITY - Focus indicators
       ============================================================ */
    QAbstractItemView:focus {{
        background: transparent;
    }}
    QAbstractItemView:focus::item {{
        background: transparent;
    }}
    
    /* ============================================================
       DARK MODE ONLY - Override for dark theme
       ============================================================ */
    """
    
    if theme == "dark":
        stylesheet += f"""
        /* Dark theme specific overrides */
        QLabel {{
            color: {color_map["text_primary"]};
        }}
        QLabel[disabled="true"] {{
            color: {color_map["text_disabled"]};
        }}
        """
    
    return stylesheet


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def apply_card_elevation(widget, level: int = 1):
    """
    Apply elevation to a widget for depth effect.
    
    Args:
        widget: QWidget to apply elevation to
        level: Elevation level (1=low, 2=medium, 3=high)
    """
    from PySide6.QtGui import QDropShadowEffect
    
    shadows = {
        1: (0, 2, 4, 0.08),    # Subtle
        2: (0, 4, 8, 0.12),   # Medium
        3: (0, 8, 16, 0.16),  # Prominent
    }
    
    offset_x, offset_y, blur, opacity = shadows.get(level, shadows[1])
    shadow = QDropShadowEffect()
    shadow.setBlurRadius(blur)
    shadow.setOffset(offset_x, offset_y)
    shadow.setColor(QColor("rgba(0, 0, 0, {})".format(opacity)))
    
    widget.setGraphicsEffect(shadow)


def create_gradient_background(start_color: str, end_color: str, widget):
    """
    Create a gradient background for a widget.
    
    Args:
        start_color: Starting color (e.g., "#22d3ee")
        end_color: Ending color (e.g., "#a78bfa")
        widget: QWidget to apply gradient to
    """
    gradient = get_gradient(start_color, end_color)
    brush = QBrush(gradient)
    widget.setPalette(QPalette())
    widget.palette().setBrush(widget.backgroundRole(), brush)


# =============================================================================
# THEME INITIALIZATION
# =============================================================================

def initialize_theme(theme: str = "dark") -> ThemeManager:
    """
    Initialize and return a theme manager.
    
    Args:
        theme: Theme to initialize ("light", "dark", or "system")
    
    Returns:
        ThemeManager instance
    """
    manager = ThemeManager()
    manager.current_theme = theme
    return manager


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "ThemeManager",
    "get_enhanced_stylesheet",
    "apply_card_elevation",
    "create_gradient_background",
    "initialize_theme",
    "_DARK_COLORS",
    "_LIGHT_COLORS",
]
