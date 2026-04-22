"""MeanVC Desktop Application — main entry point."""

from __future__ import annotations

import sys

from meanvc_gui import APP_DESCRIPTION, APP_NAME, APP_VERSION
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from meanvc_gui.components.theme import COLORS, get_dark_palette, get_nav_style, get_stylesheet
from meanvc_gui.core.device import get_current_device
from meanvc_gui.pages.library import LibraryPage
from meanvc_gui.pages.realtime import RealtimePage
from meanvc_gui.pages.offline import OfflinePage
from meanvc_gui.pages.analysis import AnalysisPage
from meanvc_gui.pages.settings import SettingsPage


_APP_VERSION = "0.1.0"

# ---------------------------------------------------------------------------
# Cross-page event bus
# ---------------------------------------------------------------------------

class AppBus(QObject):
    """Application-level signal bus for cross-page communication."""
    profile_selected   = Signal(dict)    # emitted by Library → consumed by Offline, Realtime
    analysis_requested = Signal(str)     # emitted by Offline (output_path) → Analysis
    navigate_to        = Signal(int)     # navigate to page index

bus = AppBus()


# ---------------------------------------------------------------------------
# Sidebar navigation item
# ---------------------------------------------------------------------------

_NAV_ITEMS = [
    ("📚", "Library"),
    ("🎙", "Realtime"),
    ("🔄", "Offline"),
    ("📊", "Analysis"),
    ("⚙", "Settings"),
]


class NavItem(QFrame):
    clicked = Signal(int)

    def __init__(self, icon: str, label: str, index: int, parent=None):
        super().__init__(parent)
        self._index = index
        self._selected = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(44)

        row = QHBoxLayout(self)
        row.setContentsMargins(16, 0, 16, 0)
        row.setSpacing(12)

        self._icon = QLabel(icon)
        self._icon.setFixedWidth(20)
        self._icon.setAlignment(Qt.AlignCenter)
        self._icon.setStyleSheet("font-size: 16px; background: transparent;")
        row.addWidget(self._icon)

        self._label = QLabel(label)
        self._label.setStyleSheet(
            f"font-size: 13px; font-weight: 500; color: {COLORS['text_secondary']}; background: transparent;"
        )
        row.addWidget(self._label)
        row.addStretch()

        self._update_style()

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._update_style()

    def _update_style(self) -> None:
        if self._selected:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['nav_active_bg']};
                    /* border-left: 2px solid {COLORS['primary']}; */
                    border-radius: 0;
                }}
            """)
            self._label.setStyleSheet(
                f"font-size: 13px; font-weight: 600; color: {COLORS['primary']}; background: transparent;"
            )
        else:
            self.setStyleSheet("QFrame { background: transparent; border: none; }")
            self._label.setStyleSheet(
                f"font-size: 13px; font-weight: 500; color: {COLORS['text_secondary']}; background: transparent;"
            )

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        self.clicked.emit(self._index)
        super().mousePressEvent(event)


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MeanVCWindow(QMainWindow):
    """Application main window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1100, 720)
        self.resize(1280, 820)

        self.setPalette(get_dark_palette())
        self.setStyleSheet(get_stylesheet())

        # Current profile — set by Library page
        self.current_profile: dict | None = None

        self._build_ui()
        self._register_shortcuts()
        self._navigate(0)

        # Asset check after window is shown
        from PySide6.QtCore import QTimer
        QTimer.singleShot(500, self._check_assets_on_startup)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- Sidebar ---
        sidebar = QFrame()
        sidebar.setFixedWidth(200)
        sidebar.setObjectName("Sidebar")
        sidebar.setStyleSheet(f"""
            #Sidebar {{
                background-color: {COLORS['nav_bg']};
                border-right: 1px solid {COLORS['border']};
            }}
        """)

        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(0, 0, 0, 0)
        sb_layout.setSpacing(0)

        # Logo / title
        logo_area = QWidget()
        logo_area.setFixedHeight(60)
        logo_layout = QHBoxLayout(logo_area)
        logo_layout.setContentsMargins(20, 0, 12, 0)
        logo_label = QLabel(APP_NAME)
        logo_label.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {COLORS['primary']}; letter-spacing: -0.03em;"
        )
        logo_layout.addWidget(logo_label)
        logo_layout.addStretch()
        sb_layout.addWidget(logo_area)

        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background: {COLORS['border']};")
        sb_layout.addWidget(div)
        sb_layout.addSpacing(8)

        # Nav items
        self._nav_items: list[NavItem] = []
        for i, (icon, label) in enumerate(_NAV_ITEMS):
            item = NavItem(icon, label, i)
            item.clicked.connect(self._navigate)
            sb_layout.addWidget(item)
            self._nav_items.append(item)

        sb_layout.addStretch()

        # Bottom: device badge + version
        bottom = QWidget()
        bottom.setFixedHeight(64)
        bot_layout = QVBoxLayout(bottom)
        bot_layout.setContentsMargins(20, 8, 20, 8)
        bot_layout.setSpacing(2)

        device = get_current_device().upper()
        device_badge = QLabel(f"● {device}")
        badge_color = (
            COLORS["success"] if device == "CUDA"
            else COLORS["warning"] if device == "MPS"
            else COLORS["text_muted"]
        )
        device_badge.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {badge_color}; background: transparent;"
        )
        bot_layout.addWidget(device_badge)

        version_lbl = QLabel(f"v{_APP_VERSION}")
        version_lbl.setStyleSheet(
            f"font-size: 10px; color: {COLORS['text_muted']}; background: transparent;"
        )
        bot_layout.addWidget(version_lbl)

        sb_layout.addWidget(bottom)
        root_layout.addWidget(sidebar)

        # --- Content area ---
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("QStackedWidget { background: transparent; }")
        root_layout.addWidget(self._stack, 1)

        # Initialise pages
        self._pages = [
            LibraryPage(self),
            RealtimePage(self),
            OfflinePage(self),
            AnalysisPage(self),
            SettingsPage(self),
        ]
        for page in self._pages:
            self._stack.addWidget(page)

        # Wire cross-page bus
        bus.navigate_to.connect(self._navigate)

    def _register_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self.close)
        for i in range(5):
            QShortcut(QKeySequence(f"Ctrl+{i+1}"), self).activated.connect(
                lambda checked=False, idx=i: self._navigate(idx)
            )

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _navigate(self, index: int) -> None:
        if not (0 <= index < len(self._pages)):
            return
        self._stack.setCurrentIndex(index)
        for i, item in enumerate(self._nav_items):
            item.set_selected(i == index)

    # ------------------------------------------------------------------
    # Startup asset check
    # ------------------------------------------------------------------

    def _check_assets_on_startup(self) -> None:
        try:
            from meanvc_gui.core.engine import check_assets
            results = check_assets()
            missing = [name for name, info in results.items() if not info["exists"]]
            if missing:
                msg = QMessageBox(self)
                msg.setWindowTitle(f"{APP_NAME} — Missing Assets")
                msg.setIcon(QMessageBox.Warning)
                msg.setText(
                    f"{len(missing)} required model file(s) missing.\n"
                    "The app will open but conversion will not work until assets are downloaded."
                )
                msg.setInformativeText("Click 'Open Settings' to download missing assets.")
                open_btn = msg.addButton("Open Settings", QMessageBox.AcceptRole)
                msg.addButton("Dismiss", QMessageBox.RejectRole)
                msg.exec()
                if msg.clickedButton() == open_btn:
                    self._navigate(4)  # Settings page
        except Exception:
            pass  # engine import may fail if deps not met — silent here


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("-apple-system", 13))

    window = MeanVCWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
