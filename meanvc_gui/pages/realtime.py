"""Realtime conversion page for live voice conversion."""

import numpy as np

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QSlider,
    QGroupBox,
    QCheckBox,
)
from PySide6.QtCore import Qt, QTimer, QPointF, Slot
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtMultimedia import QAudioFormat, QAudioSource, QMediaDevices
from PySide6.QtGui import QBrush, QColor

from meanvc_gui.components.theme import COLORS, get_button_style
from meanvc_gui.core.engine import get_engine
from meanvc_gui.core.device import enumerate_audio_devices


class RealtimePage(QWidget):
    """Real-time voice conversion page."""

    def __init__(self, app):
        """Initialize realtime page.

        Args:
            app: Main window reference
        """
        super().__init__()
        self.app = app
        self.running = False
        self.save_output = False
        self._setup_ui()

    def _setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Realtime Conversion")
        title.setStyleSheet(
            f"font-size: 24px; color: {COLORS['text']}; font-weight: 300;"
        )
        layout.addWidget(title)
        layout.addSpacing(20)

        # Device selection
        device_group = QGroupBox("Audio Devices")
        device_layout = QVBoxLayout()

        # Input device
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Input:"))
        self.input_combo = QComboBox()
        input_layout.addWidget(self.input_combo)
        device_layout.addLayout(input_layout)

        # Output device
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output:"))
        self.output_combo = QComboBox()
        output_layout.addWidget(self.output_combo)
        device_layout.addLayout(output_layout)

        # Populate devices after both combos are created
        self._populate_devices()

        device_group.setLayout(device_layout)
        layout.addWidget(device_group)

        layout.addSpacing(15)

        # Conversion settings
        settings_group = QGroupBox("Conversion Settings")
        settings_layout = QVBoxLayout()

        # Pitch shift
        pitch_layout = QHBoxLayout()
        pitch_layout.addWidget(QLabel("Pitch Shift:"))
        self.pitch_slider = QSlider(Qt.Horizontal)
        self.pitch_slider.setMinimum(-12)
        self.pitch_slider.setMaximum(12)
        self.pitch_slider.setValue(0)
        self.pitch_label = QLabel("0")
        pitch_layout.addWidget(self.pitch_slider)
        pitch_layout.addWidget(self.pitch_label)
        settings_layout.addLayout(pitch_layout)

        # Model selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["200ms (Faster)", "160ms (Higher Quality)"])
        model_layout.addWidget(self.model_combo)
        model_layout.addStretch()
        settings_layout.addLayout(model_layout)

        # Steps
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

        # Control buttons
        control_layout = QHBoxLayout()

        self.start_btn = QPushButton("Start")
        self.start_btn.setStyleSheet(get_button_style())
        self.start_btn.clicked.connect(self._toggle_conversion)
        control_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_conversion)
        control_layout.addWidget(self.stop_btn)

        control_layout.addStretch()

        layout.addLayout(control_layout)

        # Save output checkbox
        self.save_checkbox = QCheckBox("Save output to file")
        self.save_checkbox.stateChanged.connect(self._on_save_change)
        layout.addWidget(self.save_checkbox)

        # Status
        self.status_label = QLabel("Ready to convert")
        self.status_label.setStyleSheet(f"color: {COLORS['success']};")
        layout.addWidget(self.status_label)

        # Waveform display using Qt Charts
        self._setup_waveform_chart()
        layout.addWidget(self.chart_view)

        layout.addStretch()

    def _setup_waveform_chart(self):
        """Setup real-time waveform chart."""
        SAMPLE_COUNT = 2000

        self._series = QLineSeries()
        self._buffer = [QPointF(x, 0) for x in range(SAMPLE_COUNT)]
        self._series.append(self._buffer)

        self._chart = QChart()
        self._chart.addSeries(self._series)

        self._axis_x = QValueAxis()
        self._axis_x.setRange(0, SAMPLE_COUNT)
        self._axis_x.setLabelFormat("%g")
        self._axis_x.setTitleText("Samples")

        self._axis_y = QValueAxis()
        self._axis_y.setRange(-1, 1)
        self._axis_y.setTitleText("Audio level")

        self._chart.setAxisX(self._axis_x, self._series)
        self._chart.setAxisY(self._axis_y, self._series)
        self._chart.legend().hide()
        self._chart.setTitle("Input Waveform")
        self._chart.setBackgroundBrush(QBrush(QColor(COLORS["surface_variant"])))

        self.chart_view = QChartView(self._chart)
        self.chart_view.setMinimumHeight(150)

    def _populate_devices(self):
        """Populate audio device dropdowns."""
        devices = enumerate_audio_devices()

        self.input_combo.clear()
        for idx, name in devices["inputs"]:
            self.input_combo.addItem(f"{idx}: {name}", idx)

        self.output_combo.clear()
        for idx, name in devices["outputs"]:
            self.output_combo.addItem(f"{idx}: {name}", idx)

    def _toggle_conversion(self):
        """Toggle conversion on/off."""
        if not self.running:
            self._start_conversion()
        else:
            self._stop_conversion()

    def _start_conversion(self):
        """Start real-time conversion."""
        self.running = True
        self.start_btn.setText("Running...")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("Converting...")
        self.status_label.setStyleSheet(f"color: {COLORS['warning']};")

        self.engine = get_engine()
        self.engine.load()

    def _stop_conversion(self):
        """Stop conversion."""
        self.running = False
        self.start_btn.setText("Start")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Ready to convert")
        self.status_label.setStyleSheet(f"color: {COLORS['success']};")

    def _on_save_change(self, state):
        """Handle save output checkbox change."""
        self.save_output = state == Qt.Checked
