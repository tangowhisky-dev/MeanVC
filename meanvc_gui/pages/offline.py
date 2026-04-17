"""Offline conversion page for batch processing."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QFileDialog,
    QProgressBar,
    QGroupBox,
    QSlider,
    QComboBox,
)
from PySide6.QtCore import Qt, QThread, Signal

from meanvc_gui.components.theme import COLORS, get_button_style
from meanvc_gui.core.engine import get_engine


class ConversionWorker(QThread):
    """Background conversion worker."""

    progress = Signal(int)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, source, ref, model_type, steps):
        super().__init__()
        self.source = source
        self.ref = ref
        self.model_type = model_type
        self.steps = steps

    def run(self):
        try:
            engine = get_engine()
            output = engine.convert(self.source, self.ref, self.model_type, self.steps)
            self.finished.emit(output)
        except Exception as e:
            self.error.emit(str(e))


class OfflinePage(QWidget):
    """Offline batch conversion page."""

    def __init__(self, app):
        """Initialize offline page.

        Args:
            app: Main window reference
        """
        super().__init__()
        self.app = app
        self.source_path = ""
        self.reference_path = ""
        self.converting = False
        self._setup_ui()

    def _setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Offline Conversion")
        title.setStyleSheet(
            f"font-size: 24px; color: {COLORS['text']}; font-weight: 300;"
        )
        layout.addWidget(title)
        layout.addSpacing(20)

        # File selection group
        file_group = QGroupBox("Audio Files")
        file_layout = QVBoxLayout()

        # Source file
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("Source:"))
        self.source_edit = QLineEdit()
        self.source_edit.setPlaceholderText("Select source audio file...")
        source_layout.addWidget(self.source_edit, 1)
        source_btn = QPushButton("Browse")
        source_btn.clicked.connect(self._pick_source)
        source_layout.addWidget(source_btn)
        file_layout.addLayout(source_layout)

        # Reference file
        ref_layout = QHBoxLayout()
        ref_layout.addWidget(QLabel("Reference:"))
        self.ref_edit = QLineEdit()
        self.ref_edit.setPlaceholderText("Select reference audio file...")
        ref_layout.addWidget(self.ref_edit, 1)
        ref_btn = QPushButton("Browse")
        ref_btn.clicked.connect(self._pick_reference)
        ref_layout.addWidget(ref_btn)
        file_layout.addLayout(ref_layout)

        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        layout.addSpacing(15)

        # Settings group
        settings_group = QGroupBox("Settings")
        settings_layout = QVBoxLayout()

        # Model type
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["200ms (Faster)", "160ms (Higher Quality)"])
        model_layout.addWidget(self.model_combo)
        model_layout.addStretch()
        settings_layout.addLayout(model_layout)

        # Steps slider
        steps_layout = QHBoxLayout()
        steps_layout.addWidget(QLabel("Steps:"))
        self.steps_slider = QSlider(Qt.Horizontal)
        self.steps_slider.setMinimum(1)
        self.steps_slider.setMaximum(10)
        self.steps_slider.setValue(1)
        self.steps_label = QLabel("1")
        steps_layout.addWidget(self.steps_slider)
        steps_layout.addWidget(self.steps_label)
        settings_layout.addLayout(steps_layout)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        layout.addSpacing(15)

        # Actions
        action_layout = QHBoxLayout()
        self.convert_btn = QPushButton("Convert")
        self.convert_btn.setStyleSheet(get_button_style())
        self.convert_btn.clicked.connect(self._start_conversion)
        action_layout.addWidget(self.convert_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        action_layout.addWidget(self.stop_btn)
        action_layout.addStretch()

        layout.addLayout(action_layout)

        # Progress
        self.progress = QProgressBar()
        layout.addWidget(self.progress)

        # Result
        self.result_label = QLabel("")
        self.result_label.setStyleSheet(f"color: {COLORS['success']};")
        layout.addWidget(self.result_label)

        layout.addStretch()

    def _pick_source(self):
        """Pick source audio file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Source Audio", "", "Audio Files (*.wav *.mp3 *.flac *.ogg)"
        )
        if path:
            self.source_path = path
            self.source_edit.setText(path)

    def _pick_reference(self):
        """Pick reference audio file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Reference Audio", "", "Audio Files (*.wav *.mp3 *.flac *.ogg)"
        )
        if path:
            self.reference_path = path
            self.ref_edit.setText(path)

    def _start_conversion(self):
        """Start conversion."""
        if not self.source_path or not self.reference_path:
            self.result_label.setText("Please select both source and reference files")
            self.result_label.setStyleSheet(f"color: {COLORS['error']};")
            return

        self.converting = True
        self.convert_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress.setValue(0)
        self.result_label.setText("")

        model_type = "200ms" if self.model_combo.currentIndex() == 0 else "160ms"
        steps = self.steps_slider.value()

        self.worker = ConversionWorker(
            self.source_path, self.reference_path, model_type, steps
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, value):
        """Handle progress update."""
        self.progress.setValue(value)

    def _on_finished(self, output_path):
        """Handle conversion finished."""
        self.converting = False
        self.convert_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress.setValue(100)
        self.result_label.setText(f"Converted: {output_path}")
        self.result_label.setStyleSheet(f"color: {COLORS['success']};")

    def _on_error(self, error):
        """Handle conversion error."""
        self.converting = False
        self.convert_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.result_label.setText(f"Error: {error}")
        self.result_label.setStyleSheet(f"color: {COLORS['error']};")
