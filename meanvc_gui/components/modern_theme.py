"""Modern theme system for MeanVC GUI.

Supports light, dark, and system theme modes.
"""

import os
from PySide6.QtCore import QObject, Signal, Property
from PySide6.QtGui import QColor, QPalette, QFont, QFontDatabase


class ThemeManager(QObject):
    """Theme manager with light/dark/system support."""

    theme_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self._theme = "system"
        self._custom_colors = {}

    @Property(str)
    def current_theme(self):
        return self._theme

    @current_theme.setter
    def current_theme(self, theme):
        if theme in ["light", "dark", "system"]:
            self._theme = theme
            self.theme_changed.emit(theme)

    def colors(self):
        """Get color palette for current theme."""
        return _LIGHT_COLORS if self._theme == "light" else _DARK_COLORS


# Modern dark theme - inspired by VS Code, Figma
_DARK_COLORS = {
    # Backgrounds - layered depth
    "bg_primary": "#0d0d0f",
    "bg_secondary": "#141416",
    "bg_tertiary": "#1a1a1d",
    "bg_elevated": "#1f1f23",
    "bg overlay": "#000000",
    # Surface cards
    "surface": "#18181b",
    "surface_hover": "#222226",
    "surface_active": "#2a2a2f",
    "surface_card": "#141416",
    "surface_card_hover": "#1a1a1e",
    # Primary accent - Cyan/Violet gradient feel
    "primary": "#22d3ee",
    "primary_hover": "#06b6d4",
    "primary_muted": "#22d3ee33",
    "primary_container": "#22d3ee1a",
    # Secondary
    "secondary": "#a78bfa",
    "secondary_hover": "#8b5cf6",
    # Text hierarchy
    "text_primary": "#fafafa",
    "text_secondary": "#a1aaae",
    "text_tertiary": "#71717a",
    "text_disabled": "#52525b",
    "text_inverse": "#0d0d0f",
    # Semantic colors
    "success": "#34d399",
    "success_bg": "#34d3991a",
    "warning": "#fbbf24",
    "warning_bg": "#fbbf241a",
    "error": "#f87171",
    "error_bg": "#f871711a",
    "info": "#60a5fa",
    "info_bg": "#60a5fa1a",
    # Borders
    "border": "#27272a",
    "border_focus": "#22d3ee",
    "border_subtle": "#1f1f23",
    # Dividers
    "divider": "#1f1f23",
    "divider_strong": "#27272a",
    # Shadows
    "shadow": "#000000",
    "shadow_strong": "#000000aa",
    # Input fields
    "input_bg": "#0d0d0f",
    "input_border": "#27272a",
    "input_placeholder": "#52525b",
    # Selection
    "selection": "#22d3ee33",
    "selection_text": "#22d3ee",
}


# Clean light theme
_LIGHT_COLORS = {
    # Backgrounds
    "bg_primary": "#ffffff",
    "bg_secondary": "#fafafa",
    "bg_tertiary": "#f5f5f5",
    "bg_elevated": "#ffffff",
    "bg_overlay": "#000000",
    # Surface cards
    "surface": "#ffffff",
    "surface_hover": "#f5f5f5",
    "surface_active": "#eeeeee",
    "surface_card": "#fafafa",
    "surface_card_hover": "#f0f0f0",
    # Primary accent
    "primary": "#0891b2",
    "primary_hover": "#0e7490",
    "primary_muted": "#0891b233",
    "primary_container": "#0891b21a",
    # Secondary
    "secondary": "#7c3aed",
    "secondary_hover": "#6d28d9",
    # Text hierarchy
    "text_primary": "#18181b",
    "text_secondary": "#52525b",
    "text_tertiary": "#71717a",
    "text_disabled": "#a1aaa",
    "text_inverse": "#ffffff",
    # Semantic
    "success": "#059669",
    "success_bg": "#0596691a",
    "warning": "#d97706",
    "warning_bg": "#d977061a",
    "error": "#dc2626",
    "error_bg": "#dc26261a",
    "info": "#2563eb",
    "info_bg": "#2563eb1a",
    # Borders
    "border": "#e4e4e7",
    "border_focus": "#0891b2",
    "border_subtle": "#f4f4f5",
    # Dividers
    "divider": "#f4f4f5",
    "divider_strong": "#e4e4e7",
    # Shadows
    "shadow": "#00000008",
    "shadow_strong": "#0000001a",
    # Input
    "input_bg": "#ffffff",
    "input_border": "#e4e4e7",
    "input_placeholder": "#a1aaa",
    # Selection
    "selection": "#0891b233",
    "selection_text": "#0891b2",
}


def get_theme_stylesheet(theme: str = "dark") -> str:
    """Get complete theme stylesheet."""
    colors = _LIGHT_COLORS if theme == "light" else _DARK_COLORS

    return f"""
    /* ======================
       GLOBAL RESET
       ====================== */
    * {{
        border-radius: 8px;
    }}
    
    QMainWindow {{
        background-color: {colors["bg_primary"]};
    }}
    
    QWidget {{
        color: {colors["text_primary"]};
        font-family: "Inter", "Segoe UI", -apple-system, sans-serif;
        font-size: 13px;
    }}
    
    /* ======================
       SCROLLBARS
       ====================== */
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        border: none;
    }}
    QScrollBar::handle:vertical {{
        background: {colors["border"]};
        border-radius: 5px;
        min-height: 40px;
        margin: 4px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {colors["text_tertiary"]};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 10px;
        border: none;
    }}
    QScrollBar::handle:horizontal {{
        background: {colors["border"]};
        border-radius: 5px;
        min-width: 40px;
        margin: 4px;
    }}
    
    /* ======================
       PUSH BUTTONS
       ====================== */
    QPushButton {{
        background-color: {colors["surface"]};
        color: {colors["text_primary"]};
        border: 1px solid {colors["border"]};
        padding: 10px 20px;
        border-radius: 8px;
        font-weight: 500;
        font-size: 13px;
    }}
    QPushButton:hover {{
        background-color: {colors["surface_hover"]};
        border-color: {colors["border_focus"]};
    }}
    QPushButton:pressed {{
        background-color: {colors["surface_active"]};
    }}
    QPushButton:disabled {{
        color: {colors["text_disabled"]};
        background-color: {colors["bg_secondary"]};
        border-color: {colors["border"]};
    }}
    
    /* Primary button variant */
    QPushButton[primary="true"] {{
        background-color: {colors["primary"]};
        color: {colors["text_inverse"]};
        border: none;
    }}
    QPushButton[primary="true"]:hover {{
        background-color: {colors["primary_hover"]};
    }}
    QPushButton[primary="true"]:disabled {{
        background-color: {colors["border"]};
        color: {colors["text_disabled"]};
    }}
    
    /* Icon button */
    QPushButton[iconOnly="true"] {{
        background: transparent;
        border: none;
        padding: 8px;
        border-radius: 8px;
    }}
    QPushButton[iconOnly="true"]:hover {{
        background-color: {colors["surface_hover"]};
    }}
    
    /* ======================
       INPUT FIELDS
       ====================== */
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {colors["input_bg"]};
        color: {colors["text_primary"]};
        border: 1px solid {colors["input_border"]};
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 13px;
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border-color: {colors["border_focus"]};
    }}
    QLineEdit::placeholder, QTextEdit::placeholder {{
        color: {colors["input_placeholder"]};
    }}
    
    /* ======================
       COMBOBOX
       ====================== */
    QComboBox {{
        background-color: {colors["surface"]};
        color: {colors["text_primary"]};
        border: 1px solid {colors["border"]};
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 13px;
    }}
    QComboBox:hover {{
        border-color: {colors["border_focus"]};
    }}
    QComboBox:focus {{
        border-color: {colors["border_focus"]};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 30px;
    }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {colors["text_secondary"]};
    }}
    QComboBox QListView {{
        background-color: {colors["surface"]};
        border: 1px solid {colors["border"]};
        border-radius: 8px;
        padding: 4px;
    }}
    QComboBox QListView::item {{
        padding: 10px 14px;
        border-radius: 6px;
    }}
    QComboBox QListView::item:selected {{
        background-color: {colors["selection"]};
        color: {colors["selection_text"]};
    }}
    QComboBox QListView::item:hover {{
        background-color: {colors["surface_hover"]};
    }}
    
    /* ======================
       SLIDERS
       ====================== */
    QSlider::groove:horizontal {{
        background: {colors["border"]};
        height: 4px;
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {colors["primary"]};
        width: 16px;
        height: 16px;
        margin: -6px 0;
        border-radius: 8px;
    }}
    QSlider::handle:horizontal:hover {{
        background: {colors["primary_hover"]};
    }}
    QSlider::sub-page:horizontal {{
        background: {colors["primary"]};
        border-radius: 2px;
    }}
    
    /* ======================
       PROGRESS BAR
       ====================== */
    QProgressBar {{
        background-color: {colors["border"]};
        border: none;
        border-radius: 4px;
        height: 6px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        background: {colors["primary"]};
        border-radius: 4px;
    }}
    
    /* ======================
       LIST WIDGET
       ====================== */
    QListWidget {{
        background: transparent;
        border: none;
        outline: none;
    }}
    QListWidget::item {{
        background: transparent;
        color: {colors["text_primary"]};
        padding: 12px 16px;
        border-radius: 8px;
        margin: 2px 0;
    }}
    QListWidget::item:selected {{
        background: {colors["selection"]};
        color: {colors["selection_text"]};
    }}
    QListWidget::item:hover {{
        background: {colors["surface_hover"]};
    }}
    
    /* ======================
       TABLE WIDGET
       ====================== */
    QTableWidget, QTreeWidget {{
        background: transparent;
        border: none;
        gridline-color: {colors["divider"]};
    }}
    QTableWidget::item, QTreeWidget::item {{
        padding: 10px 14px;
        border: none;
    }}
    QTableWidget::item:selected, QTreeWidget::item:selected {{
        background: {colors["selection"]};
        color: {colors["selection_text"]};
    }}
    QHeaderView::section {{
        background: transparent;
        color: {colors["text_secondary"]};
        font-weight: 500;
        font-size: 12px;
        padding: 10px 14px;
        border: none;
        border-bottom: 1px solid {colors["divider"]};
    }}
    
    /* ======================
       GROUP BOX
       ====================== */
    QGroupBox {{
        background: {colors["surface_card"]};
        border: 1px solid {colors["border"]};
        border-radius: 12px;
        margin-top: 20px;
        padding-top: 20px;
        font-weight: 500;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 16px;
        padding: 0 10px;
        color: {colors["text_secondary"]};
    }}
    
    /* ======================
       MENU
       ====================== */
    QMenu {{
        background: {colors["surface"]};
        color: {colors["text_primary"]};
        border: 1px solid {colors["border"]};
        border-radius: 10px;
        padding: 6px;
    }}
    QMenu::item {{
        padding: 10px 36px 10px 14px;
        border-radius: 6px;
    }}
    QMenu::item:selected {{
        background: {colors["selection"]};
    }}
    QMenu::separator {{
        height: 1px;
        background: {colors["divider"]};
        margin: 6px 0;
    }}
    
    /* ======================
       TOOLTIP
       ====================== */
    QToolTip {{
        background: {colors["bg_tertiary"]};
        color: {colors["text_primary"]};
        border: 1px solid {colors["border"]};
        padding: 8px 12px;
        border-radius: 8px;
    }}
    
    /* ======================
       CHECKBOX & RADIO
       ====================== */
    QCheckBox, QRadioButton {{
        color: {colors["text_primary"]};
        spacing: 10px;
    }}
    QCheckBox::indicator, QRadioButton::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 1px solid {colors["border"]};
        background: transparent;
    }}
    QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
        background: {colors["primary"]};
        border-color: {colors["primary"]};
    }}
    
    /* ======================
       FRAMES
       ====================== */
    QFrame[frameShape="4"], QFrame[frameShape="5"] {{
        background: {colors["divider"]};
    }}
    
    /* ======================
       TAB WIDGET
       ====================== */
    QTabWidget::pane {{
        border: none;
    }}
    QTabBar::tab {{
        background: transparent;
        color: {colors["text_secondary"]};
        padding: 10px 16px;
        border: none;
    }}
    QTabBar::tab:selected {{
        color: {colors["primary"]};
    }}
    QTabBar::tab:hover {{
        color: {colors["text_primary"]};
    }}
    
    /* ======================
       DIALOGS
       ====================== */
    QDialog {{
        background: {colors["bg_primary"]};
    }}
    """


def get_card_style(theme: str = "dark") -> str:
    """Get card/container stylesheet."""
    colors = _LIGHT_COLORS if theme == "light" else _DARK_COLORS
    return f"""
        background: {colors["surface_card"]};
        border: 1px solid {colors["border"]};
        border-radius: 12px;
    """


def get_nav_item_style(selected: bool = False, theme: str = "dark") -> str:
    """Get navigation item style."""
    colors = _LIGHT_COLORS if theme == "light" else _DARK_COLORS

    if selected:
        return f"""
            background: {colors["primary_container"]};
            color: {colors["primary"]};
            border-radius: 8px;
        """
    else:
        return f"""
            background: transparent;
            color: {colors["text_secondary"]};
            border-radius: 8px;
        """


# Theme manager singleton
_theme_manager = None


def get_theme_manager() -> ThemeManager:
    """Get theme manager singleton."""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager


# Convenience accessors
COLORS = _DARK_COLORS  # Default to dark
