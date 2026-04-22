"""
MeanVC Design System — single authoritative theme module.

All pages import from here. No inline hex strings allowed in page files.

Usage:
    from meanvc_gui.components.theme import (
        COLORS, get_stylesheet, get_dark_palette,
        CardFrame, PrimaryButton, SecondaryButton, DangerButton,
        SectionTitle, BodyLabel, SecondaryLabel,
        PageContainer,
    )
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QWidget,
    QVBoxLayout,
)

# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------

COLORS: dict[str, str] = {
    # ── 60 % neutral background ───────────────────────────────────────
    "background":       "#121212",   # deep charcoal — main window
    "nav_bg":           "#1A1A1A",   # sidebar — slightly lighter than bg

    # ── 30 % secondary surfaces ──────────────────────────────────────
    "surface":          "#252525",   # cards, panels
    "surface_variant":  "#2C2C2C",   # inputs, list items
    "surface_hover":    "#333333",   # hover state on surface items

    # ── 10 % accent (Pearl Aqua) ────────────────────────────────────
    "primary":          "#84DCC6",   # Pearl Aqua
    "primary_dark":     "#5BBFA8",   # darker Pearl Aqua — hover / pressed
    "primary_muted":    "rgba(132, 220, 198, 0.12)", # ~12 % alpha fill

    # ── Text (off-white hierarchy) ───────────────────────────────────
    "text":             "#E0E0E0",   # primary — off-white (not pure white)
    "text_secondary":   "#9E9E9E",   # labels, secondary info
    "text_muted":       "#616161",   # placeholders, disabled

    # ── Semantic colours ─────────────────────────────────────────────
    "success":          "#84DCC6",   # reuse accent for success
    "success_bg":       "#84DCC618",
    "warning":          "#FFD740",   # amber
    "warning_bg":       "#FFD74018",
    "error":            "#FF5252",   # red-400
    "error_bg":         "#FF525218",
    "info":             "#40C4FF",   # light blue
    "info_bg":          "#40C4FF18",

    # ── Borders ──────────────────────────────────────────────────────
    "border":           "#383838",   # subtle divider on dark surfaces
    "border_focus":     "#84DCC6",   # accent border on focus

    # ── Nav active state ─────────────────────────────────────────────
    "nav_active_bg":    "rgba(132, 220, 198, 0.15)",
    "nav_active_border":"#84DCC6",
}


# ---------------------------------------------------------------------------
# QPalette
# ---------------------------------------------------------------------------

def get_dark_palette() -> QPalette:
    """Return a QPalette matching the COLORS dict for Fusion style."""
    p = QPalette()
    bg   = QColor(COLORS["background"])
    surf = QColor(COLORS["surface"])
    text = QColor(COLORS["text"])
    sec  = QColor(COLORS["text_secondary"])
    pri  = QColor(COLORS["primary"])
    brd  = QColor(COLORS["border"])

    p.setColor(QPalette.Window,          bg)
    p.setColor(QPalette.WindowText,      text)
    p.setColor(QPalette.Base,            surf)
    p.setColor(QPalette.AlternateBase,   QColor(COLORS["surface_variant"]))
    p.setColor(QPalette.ToolTipBase,     surf)
    p.setColor(QPalette.ToolTipText,     text)
    p.setColor(QPalette.Text,            text)
    p.setColor(QPalette.Button,          surf)
    p.setColor(QPalette.ButtonText,      text)
    p.setColor(QPalette.BrightText,      pri)
    p.setColor(QPalette.Link,            pri)
    p.setColor(QPalette.Highlight,       pri)
    p.setColor(QPalette.HighlightedText, QColor(COLORS["background"]))
    p.setColor(QPalette.Disabled, QPalette.Text, sec)
    p.setColor(QPalette.Disabled, QPalette.ButtonText, sec)
    return p


# ---------------------------------------------------------------------------
# Global QSS stylesheet
# ---------------------------------------------------------------------------

def get_stylesheet() -> str:
    C = COLORS
    return f"""
    /* ---- Window / Widget base ---- */
    QMainWindow, QWidget {{
        background-color: {C['background']};
        color: {C['text']};
        font-family: -apple-system, "SF Pro Text", "Segoe UI", "Ubuntu", sans-serif;
        font-size: 13px;
    }}

    /* ---- GroupBox ---- */
    QGroupBox {{
        border: 1px solid {C['border']};
        border-radius: 8px;
        margin-top: 16px;
        padding-top: 8px;
        font-weight: 600;
        color: {C['text_secondary']};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 6px;
        color: {C['text_secondary']};
        font-size: 12px;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }}

    /* ---- Labels ---- */
    QLabel {{
        color: {C['text']};
        background: transparent;
    }}

    /* ---- Text inputs ---- */
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {C['surface_variant']};
        border: 1px solid {C['border']};
        border-radius: 6px;
        padding: 7px 10px;
        color: {C['text']};
        selection-background-color: {C['primary_muted']};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border-color: {C['border_focus']};
        outline: none;
    }}
    QLineEdit:disabled {{
        color: {C['text_muted']};
        background-color: {C['surface']};
    }}

    /* ---- Buttons (default / secondary) ---- */
    QPushButton {{
        background-color: {C['surface_variant']};
        color: {C['text']};
        border: 1px solid {C['border']};
        padding: 7px 16px;
        border-radius: 6px;
        font-weight: 500;
        min-width: 64px;
    }}
    QPushButton:hover {{
        background-color: {C['surface_hover']};
        border-color: {C['text_muted']};
    }}
    QPushButton:pressed {{
        background-color: {C['surface']};
    }}
    QPushButton:disabled {{
        color: {C['text_muted']};
        background-color: {C['surface']};
        border-color: {C['surface_variant']};
    }}

    /* ---- Primary button (accent) ---- */
    QPushButton[primary="true"] {{
        background-color: {C['primary']};
        color: {C['background']};
        border: none;
        font-weight: 600;
    }}
    QPushButton[primary="true"]:hover {{
        background-color: {C['primary_dark']};
    }}
    QPushButton[primary="true"]:pressed {{
        background-color: {C['primary_dark']};
        opacity: 0.9;
    }}
    QPushButton[primary="true"]:disabled {{
        background-color: {C['surface_variant']};
        color: {C['text_muted']};
    }}

    /* ---- Danger button ---- */
    QPushButton[danger="true"] {{
        background-color: #3B1A1A;
        color: {C['error']};
        border: 1px solid #6B2A2A;
        font-weight: 600;
    }}
    QPushButton[danger="true"]:hover {{
        background-color: #5C2222;
        color: #FF8A80;
        border-color: {C['error']};
    }}
    QPushButton[danger="true"]:pressed {{
        background-color: #7A2B2B;
        color: #FFCDD2;
        border-color: {C['error']};
    }}
    QPushButton[danger="true"]:disabled {{
        background-color: {C['surface_variant']};
        color: {C['text_muted']};
        border-color: {C['border']};
    }}

    /* ---- ComboBox ---- */
    QComboBox {{
        background-color: {C['surface_variant']};
        border: 1px solid {C['border']};
        border-radius: 6px;
        padding: 7px 10px;
        color: {C['text']};
        min-width: 80px;
    }}
    QComboBox:hover {{
        border-color: {C['text_muted']};
    }}
    QComboBox:focus {{
        border-color: {C['border_focus']};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {C['text_secondary']};
        margin-right: 8px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {C['surface']};
        border: 1px solid {C['border']};
        border-radius: 6px;
        color: {C['text']};
        selection-background-color: {C['surface_variant']};
        outline: none;
    }}

    /* ---- Slider ---- */
    QSlider::groove:horizontal {{
        background: {C['surface_variant']};
        height: 4px;
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {C['primary']};
        width: 14px;
        height: 14px;
        margin: -5px 0;
        border-radius: 7px;
    }}
    QSlider::handle:horizontal:hover {{
        background: {C['primary_dark']};
    }}
    QSlider::sub-page:horizontal {{
        background: {C['primary']};
        border-radius: 2px;
    }}

    /* ---- ProgressBar ---- */
    QProgressBar {{
        background-color: {C['surface_variant']};
        border: none;
        border-radius: 4px;
        height: 6px;
        text-align: center;
        color: transparent;
    }}
    QProgressBar::chunk {{
        background-color: {C['primary']};
        border-radius: 4px;
    }}

    /* ---- ListWidget ---- */
    QListWidget {{
        background-color: {C['surface']};
        border: 1px solid {C['border']};
        border-radius: 8px;
        color: {C['text']};
        outline: none;
    }}
    QListWidget::item {{
        padding: 10px 12px;
        border-radius: 6px;
        margin: 2px 4px;
        border: none;
    }}
    QListWidget::item:hover {{
        background-color: {C['surface_variant']};
    }}
    QListWidget::item:selected {{
        background-color: {C['primary_muted']};
        color: {C['text']};
        border-left: 2px solid {C['primary']};
        padding-left: 10px;
    }}

    /* ---- TableWidget ---- */
    QTableWidget {{
        background-color: {C['surface']};
        border: 1px solid {C['border']};
        border-radius: 8px;
        color: {C['text']};
        gridline-color: {C['border']};
        outline: none;
    }}
    QTableWidget::item {{
        padding: 8px 12px;
    }}
    QTableWidget::item:selected {{
        background-color: {C['primary_muted']};
        color: {C['text']};
    }}
    QHeaderView::section {{
        background-color: {C['surface_variant']};
        color: {C['text_secondary']};
        padding: 8px 12px;
        border: none;
        border-right: 1px solid {C['border']};
        font-weight: 600;
        font-size: 12px;
    }}

    /* ---- ScrollBar ---- */
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {C['border']};
        border-radius: 4px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {C['text_muted']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 8px;
    }}
    QScrollBar::handle:horizontal {{
        background: {C['border']};
        border-radius: 4px;
        min-width: 24px;
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}

    /* ---- ScrollArea ---- */
    QScrollArea {{
        background: transparent;
        border: none;
    }}

    /* ---- CheckBox ---- */
    QCheckBox {{
        color: {C['text']};
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 4px;
        border: 1px solid {C['border']};
        background: {C['surface_variant']};
    }}
    QCheckBox::indicator:checked {{
        background: {C['primary']};
        border-color: {C['primary']};
    }}
    QCheckBox::indicator:hover {{
        border-color: {C['text_muted']};
    }}

    /* ---- Splitter ---- */
    QSplitter::handle {{
        background: {C['border']};
        width: 1px;
    }}

    /* ---- ToolTip ---- */
    QToolTip {{
        background-color: {C['surface']};
        color: {C['text']};
        border: 1px solid {C['border']};
        border-radius: 4px;
        padding: 4px 8px;
    }}
    """


# ---------------------------------------------------------------------------
# Reusable widget classes
# ---------------------------------------------------------------------------

class CardFrame(QFrame):
    """A surface card with rounded border."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("CardFrame")
        self.setStyleSheet(f"""
            #CardFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
        """)


class PrimaryButton(QPushButton):
    """Accent-colored action button."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setProperty("primary", "true")
        self.setMinimumHeight(36)


class SecondaryButton(QPushButton):
    """Outlined secondary button."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setMinimumHeight(36)


class DangerButton(QPushButton):
    """Destructive action button."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setProperty("danger", "true")
        self.setMinimumHeight(36)


class SectionTitle(QLabel):
    """Page-level heading label."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            font-size: 22px;
            font-weight: 300;
            color: {COLORS['text']};
            letter-spacing: -0.02em;
            background: transparent;
        """)


class BodyLabel(QLabel):
    """Standard body text label."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setStyleSheet(f"color: {COLORS['text']}; font-size: 13px; background: transparent;")


class SecondaryLabel(QLabel):
    """Muted secondary label."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; background: transparent;")


class StatusBadge(QLabel):
    """Compact status indicator with colour-coded background."""

    @staticmethod
    def _make_styles() -> dict[str, str]:
        C = COLORS
        return {
            "ready":      f"background:{C['success_bg']}; color:{C['success']};",
            "extracting": f"background:{C['warning_bg']}; color:{C['warning']};",
            "failed":     f"background:{C['error_bg']}; color:{C['error']};",
            "pending":    f"background:{C['surface_variant']}; color:{C['text_muted']};",
            "missing":    f"background:{C['error_bg']}; color:{C['error']};",
        }
    _STYLES: dict[str, str] = {}  # populated after COLORS is defined

    def __init__(
        self, status: str = "pending", parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.set_status(status)

    def set_status(self, status: str) -> None:
        if not StatusBadge._STYLES:
            StatusBadge._STYLES = StatusBadge._make_styles()
        style = self._STYLES.get(status, self._STYLES["pending"])
        self.setText(status.capitalize())
        self.setStyleSheet(f"""
            {style}
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 11px;
            font-weight: 600;
        """)


class PageContainer(QWidget):
    """Standard page wrapper with 24px margins."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(24, 24, 24, 24)
        self._layout.setSpacing(16)

    @property
    def layout(self) -> QVBoxLayout:  # type: ignore[override]
        return self._layout


# ---------------------------------------------------------------------------
# Legacy helpers kept for backward compat
# ---------------------------------------------------------------------------

def get_nav_style() -> str:
    C = COLORS
    return f"""
    QListWidget {{
        background-color: {C['nav_bg']};
        border: none;
        outline: none;
        padding: 8px 0;
    }}
    QListWidget::item {{
        color: {C['text_secondary']};
        padding: 10px 20px;
        border-left: 3px solid transparent;
        border-radius: 0;
        margin: 1px 0;
        font-size: 13px;
        font-weight: 500;
    }}
    QListWidget::item:hover {{
        background-color: {C['surface_variant']};
        color: {C['text']};
    }}
    QListWidget::item:selected {{
        background-color: {C['nav_active_bg']};
        color: {C['primary']};
        # border-left: 3px solid {C['nav_active_border']};
    }}
    """


def get_button_style(primary: bool = True) -> str:
    """Legacy helper — prefer using PrimaryButton / SecondaryButton classes."""
    C = COLORS
    if primary:
        return f"""
        QPushButton {{
            background-color: {C['primary']};
            color: {C['background']};
            border: none;
            padding: 8px 18px;
            border-radius: 6px;
            font-weight: 600;
            min-height: 34px;
        }}
        QPushButton:hover {{ background-color: {C['primary_dark']}; }}
        QPushButton:disabled {{ background-color: {C['surface_variant']}; color: {C['text_muted']}; }}
        """
    return f"""
    QPushButton {{
        background-color: {C['surface_variant']};
        color: {C['text']};
        border: 1px solid {C['border']};
        padding: 8px 18px;
        border-radius: 6px;
        font-weight: 500;
    }}
    QPushButton:hover {{ background-color: {C['surface_hover']}; }}
    """
