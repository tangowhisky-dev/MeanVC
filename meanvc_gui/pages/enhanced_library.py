"""
Enhanced Library Page with professional styling.

Features:
- Consistent card design
- Smooth hover effects
- Better proportions
- Improved visual hierarchy
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QGroupBox,
    QTableWidget,
    QTableWidgetItem,
    QFileDialog,
    QInputDialog,
    QMessageBox,
    QFrame,
    QScrollArea,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QLinearGradient, QBrush, QColor

from meanvc_gui.components.enhanced_theme import _DARK_COLORS
from meanvc_gui.core.profile_manager import get_profile_manager


class EnhancedProfileCard(QFrame):
    """Modern profile card with smooth transitions."""
    
    selected = Signal(str)
    
    def __init__(self, profile: dict, parent=None):
        super().__init__(parent)
        self.profile = profile
        self._selected = False
        self._setup_ui()
    
    def _setup_ui(self):
        colors = _DARK_COLORS
        
        self.setFixedHeight(112)
        self.setCursor(Qt.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Name row
        name_row = QHBoxLayout()
        
        name_label = QLabel(self.profile.get("name", "Untitled"))
        name_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 600;
            color: {colors["text_primary"]};
            letter-spacing: -0.01em;
        """)
        name_row.addWidget(name_label)
        
        name_row.addStretch()
        
        # Duration badge with better styling
        duration = self.profile.get("total_audio_duration", 0)
        duration_label = QLabel(f"🕐 {duration:.0f}s")
        duration_label.setStyleSheet(f"""
            font-size: 13px;
            color: {colors["text_secondary"]};
            background: {colors["surface_elevated"]};
            padding: 6px 12px;
            border-radius: 20px;
            border: 1px solid {colors["border_faint"]};
        """)
        name_row.addWidget(duration_label)
        
        layout.addLayout(name_row)
        
        # Stats row
        stats_row = QHBoxLayout()
        
        files = self.profile.get("num_audio_files", 0)
        files_label = QLabel(f"📁 {files} audio files")
        files_label.setStyleSheet(f"""
            font-size: 13px;
            color: {colors["text_tertiary"]};
        """)
        stats_row.addWidget(files_label)
        
        stats_row.addStretch()
        
        # Created date
        created = self.profile.get("created_at", "")[:10]
        date_label = QLabel(f"📅 {created}")
        date_label.setStyleSheet(f"""
            font-size: 13px;
            color: {colors["text_tertiary"]};
        """)
        stats_row.addWidget(date_label)
        
        layout.addLayout(stats_row)
        
        self.setStyleSheet(f"""
            QFrame {{
                background: {colors["surface_card"]};
                border: 1px solid {colors["border_faint"]};
                border-radius: 14px;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
            }}
        """)
    
    def set_selected(self, selected: bool):
        self._selected = selected
        colors = _DARK_COLORS
        
        if selected:
            self.setStyleSheet(f"""
                QFrame {{
                    background: {colors["selection"]};
                    border: 2px solid {colors["primary"]};
                    border-radius: 14px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background: {colors["surface_card"]};
                    border: 1px solid {colors["border_faint"]};
                    border-radius: 14px;
                }}
            """)
    
    def mousePressEvent(self, event):
        self.selected.emit(self.profile["id"])
        super().mousePressEvent(event)


class LibraryPage(QWidget):
    """Enhanced library page for voice profile management."""
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.profile_manager = get_profile_manager()
        self.current_profile = None
        self._setup_ui()
        self._load_profiles()
    
    def _setup_ui(self):
        colors = _DARK_COLORS
        
        self.setStyleSheet(f"background: {colors['bg_primary']};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(24)
        
        # Header section with better proportions
        header = QHBoxLayout()
        
        title = QLabel("Voice Profiles")
        title.setStyleSheet(f"""
            font-size: 32px;
            font-weight: 700;
            color: {colors["text_primary"]};
            letter-spacing: -0.03em;
        """)
        header.addWidget(title)
        
        header.addStretch()
        
        # Add button with enhanced styling
        add_btn = QPushButton("➕ New Profile")
        add_btn.setProperty("primary", True)
        add_btn.setFixedHeight(44)
        add_btn.setFixedWidth(160)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors["primary"]};
                color: {colors["text_inverse"]};
                border: none;
                padding: 12px 24px;
                border-radius: 10px;
                font-weight: 600;
                font-size: 14px;
                box-shadow: 0 2px 8px {colors["primary_glow"]};
            }}
            QPushButton:hover {{
                background-color: {colors["primary_light"]};
                box-shadow: 0 4px 12px {colors["primary_glow"]};
            }}
            QPushButton:pressed {{
                background-color: {colors["primary_darker"]};
            }}
        """)
        add_btn.clicked.connect(self._new_profile)
        header.addWidget(add_btn)
        
        layout.addLayout(header)
        
        # Content area with grid layout
        content = QHBoxLayout()
        content.setSpacing(24)
        
        # Left panel - Profiles list
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        
        # Scroll area with custom styling
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                width: 6px;
                background: transparent;
            }}
            QScrollBar::handle:vertical {{
                background: {colors["border"]};
                border-radius: 3px;
                margin: 24px 0;
            }}
        """)
        
        self.profiles_container = QWidget()
        self.profiles_layout = QVBoxLayout(self.profiles_container)
        self.profiles_layout.setContentsMargins(0, 0, 0, 0)
        self.profiles_layout.setSpacing(12)
        
        scroll.setWidget(self.profiles_container)
        
        left_layout.addWidget(scroll)
        left_panel.setFixedWidth(380)
        
        content.addWidget(left_panel)
        
        # Right panel - Details
        self.details_panel = QFrame()
        self.details_panel.setFixedWidth(420)
        details_layout = QVBoxLayout(self.details_panel)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(20)
        
        # Profile details card with elevation
        details_card = QFrame()
        details_card.setStyleSheet(f"""
            QFrame {{
                background: {colors["surface_card"]};
                border: 1px solid {colors["border_faint"]};
                border-radius: 16px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
            }}
        """)
        card_layout = QVBoxLayout(details_card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(16)
        
        # Card header
        card_header = QHBoxLayout()
        card_title = QLabel("Profile Details")
        card_title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 600;
            color: {colors["text_primary"]};
        """)
        card_header.addWidget(card_title)
        card_header.addStretch()
        card_layout.addLayout(card_header)
        
        # Details info
        self.details_info = QVBoxLayout()
        self.details_info.setSpacing(12)
        card_layout.addLayout(self.details_info)
        
        details_layout.addWidget(details_card)
        
        # Audio files card
        audio_card = QFrame()
        audio_card.setStyleSheet(f"""
            QFrame {{
                background: {colors["surface_card"]};
                border: 1px solid {colors["border_faint"]};
                border-radius: 16px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
            }}
        """)
        audio_layout = QVBoxLayout(audio_card)
        audio_layout.setContentsMargins(24, 24, 24, 24)
        audio_layout.setSpacing(16)
        
        audio_header = QHBoxLayout()
        audio_title = QLabel("Audio Files")
        audio_title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 600;
            color: {colors["text_primary"]};
        """)
        audio_header.addWidget(audio_title)
        audio_header.addStretch()
        
        add_audio_btn = QPushButton("➕ Add")
        add_audio_btn.setFixedSize(70, 36)
        add_audio_btn.clicked.connect(self._add_audio)
        audio_header.addWidget(add_audio_btn)
        
        audio_layout.addLayout(audio_header)
        
        # Audio list
        self.audio_list = QListWidget()
        self.audio_list.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: none;
            }}
            QListWidget::item {{
                background: {colors["surface_elevated"]};
                color: {colors["text_primary"]};
                padding: 14px;
                border-radius: 8px;
                margin-bottom: 8px;
                border: 1px solid {colors["border_faint"]};
            }}
        """)
        audio_layout.addWidget(self.audio_list)
        
        details_layout.addWidget(audio_card)
        
        # Actions section
        actions = QHBoxLayout()
        actions.setSpacing(12)
        
        use_btn = QPushButton("Use for Conversion")
        use_btn.setProperty("primary", True)
        use_btn.setFixedHeight(44)
        use_btn.clicked.connect(self._use_profile)
        actions.addWidget(use_btn)
        
        delete_btn = QPushButton("Delete")
        delete_btn.setFixedHeight(44)
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                background: {colors["error_bg"]};
                color: {colors["error"]};
                border: 1px solid {colors["error"]};
            }}
            QPushButton:hover {{
                background: {colors["error"]};
                color: {colors["text_inverse"]};
            }}
        """)
        delete_btn.clicked.connect(self._delete_profile)
        actions.addWidget(delete_btn)
        
        actions.addStretch()
        
        details_layout.addLayout(actions)
        
        content.addWidget(self.details_panel)
        
        layout.addLayout(content)
        layout.addStretch()
    
    def _load_profiles(self):
        """Load profiles from database."""
        # Clear existing
        while self.profiles_layout.count():
            item = self.profiles_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        profiles = self.profile_manager.list_profiles()
        
        for profile in profiles:
            card = EnhancedProfileCard(profile)
            card.selected.connect(self._on_profile_selected)
            self.profiles_layout.addWidget(card)
        
        if profiles:
            self._on_profile_selected(profiles[0]["id"])
        else:
            self.current_profile = None
            if hasattr(self, "audio_list"):
                self._show_details_placeholder()
    
    def _on_profile_selected(self, profile_id: str):
        """Handle profile selection."""
        # Update card selection
        for i in range(self.profiles_layout.count()):
            widget = self.profiles_layout.itemAt(i).widget()
            if isinstance(widget, EnhancedProfileCard):
                widget.set_selected(widget.profile["id"] == profile_id)
        
        self.current_profile = self.profile_manager.get_profile(profile_id)
        self._update_details()
        self._update_audio_list()
    
    def _update_details(self):
        """Update profile details."""
        colors = _DARK_COLORS
        
        # Clear existing
        while self.details_info.count():
            item = self.details_info.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self.current_profile:
            self._show_details_placeholder()
            return
        
        profile = self.current_profile
        
        # Name
        self._add_detail_row("Name", profile.get("name", "Untitled"))
        
        # Description
        desc = profile.get("description", "")
        if desc:
            self._add_detail_row("Description", desc)
        
        # Audio files
        self._add_detail_row("Audio Files", str(profile.get("num_audio_files", 0)))
        
        # Duration
        duration = profile.get("total_audio_duration", 0)
        self._add_detail_row("Total Duration", f"{duration:.1f} seconds")
        
        # Created
        created = profile.get("created_at", "")[:19].replace("T", " ")
        self._add_detail_row("Created", created)
    
    def _add_detail_row(self, label: str, value: str):
        """Add a detail row."""
        colors = _DARK_COLORS
        
        row = QHBoxLayout()
        row.setSpacing(12)
        
        lbl = QLabel(label)
        lbl.setStyleSheet(f"""
            font-size: 13px;
            color: {colors["text_secondary"]};
        """)
        lbl.setFixedWidth(110)
        row.addWidget(lbl)
        
        val = QLabel(value)
        val.setStyleSheet(f"""
            font-size: 13px;
            color: {colors["text_primary"]};
            font-weight: 500;
        """)
        row.addWidget(val)
        
        row.addStretch()
        
        self.details_info.addLayout(row)
    
    def _show_details_placeholder(self):
        """Show placeholder when no profile selected."""
        colors = _DARK_COLORS
        
        while self.details_info.count():
            item = self.details_info.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        placeholder = QLabel("Select a profile to view details")
        placeholder.setStyleSheet(f"""
            font-size: 14px;
            color: {colors["text_tertiary"]};
            padding: 40px;
        """)
        self.details_info.addWidget(placeholder)
        
        self.audio_list.clear()
    
    def _update_audio_list(self):
        """Update audio files list."""
        colors = _DARK_COLORS
        
        self.audio_list.clear()
        
        if not self.current_profile:
            return
        
        for audio in self.current_profile.get("audio_files", []):
            filename = audio.get("filename", "Unknown")
            duration = audio.get("duration", 0)
            default_mark = " ★" if audio.get("is_default") else ""
            
            item = QListWidgetItem(f"🎵 {filename} ({duration:.1f}s){default_mark}")
            item.setData(Qt.UserRole, audio["id"])
            self.audio_list.addItem(item)
    
    def _new_profile(self):
        """Create new profile."""
        name, ok = QInputDialog.getText(self, "New Profile", "Profile Name:")
        if not ok or not name.strip():
            return
        
        description, _ = QInputDialog.getText(
            self, "New Profile", "Description (optional):"
        )
        if not description:
            description = ""
        
        profile = self.profile_manager.create_profile(name.strip(), description)
        self._load_profiles()
