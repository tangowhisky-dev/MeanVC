"""Analysis page — speaker similarity analysis with waveform playback and embedding charts."""

from __future__ import annotations

import math
import os
import time

import numpy as np
import torchaudio

from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QLineSeries,
    QScatterSeries,
    QValueAxis,
)
from PySide6.QtCore import (
    QBuffer,
    QByteArray,
    QIODevice,
    QPointF,
    Qt,
    QThread,
    QTimer,
    QUrl,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from meanvc_gui.components.theme import (
    COLORS,
    CardFrame,
    PrimaryButton,
    SecondaryLabel,
    SectionTitle,
)
from meanvc_gui.core.engine import get_engine

_COLOR_A = "#84DCC6"   # Pearl Aqua — File A
_COLOR_B = "#A78BFA"   # Violet    — File B


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_dur(sec: float) -> str:
    if sec < 60:
        return f"{sec:.1f}s"
    return f"{int(sec//60)}m {int(sec%60)}s"


def _fmt_time(sec: float) -> str:
    m = int(sec // 60)
    s = int(sec % 60)
    return f"{m}:{s:02d}"


def _quality_color(quality: str) -> str:
    return {
        "Good": COLORS["success"],
        "Fair": COLORS["warning"],
        "Low":  COLORS["error"],
    }.get(quality, COLORS["text_muted"])


# ---------------------------------------------------------------------------
# Waveform canvas widget
# ---------------------------------------------------------------------------

class WaveformCanvas(QWidget):
    """Canvas waveform with playhead, cursor seek, and play/stop controls."""

    def __init__(self, color: str = _COLOR_A, parent=None) -> None:
        super().__init__(parent)
        self._color     = QColor(color)
        self._dim_color = QColor(COLORS["border"])
        self._peaks: np.ndarray | None = None
        self._duration  = 0.0
        self._playhead  = 0.0
        self._cursor    = 0.0
        self._loading   = False

        self.setMinimumHeight(80)
        self.setMaximumHeight(80)
        self.setCursor(Qt.CrossCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def load_file(self, path: str) -> None:
        self._loading = True
        self._peaks   = None
        self._playhead = 0.0
        self._cursor   = 0.0
        self.update()

        try:
            wav, sr = torchaudio.load(path)
            if wav.shape[0] > 1:
                wav = wav.mean(dim=0, keepdim=True)
            if sr != 16000:
                wav = torchaudio.transforms.Resample(sr, 16000)(wav)
            self._duration = wav.shape[1] / 16000
            samples = wav.squeeze().numpy()
            BINS = 800
            spb = max(1, len(samples) // BINS)
            peaks = np.array([
                np.abs(samples[i*spb:(i+1)*spb]).max()
                for i in range(BINS)
            ], dtype=np.float32)
            max_p = peaks.max() or 1.0
            self._peaks = peaks / max_p
        except Exception:
            self._peaks = None
            self._duration = 0.0
        finally:
            self._loading = False
            self.update()

    def set_playhead(self, sec: float) -> None:
        self._playhead = sec
        self.update()

    def reset(self) -> None:
        self._peaks    = None
        self._duration = 0.0
        self._playhead = 0.0
        self._cursor   = 0.0
        self.update()

    @property
    def cursor_sec(self) -> float:
        return self._cursor

    @property
    def duration(self) -> float:
        return self._duration

    def mousePressEvent(self, ev) -> None:
        if self._duration > 0:
            self._cursor = max(0.0, min(self._duration,
                (ev.position().x() / self.width()) * self._duration))
            self.update()

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        W, H = self.width(), self.height()
        mid = H // 2

        # background
        p.fillRect(0, 0, W, H, QColor(COLORS["surface_variant"]))

        if self._loading:
            p.setPen(QColor(COLORS["text_muted"]))
            p.drawText(0, 0, W, H, Qt.AlignCenter, "Decoding waveform…")
            return

        if self._peaks is not None:
            n = len(self._peaks)
            for i, amp in enumerate(self._peaks):
                x = int(i / n * W)
                h = max(1, int(amp * mid * 0.88))
                past = (self._duration > 0 and
                        (i / n) * self._duration < self._playhead)
                p.setPen(self._color if past else self._dim_color)
                p.drawLine(x, mid - h, x, mid + h)
        else:
            p.setPen(QColor(COLORS["text_muted"]))
            p.drawText(0, 0, W, H, Qt.AlignCenter, "No file loaded")
            return

        # cursor line (dashed slate)
        if self._duration > 0:
            cx = int(self._cursor / self._duration * W)
            pen = QPen(QColor(148, 163, 184, 130))
            pen.setStyle(Qt.DashLine)
            p.setPen(pen)
            p.drawLine(cx, 0, cx, H)

        # playhead line (amber)
        if self._duration > 0 and self._playhead > 0:
            px = int(self._playhead / self._duration * W)
            p.setPen(QPen(QColor("#FBBF24"), 2))
            p.drawLine(px, 0, px, H)

        # time labels at 0, 25, 50, 75, 100%
        if self._duration > 0:
            font = QFont("Courier", 8)
            p.setFont(font)
            p.setPen(QColor(COLORS["text_muted"]))
            for f in [0.0, 0.25, 0.5, 0.75, 1.0]:
                lbl = _fmt_time(f * self._duration)
                lx = max(0, min(int(f * W), W - 30))
                p.drawText(lx + 2, H - 3, lbl)


# ---------------------------------------------------------------------------
# Audio slot widget — waveform + play button
# ---------------------------------------------------------------------------

class AudioSlot(QWidget):
    """One file slot: file path label, waveform, play/stop button."""

    def __init__(self, label: str, color: str, parent=None) -> None:
        super().__init__(parent)
        self._path     = ""
        self._color    = color
        self._playing  = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Header row
        hdr = QHBoxLayout()
        self._slot_badge = QLabel(label)
        self._slot_badge.setStyleSheet(
            f"color: {color}; font-size: 11px; font-weight: 700; background: transparent; "
            f"font-family: monospace; letter-spacing: 0.05em;"
        )
        hdr.addWidget(self._slot_badge)
        hdr.addStretch()
        self._dur_label = SecondaryLabel("")
        hdr.addWidget(self._dur_label)
        layout.addLayout(hdr)

        # Waveform
        self._canvas = WaveformCanvas(color=color)
        layout.addWidget(self._canvas)

        # Controls row
        ctrl = QHBoxLayout()
        self._play_btn = QPushButton("▶  Play")
        self._play_btn.setFixedHeight(28)
        self._play_btn.setEnabled(False)
        self._play_btn.clicked.connect(self._toggle_play)
        ctrl.addWidget(self._play_btn)

        self._pos_label = SecondaryLabel("0:00 / 0:00")
        ctrl.addWidget(self._pos_label)
        ctrl.addStretch()

        self._file_label = SecondaryLabel("No file selected")
        self._file_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px; background: transparent;"
        )
        ctrl.addWidget(self._file_label, 1)

        browse_btn = QPushButton("Browse…")
        browse_btn.setFixedHeight(28)
        browse_btn.clicked.connect(self._browse)
        ctrl.addWidget(browse_btn)
        layout.addLayout(ctrl)

        # QMediaPlayer
        self._player  = QMediaPlayer()
        self._audio_out = QAudioOutput()
        self._player.setAudioOutput(self._audio_out)
        self._audio_out.setVolume(1.0)
        self._player.playbackStateChanged.connect(self._on_state_change)
        self._player.positionChanged.connect(self._on_position)
        self._player.durationChanged.connect(self._on_duration_changed)

        # Timer for canvas playhead
        self._timer = QTimer()
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick)

    # ------------------------------------------------------------------

    def set_file(self, path: str) -> None:
        if self._playing:
            self._player.stop()
        self._path = path
        self._file_label.setText(os.path.basename(path))
        self._file_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 11px; background: transparent;")
        self._canvas.load_file(path)
        self._player.setSource(QUrl.fromLocalFile(path))
        self._play_btn.setEnabled(True)
        self._playing = False
        self._play_btn.setText("▶  Play")
        self._play_btn.setStyleSheet("")

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Audio File", "",
            "Audio Files (*.wav *.mp3 *.flac *.ogg *.m4a)",
        )
        if path:
            self.set_file(path)

    def _toggle_play(self) -> None:
        if self._playing:
            self._player.pause()
        else:
            # Seek to canvas cursor if not already playing
            if self._canvas.duration > 0:
                seek_ms = int(self._canvas.cursor_sec * 1000)
                self._player.setPosition(seek_ms)
            self._player.play()

    def _on_state_change(self, state) -> None:
        self._playing = (state == QMediaPlayer.PlayingState)
        if self._playing:
            self._play_btn.setText("⏸  Pause")
            self._play_btn.setStyleSheet(
                f"background: rgba(251,191,36,0.15); color: #FBBF24; "
                f"border: 1px solid rgba(251,191,36,0.4);"
            )
            self._timer.start()
        else:
            self._play_btn.setText("▶  Play")
            self._play_btn.setStyleSheet("")
            self._timer.stop()
            if state == QMediaPlayer.StoppedState:
                self._canvas.set_playhead(0.0)

    def _on_position(self, ms: int) -> None:
        sec = ms / 1000
        dur = self._canvas.duration
        self._pos_label.setText(
            f"{_fmt_time(sec)} / {_fmt_time(dur)}" if dur > 0 else "0:00"
        )

    def _on_duration_changed(self, ms: int) -> None:
        dur = ms / 1000
        self._dur_label.setText(_fmt_dur(dur))

    def _tick(self) -> None:
        self._canvas.set_playhead(self._player.position() / 1000)

    @property
    def path(self) -> str:
        return self._path


# ---------------------------------------------------------------------------
# SVG ring gauge
# ---------------------------------------------------------------------------

class SimilarityGauge(QWidget):
    """Circular ring gauge rendered as SVG, matching rvc-web SimilarityGauge."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._svg = QSvgWidget()
        self._svg.setFixedSize(110, 110)
        self._label = QLabel("A ↔ B")
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setStyleSheet(
            f"font-size: 11px; font-family: monospace; color: {COLORS['text_secondary']};"
        )
        self._sub = SecondaryLabel("Run analysis to see score")
        self._sub.setAlignment(Qt.AlignCenter)

        lyt = QVBoxLayout(self)
        lyt.setContentsMargins(0, 0, 0, 0)
        lyt.setSpacing(4)
        lyt.addWidget(self._svg, 0, Qt.AlignHCenter)
        lyt.addWidget(self._label)
        lyt.addWidget(self._sub)

        self._render(0.0)

    def set_value(self, similarity_0_100: float) -> None:
        v = similarity_0_100 / 100.0
        self._render(v)
        tier = (
            "Excellent"  if v >= 0.80 else
            "Very Good"  if v >= 0.70 else
            "Good"       if v >= 0.60 else
            "Moderate"   if v >= 0.50 else
            "Poor"       if v >= 0.40 else
            "Very Poor"
        )
        self._sub.setText(tier)

    def _render(self, v: float) -> None:
        color = (
            "#22c55e" if v >= 0.80 else
            "#4ade80" if v >= 0.70 else
            "#22d3ee" if v >= 0.60 else
            "#fef08a" if v >= 0.50 else
            "#fb923c" if v >= 0.40 else
            "#f87171"
        )
        pct = round(v * 100)
        dash_array = 2 * math.pi * 40
        dash_offset = dash_array * (1 - v)
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96" viewBox="0 0 96 96">
  <circle cx="48" cy="48" r="40" fill="none" stroke="#27272a" stroke-width="8"/>
  <circle cx="48" cy="48" r="40" fill="none" stroke="{color}" stroke-width="8"
    stroke-dasharray="{dash_array:.2f}" stroke-dashoffset="{dash_offset:.2f}"
    stroke-linecap="round" transform="rotate(-90 48 48)"/>
  <text x="48" y="48" text-anchor="middle" fill="{color}"
    font-size="18" font-family="monospace" font-weight="bold" dy="0.15em">{pct}%</text>
</svg>"""
        ba = QByteArray(svg.encode())
        self._svg.load(ba)


# ---------------------------------------------------------------------------
# Embedding charts — three tabs matching rvc-web
# ---------------------------------------------------------------------------

def build_diff_chart(emb_a: list[float], emb_b: list[float]) -> QChartView:
    """Bar chart: A−B per dimension. Fixed Y-axis ±0.5. Single Pearl Aqua colour."""
    n = len(emb_a)
    diffs = [emb_a[i] - emb_b[i] for i in range(n)]

    bar_set = QBarSet("A − B")
    bar_set.setColor(QColor(COLORS["primary"]))
    bar_set.setBorderColor(QColor(0, 0, 0, 0))
    for d in diffs:
        bar_set.append(max(-0.5, min(0.5, d)))

    series = QBarSeries()
    series.append(bar_set)
    series.setBarWidth(1.0)

    chart = _chart_base()
    chart.addSeries(series)
    chart.legend().hide()

    ax = _axis_x("Dimension", 0, n)
    ax.setTickCount(5)
    ax.setLabelFormat("%d")

    ay = _axis_y("Difference (A − B)", -0.5, 0.5)
    ay.setTickCount(11)          # -0.5 to +0.5 in 0.1 steps
    ay.setLabelFormat("%.1f")

    chart.addAxis(ax, Qt.AlignBottom)
    chart.addAxis(ay, Qt.AlignLeft)
    series.attachAxis(ax)
    series.attachAxis(ay)

    view = QChartView(chart)
    view.setMinimumHeight(180)
    view.setMaximumHeight(180)
    view.setStyleSheet("border: none;")
    return view

def _chart_base(title: str = "") -> QChart:
    C = COLORS
    chart = QChart()
    chart.setBackgroundBrush(QBrush(QColor(C["surface"])))
    chart.setPlotAreaBackgroundBrush(QBrush(QColor(C["surface_variant"])))
    chart.setPlotAreaBackgroundVisible(True)
    chart.legend().setLabelColor(QColor(C["text_secondary"]))
    chart.legend().setColor(QColor(C["surface"]))
    if title:
        chart.setTitle(title)
        chart.setTitleBrush(QBrush(QColor(C["text_secondary"])))
    chart.setMargins(__import__("PySide6.QtCore", fromlist=["QMargins"]).QMargins(4, 4, 4, 4))
    return chart


def _axis_x(label: str, mn: float, mx: float) -> QValueAxis:
    ax = QValueAxis()
    ax.setTitleText(label)
    ax.setTitleBrush(QBrush(QColor(COLORS["text_secondary"])))
    ax.setLabelsBrush(QBrush(QColor(COLORS["text_muted"])))
    ax.setGridLineColor(QColor(COLORS["border"]))
    ax.setRange(mn, mx)
    return ax


def _axis_y(label: str, mn: float, mx: float) -> QValueAxis:
    ay = QValueAxis()
    ay.setTitleText(label)
    ay.setTitleBrush(QBrush(QColor(COLORS["text_secondary"])))
    ay.setLabelsBrush(QBrush(QColor(COLORS["text_muted"])))
    ay.setGridLineColor(QColor(COLORS["border"]))
    ay.setRange(mn, mx)
    return ay


def build_scatter_chart(emb_a: list[float], emb_b: list[float]) -> QChartView:
    """Scatter plot: A values on X, B values on Y. On diagonal = identical."""
    all_vals = emb_a + emb_b
    mn = min(all_vals) - 0.05
    mx = max(all_vals) + 0.05

    # Three series by |diff|
    green_s  = QScatterSeries()
    orange_s = QScatterSeries()
    red_s    = QScatterSeries()
    for s, col, name in [
        (green_s,  "#4ADE80", "Similar"),
        (orange_s, "#FB923C", "Moderate"),
        (red_s,    "#F87171", "Divergent"),
    ]:
        s.setColor(QColor(col))
        s.setBorderColor(QColor(0, 0, 0, 0))
        s.setMarkerSize(5)
        s.setName(name)

    for i in range(len(emb_a)):
        d = abs(emb_a[i] - emb_b[i])
        pt = QPointF(emb_a[i], emb_b[i])
        if d < 0.1:
            green_s.append(pt)
        elif d < 0.2:
            orange_s.append(pt)
        else:
            red_s.append(pt)

    chart = _chart_base()
    for s in (green_s, orange_s, red_s):
        chart.addSeries(s)

    ax = _axis_x("File A", mn, mx)
    ay = _axis_y("File B", mn, mx)
    chart.addAxis(ax, Qt.AlignBottom)
    chart.addAxis(ay, Qt.AlignLeft)
    for s in (green_s, orange_s, red_s):
        s.attachAxis(ax)
        s.attachAxis(ay)

    # Perfect-match diagonal
    diag = QLineSeries()
    diag.append(QPointF(mn, mn))
    diag.append(QPointF(mx, mx))
    pen = QPen(QColor(72, 74, 64, 180))
    pen.setStyle(Qt.DashLine)
    pen.setWidth(2)
    diag.setPen(pen)
    diag.setName("")
    chart.addSeries(diag)
    diag.attachAxis(ax)
    diag.attachAxis(ay)

    view = QChartView(chart)
    view.setMinimumHeight(360)
    view.setMaximumHeight(360)
    view.setStyleSheet("border: none;")
    return view


def build_line_chart(emb_a: list[float], emb_b: list[float]) -> QChartView:
    """Overlaid line chart: A and B embedding values across all dimensions."""
    n = len(emb_a)
    series_a = QLineSeries()
    series_b = QLineSeries()
    series_a.setName("File A")
    series_b.setName("File B")

    pen_a = QPen(QColor(_COLOR_A))
    pen_a.setWidth(2)
    series_a.setPen(pen_a)
    pen_b = QPen(QColor(_COLOR_B))
    pen_b.setWidth(2)
    series_b.setPen(pen_b)

    for i in range(n):
        series_a.append(QPointF(i + 1, emb_a[i]))
        series_b.append(QPointF(i + 1, emb_b[i]))

    all_vals = emb_a + emb_b
    mn = min(all_vals) - 0.05
    mx = max(all_vals) + 0.05

    chart = _chart_base()
    chart.addSeries(series_a)
    chart.addSeries(series_b)
    chart.legend().setVisible(True)

    ax = _axis_x("Dimension", 0, n + 1)
    ay = _axis_y("Value", mn, mx)
    chart.addAxis(ax, Qt.AlignBottom)
    chart.addAxis(ay, Qt.AlignLeft)
    series_a.attachAxis(ax)
    series_a.attachAxis(ay)
    series_b.attachAxis(ax)
    series_b.attachAxis(ay)

    view = QChartView(chart)
    view.setMinimumHeight(180)
    view.setMaximumHeight(180)
    view.setStyleSheet("border: none;")
    return view


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------

class SimilarityWorker(QThread):
    finished = Signal(dict)
    error    = Signal(str)

    def __init__(self, file_a: str, file_b: str, parent=None) -> None:
        super().__init__(parent)
        self._file_a = file_a
        self._file_b = file_b

    def run(self) -> None:
        try:
            engine = get_engine()
            result = engine.calculate_similarity(self._file_a, self._file_b)
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


# ---------------------------------------------------------------------------
# Analysis page
# ---------------------------------------------------------------------------

class AnalysisPage(QWidget):
    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        self._worker: SimilarityWorker | None = None
        self._build()
        self._subscribe()

    def _subscribe(self) -> None:
        try:
            from meanvc_gui.main import bus
            bus.analysis_requested.connect(self._receive_file_b)
        except Exception:
            pass

    def _receive_file_b(self, path: str) -> None:
        self._slot_b.set_file(path)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build(self) -> None:
        # Outer layout — just holds the single full-page scroll area
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        root.addWidget(SectionTitle("Speaker Analysis"))

        # ── Audio file slots ──────────────────────────────────────────
        files_card = CardFrame()
        fc = QVBoxLayout(files_card)
        fc.setContentsMargins(16, 14, 16, 14)
        fc.setSpacing(14)

        self._slot_a = AudioSlot("FILE A — Source / Reference", _COLOR_A)
        self._slot_b = AudioSlot("FILE B — Converted / Output", _COLOR_B)
        fc.addWidget(self._slot_a)

        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {COLORS['border']};")
        fc.addWidget(sep)

        fc.addWidget(self._slot_b)
        root.addWidget(files_card)

        # ── Analyse button + status ───────────────────────────────────
        ctrl_row = QHBoxLayout()
        self._analyze_btn = PrimaryButton("Analyze Similarity")
        self._analyze_btn.setMinimumWidth(160)
        self._analyze_btn.setMinimumHeight(38)
        self._analyze_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: {COLORS['background']};
                border: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
                padding: 8px 20px;
            }}
            QPushButton:hover {{ background-color: {COLORS['primary_dark']}; }}
            QPushButton:disabled {{
                background-color: {COLORS['surface_variant']};
                color: {COLORS['text_muted']};
            }}
        """)
        self._analyze_btn.clicked.connect(self._run_analysis)
        ctrl_row.addWidget(self._analyze_btn)
        self._status_lbl = SecondaryLabel("")
        ctrl_row.addWidget(self._status_lbl)
        ctrl_row.addStretch()
        root.addLayout(ctrl_row)

        # ── Results — appended inline below the controls ──────────────
        self._results_layout = QVBoxLayout()
        self._results_layout.setContentsMargins(0, 0, 0, 0)
        self._results_layout.setSpacing(16)
        root.addLayout(self._results_layout)

        root.addStretch()
        scroll.setWidget(page)
        outer.addWidget(scroll)
    # ------------------------------------------------------------------
    # Run analysis
    # ------------------------------------------------------------------

    def _run_analysis(self) -> None:
        if not self._slot_a.path or not self._slot_b.path:
            QMessageBox.warning(self, "Missing Files",
                                "Select both File A and File B first.")
            return

        self._analyze_btn.setEnabled(False)
        self._status_lbl.setText("Extracting ECAPA-TDNN embeddings…")
        self._clear_results()

        self._worker = SimilarityWorker(self._slot_a.path, self._slot_b.path)
        self._worker.finished.connect(self._on_results)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _clear_results(self) -> None:
        while self._results_layout.count():
            item = self._results_layout.takeAt(0)
            if w := item.widget():
                w.deleteLater()

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------

    def _on_results(self, result: dict) -> None:
        self._analyze_btn.setEnabled(True)
        self._status_lbl.setText("")
        self._clear_results()

        score  = result["similarity"]
        emb_a  = result["emb_a"]
        emb_b  = result["emb_b"]
        dur_a  = result["duration_a"]
        dur_b  = result["duration_b"]
        qual_a = result["quality_a"]
        qual_b = result["quality_b"]

        # ── Score card ────────────────────────────────────────────────
        score_card = CardFrame()
        sc = QHBoxLayout(score_card)
        sc.setContentsMargins(20, 16, 20, 16)
        sc.setSpacing(24)

        gauge = SimilarityGauge()
        gauge.set_value(score)
        sc.addWidget(gauge)

        # Detail column
        detail_col = QVBoxLayout()
        detail_col.setSpacing(10)

        v = score / 100.0
        score_color = (
            "#22c55e" if v >= 0.80 else
            "#4ade80" if v >= 0.70 else
            "#22d3ee" if v >= 0.60 else
            "#fef08a" if v >= 0.50 else
            "#fb923c" if v >= 0.40 else
            "#f87171"
        )
        big = QLabel(f"{score:.1f}%")
        big.setStyleSheet(
            f"font-size: 40px; font-weight: 200; color: {score_color}; font-family: monospace; background: transparent;"
        )
        detail_col.addWidget(big)

        for lbl, val, col in [
            ("File A", f"{_fmt_dur(dur_a)}  ·  quality: {qual_a}",
             _quality_color(qual_a)),
            ("File B", f"{_fmt_dur(dur_b)}  ·  quality: {qual_b}",
             _quality_color(qual_b)),
            ("Embedding dims", str(len(emb_a)), COLORS["text_secondary"]),
        ]:
            row = QHBoxLayout()
            k = SecondaryLabel(f"{lbl}:")
            k.setFixedWidth(120)
            row.addWidget(k)
            v = QLabel(val)
            v.setStyleSheet(f"color: {col}; font-size: 12px; font-family: monospace; background: transparent;")
            row.addWidget(v)
            row.addStretch()
            detail_col.addLayout(row)

        detail_col.addStretch()
        sc.addLayout(detail_col, 1)
        self._results_layout.addWidget(score_card)

        # ── Embedding charts ─────────────────────────────────────────
        charts_card = CardFrame()
        cc = QVBoxLayout(charts_card)
        cc.setContentsMargins(16, 14, 16, 14)
        cc.setSpacing(8)

        charts_hdr = QLabel("Embedding Analysis")
        charts_hdr.setStyleSheet(
            f"font-size: 14px; font-weight: 600; color: {COLORS['text']}; background: transparent;"
        )
        cc.addWidget(charts_hdr)
        desc = SecondaryLabel(
            f"ECAPA-TDNN speaker embeddings ({len(emb_a)}-dim). "
            "Overlapping = similar speaker characteristics."
        )
        desc.setWordWrap(True)
        cc.addWidget(desc)

        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabBar::tab {{
                background: {COLORS['surface_variant']};
                color: {COLORS['text_secondary']};
                padding: 6px 16px;
                border: none;
                border-bottom: 2px solid transparent;
                font-size: 12px;
            }}
            QTabBar::tab:selected {{
                color: {COLORS['primary']};
                border-bottom: 2px solid {COLORS['primary']};
                background: {COLORS['surface']};
            }}
            QTabWidget::pane {{
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                background: {COLORS['surface']};
            }}
        """)

        diff_view    = build_diff_chart(emb_a, emb_b)
        scatter_view = build_scatter_chart(emb_a, emb_b)
        line_view    = build_line_chart(emb_a, emb_b)

        # Tab 1 — Difference + Overlay stacked vertically
        tab1 = QWidget()
        t1_layout = QVBoxLayout(tab1)
        t1_layout.setContentsMargins(0, 8, 0, 0)
        t1_layout.setSpacing(8)
        t1_layout.addWidget(diff_view)
        t1_layout.addWidget(line_view)

        tabs.addTab(tab1,        "Difference & Overlay")
        tabs.addTab(scatter_view, "Scatter  A vs B")

        cc.addWidget(tabs)
        self._results_layout.addWidget(charts_card)

    def _on_error(self, msg: str) -> None:
        self._analyze_btn.setEnabled(True)
        self._status_lbl.setText("")
        QMessageBox.critical(self, "Analysis Error", msg)
