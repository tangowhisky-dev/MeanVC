"""Realtime page — live microphone-to-speaker voice conversion."""

from __future__ import annotations

import os

from PySide6.QtCore import Qt, QPointF, QTimer, Signal
from PySide6.QtCharts import (
    QChart,
    QChartView,
    QLineSeries,
    QValueAxis,
)
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from meanvc_gui.components.theme import (
    COLORS,
    CardFrame,
    PrimaryButton,
    SecondaryButton,
    SecondaryLabel,
    SectionTitle,
)
from meanvc_gui.core.device import enumerate_audio_devices, get_current_device
from meanvc_gui.core.profile_manager import get_profile_manager
from meanvc_gui.core.vc_runner import VCRunner

_HERE  = os.path.dirname(os.path.abspath(__file__))
_ROOT  = os.path.dirname(os.path.dirname(_HERE))


class RealtimePage(QWidget):
    """Real-time voice conversion page."""

    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        self._runner: VCRunner | None = None
        self._rtf_history: list[float] = []
        self._waveform_points: list[QPointF] = [QPointF(i, 0) for i in range(200)]
        self._build()
        self._subscribe()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        root.addWidget(SectionTitle("Realtime Conversion"))

        # ---- Profile + devices row ----
        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        # Profile picker
        profile_card = CardFrame()
        pc = QVBoxLayout(profile_card)
        pc.setContentsMargins(16, 14, 16, 14)
        pc.setSpacing(6)
        pc.addWidget(QLabel("Target Profile"))
        self._profile_combo = QComboBox()
        pc.addWidget(self._profile_combo)
        top_row.addWidget(profile_card, 1)

        # Devices
        devices_card = CardFrame()
        dc = QVBoxLayout(devices_card)
        dc.setContentsMargins(16, 14, 16, 14)
        dc.setSpacing(6)
        dc.addWidget(QLabel("Audio Devices"))
        in_row = QHBoxLayout()
        in_row.addWidget(SecondaryLabel("Input"))
        self._input_combo = QComboBox()
        in_row.addWidget(self._input_combo, 1)
        dc.addLayout(in_row)
        out_row = QHBoxLayout()
        out_row.addWidget(SecondaryLabel("Output"))
        self._output_combo = QComboBox()
        out_row.addWidget(self._output_combo, 1)
        dc.addLayout(out_row)
        refresh_btn = QPushButton("↺ Refresh")
        refresh_btn.setFixedHeight(28)
        refresh_btn.clicked.connect(self._populate_devices)
        dc.addWidget(refresh_btn)
        top_row.addWidget(devices_card, 2)
        root.addLayout(top_row)

        # ---- Settings card ----
        settings_card = CardFrame()
        sc = QVBoxLayout(settings_card)
        sc.setContentsMargins(16, 14, 16, 14)
        sc.setSpacing(10)

        steps_row = QHBoxLayout()
        steps_row.addWidget(QLabel("Steps (1=fastest, 2=better quality)"))
        self._steps_slider = QSlider(Qt.Horizontal)
        self._steps_slider.setMinimum(1)
        self._steps_slider.setMaximum(2)
        self._steps_slider.setValue(1)
        self._steps_slider.setTickPosition(QSlider.TicksBelow)
        self._steps_label = QLabel("1")
        self._steps_label.setFixedWidth(16)
        self._steps_slider.valueChanged.connect(lambda v: self._steps_label.setText(str(v)))
        steps_row.addWidget(self._steps_slider, 1)
        steps_row.addWidget(self._steps_label)
        sc.addLayout(steps_row)

        save_row = QHBoxLayout()
        self._save_check = QCheckBox("Save output to file")
        save_row.addWidget(self._save_check)
        self._save_path_btn = QPushButton("Choose…")
        self._save_path_btn.setEnabled(False)
        self._save_path_btn.clicked.connect(self._pick_save_path)
        save_row.addWidget(self._save_path_btn)
        self._save_path_label = SecondaryLabel("")
        save_row.addWidget(self._save_path_label, 1)
        self._save_check.toggled.connect(self._save_path_btn.setEnabled)
        sc.addLayout(save_row)
        root.addWidget(settings_card)

        # ---- Control row ----
        ctrl_row = QHBoxLayout()
        self._start_btn = PrimaryButton("▶  Start")
        self._start_btn.setMinimumWidth(120)
        self._start_btn.clicked.connect(self._start)
        ctrl_row.addWidget(self._start_btn)

        self._stop_btn = SecondaryButton("⏹  Stop")
        self._stop_btn.setEnabled(False)
        self._stop_btn.setMinimumWidth(100)
        self._stop_btn.clicked.connect(self._stop)
        ctrl_row.addWidget(self._stop_btn)

        ctrl_row.addStretch()

        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px; background: transparent;")
        ctrl_row.addWidget(self._status_label)

        self._rtf_label = QLabel("")
        self._rtf_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; background: transparent;")
        ctrl_row.addWidget(self._rtf_label)
        root.addLayout(ctrl_row)

        # ---- Waveform chart ----
        series = QLineSeries()
        for p in self._waveform_points:
            series.append(p)
        pen = QPen(QColor(COLORS["primary"]))
        pen.setWidth(1)
        series.setPen(pen)

        chart = QChart()
        chart.addSeries(series)
        chart.setBackgroundBrush(QBrush(QColor(COLORS["surface"])))
        chart.setPlotAreaBackgroundBrush(QBrush(QColor(COLORS["surface"])))
        chart.legend().hide()
        chart.setMargins(__import__("PySide6.QtCore", fromlist=["QMargins"]).QMargins(0, 0, 0, 0))

        ax = QValueAxis()
        ax.setRange(0, 200)
        ax.setVisible(False)
        ay = QValueAxis()
        ay.setRange(-1, 1)
        ay.setVisible(False)
        chart.addAxis(ax, Qt.AlignBottom)
        chart.addAxis(ay, Qt.AlignLeft)
        series.attachAxis(ax)
        series.attachAxis(ay)

        self._waveform_series = series
        self._chart_view = QChartView(chart)
        self._chart_view.setFixedHeight(120)
        self._chart_view.setStyleSheet(f"border-radius: 8px; background: {COLORS['surface']};")
        root.addWidget(self._chart_view)

        root.addStretch()

        self._save_out_path: str | None = None

        # Timer to animate waveform while running (random placeholder when no real data)
        self._wave_timer = QTimer()
        self._wave_timer.setInterval(80)
        self._wave_timer.timeout.connect(self._update_waveform)

    def _subscribe(self) -> None:
        self._populate_profiles()
        self._populate_devices()
        try:
            from meanvc_gui.main import bus
            bus.profile_selected.connect(self._on_profile_selected)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Populate combos
    # ------------------------------------------------------------------

    def _populate_profiles(self) -> None:
        pm = get_profile_manager()
        profiles = pm.list_profiles()
        self._profile_combo.clear()
        for p in profiles:
            self._profile_combo.addItem(p["name"], p["id"])
        if hasattr(self.app, "current_profile") and self.app.current_profile:
            pid = self.app.current_profile["id"]
            for i in range(self._profile_combo.count()):
                if self._profile_combo.itemData(i) == pid:
                    self._profile_combo.setCurrentIndex(i)

    def _populate_devices(self) -> None:
        devices = enumerate_audio_devices()
        self._input_combo.clear()
        for idx, name in devices["inputs"]:
            self._input_combo.addItem(f"{name}", idx)
        self._output_combo.clear()
        for idx, name in devices["outputs"]:
            self._output_combo.addItem(f"{name}", idx)

    def _on_profile_selected(self, profile: dict) -> None:
        pid = profile["id"]
        for i in range(self._profile_combo.count()):
            if self._profile_combo.itemData(i) == pid:
                self._profile_combo.setCurrentIndex(i)
                return
        self._populate_profiles()

    # ------------------------------------------------------------------
    # Save path
    # ------------------------------------------------------------------

    def _pick_save_path(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Recording As", "recording.wav", "WAV files (*.wav)"
        )
        if path:
            self._save_out_path = path
            self._save_path_label.setText(os.path.basename(path))

    # ------------------------------------------------------------------
    # Start / stop
    # ------------------------------------------------------------------

    def _start(self) -> None:
        if self._profile_combo.count() == 0:
            QMessageBox.warning(self, "No Profile", "Create a voice profile in Library first.")
            return

        profile_id = self._profile_combo.currentData()
        input_idx  = self._input_combo.currentData()
        output_idx = self._output_combo.currentData()
        steps      = self._steps_slider.value()
        save_path  = self._save_out_path if self._save_check.isChecked() else None

        self._runner = VCRunner(
            profile_id    = profile_id,
            input_device  = input_idx,
            output_device = output_idx,
            steps         = steps,
            save_path     = save_path,
        )
        self._runner.chunk_rtf.connect(self._on_rtf)
        self._runner.status.connect(self._on_status)
        self._runner.error.connect(self._on_error)
        self._runner.underrun.connect(lambda n: self._status_label.setText(f"Underruns: {n}"))
        self._runner.finished.connect(self._on_runner_finished)
        self._runner.start()

        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._wave_timer.start()
        self._status_label.setText("Starting…")
        self._rtf_history.clear()

    def _stop(self) -> None:
        if self._runner:
            self._runner.stop()
        self._stop_btn.setEnabled(False)
        self._wave_timer.stop()
        self._status_label.setText("Stopping…")

    def _on_runner_finished(self) -> None:
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._wave_timer.stop()
        self._status_label.setText("Stopped.")
        self._rtf_label.setText("")

    # ------------------------------------------------------------------
    # Signals from runner
    # ------------------------------------------------------------------

    def _on_rtf(self, rtf: float) -> None:
        self._rtf_history.append(rtf)
        avg = sum(self._rtf_history[-10:]) / min(len(self._rtf_history), 10)
        color = COLORS["success"] if avg < 0.8 else COLORS["warning"] if avg < 1.0 else COLORS["error"]
        self._rtf_label.setText(f"RTF: {avg:.2f}")
        self._rtf_label.setStyleSheet(f"color: {color}; font-size: 12px; background: transparent;")

    def _on_status(self, msg: str) -> None:
        self._status_label.setText(msg)

    def _on_error(self, msg: str) -> None:
        self._wave_timer.stop()
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._status_label.setText("Error")
        QMessageBox.critical(self, "Realtime Error", msg)

    # ------------------------------------------------------------------
    # Waveform animation
    # ------------------------------------------------------------------

    def _update_waveform(self) -> None:
        """Animate waveform while running (placeholder data)."""
        import math, random
        t = __import__("time").time()
        pts = []
        for i in range(200):
            y = 0.3 * math.sin(t * 8 + i * 0.1) + 0.1 * random.gauss(0, 1)
            pts.append(QPointF(i, max(-1.0, min(1.0, y))))
        self._waveform_series.replace(pts)
