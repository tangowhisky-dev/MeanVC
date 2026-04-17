"""Theme and styling for MeanVC GUI."""

from PySide6.QtGui import QColor, QPalette
from PySide6.QtCore import Qt


# Color scheme matching rvc-web dark theme
COLORS = {
    "background": "#09090b",
    "surface": "#18181b",
    "surface_variant": "#27272a",
    "primary": "#22d3ee",
    "primary_dark": "#0891b2",
    "secondary": "#818cf8",
    "tertiary": "#a78bfa",
    "text": "#f4f4f5",
    "text_secondary": "#a1a1aa",
    "text_muted": "#71717a",
    "success": "#4ade80",
    "warning": "#fbbf24",
    "error": "#f87171",
    "border": "#3f3f46",
}


def get_dark_palette():
    """Create dark theme palette.

    Returns:
        QPalette: Dark theme palette
    """
    palette = QPalette()

    # Background
    palette.setColor(QPalette.ColorRole.Window, QColor(COLORS["background"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(COLORS["text"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(COLORS["surface"]))
    palette.setColor(
        QPalette.ColorRole.AlternateBase, QColor(COLORS["surface_variant"])
    )

    # Text
    palette.setColor(QPalette.ColorRole.Text, QColor(COLORS["text"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(COLORS["text"]))

    # Buttons
    palette.setColor(QPalette.ColorRole.Button, QColor(COLORS["surface_variant"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(COLORS["text"]))

    # Highlights
    palette.setColor(QPalette.ColorRole.Highlight, QColor(COLORS["primary"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(COLORS["background"]))

    # Links
    palette.setColor(QPalette.ColorRole.Link, QColor(COLORS["primary"]))
    palette.setColor(QPalette.ColorRole.LinkVisited, QColor(COLORS["secondary"]))

    return palette


def get_button_style():
    """Get QSS for primary button.

    Returns:
        str: Button stylesheet
    """
    return f"""
    QPushButton {{
        background-color: {COLORS["primary_dark"]};
        color: {COLORS["text"]};
        border: none;
        padding: 8px 16px;
        border-radius: 6px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background-color: {COLORS["primary"]};
        color: {COLORS["background"]};
    }}
    QPushButton:disabled {{
        background-color: {COLORS["surface_variant"]};
        color: {COLORS["text_muted"]};
    }}
    """


def get_card_style():
    """Get QSS for card container.

    Returns:
        str: Card stylesheet
    """
    return f"""
    QWidget {{
        background-color: {COLORS["surface_variant"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 8px;
    }}
    """


def get_nav_style():
    """Get QSS for navigation.

    Returns:
        str: Navigation stylesheet
    """
    return f"""
    QListWidget {{
        background-color: {COLORS["surface"]};
        border: none;
        color: {COLORS["text"]};
    }}
    QListWidget::item {{
        padding: 12px;
        border-radius: 4px;
    }}
    QListWidget::item:selected {{
        background-color: {COLORS["surface_variant"]};
        color: {COLORS["primary"]};
    }}
    QListWidget::item:hover {{
        background-color: {COLORS["surface_variant"]};
    }}
    """
