"""Analysis page for speaker similarity."""

import os

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QGroupBox,
    QTableWidget,
    QTableWidgetItem,
    QLineEdit,
)
from PySide6.QtCore import Qt
from PySide6.QtCharts import (
    QChart,
    QChartView,
    QBarSet,
    QBarSeries,
    QBarCategoryAxis,
    QValueAxis,
)

from meanvc_gui.components.theme import COLORS, get_button_style
from meanvc_gui.core.engine import get_engine


class AnalysisPage(QWidget):
    """Speaker similarity analysis page."""

    def __init__(self, app):
        """Initialize analysis page.

        Args:
            app: Main window reference
        """
        super().__init__()
        self.app = app
        self.file_a = ""
        self.file_b = ""
        self.results = None
        self._setup_ui()

    def _setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Speaker Analysis")
        title.setStyleSheet(
            f"font-size: 24px; color: {COLORS['text']}; font-weight: 300;"
        )
        layout.addWidget(title)
        layout.addSpacing(20)

        # File selection
        file_group = QGroupBox("Audio Files")
        file_layout = QVBoxLayout()

        # File A
        file_a_layout = QHBoxLayout()
        file_a_layout.addWidget(QLabel("File A:"))
        self.file_a_edit = QLineEdit()
        self.file_a_edit.setPlaceholderText("Select first audio file...")
        file_a_layout.addWidget(self.file_a_edit, 1)
        browse_a_btn = QPushButton("Browse")
        browse_a_btn.clicked.connect(self._pick_file_a)
        file_a_layout.addWidget(browse_a_btn)
        file_layout.addLayout(file_a_layout)

        # File B
        file_b_layout = QHBoxLayout()
        file_b_layout.addWidget(QLabel("File B:"))
        self.file_b_edit = QLineEdit()
        self.file_b_edit.setPlaceholderText("Select second audio file...")
        file_b_layout.addWidget(self.file_b_edit, 1)
        browse_b_btn = QPushButton("Browse")
        browse_b_btn.clicked.connect(self._pick_file_b)
        file_b_layout.addWidget(browse_b_btn)
        file_layout.addLayout(file_b_layout)

        # Analyze button
        analyze_btn = QPushButton("Analyze Similarity")
        analyze_btn.setStyleSheet(get_button_style())
        analyze_btn.clicked.connect(self._analyze)
        file_layout.addWidget(analyze_btn)

        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        layout.addSpacing(15)

        # Results chart
        chart_group = QGroupBox("Similarity")
        chart_layout = QVBoxLayout()

        self.chart_view = QChartView()
        self.chart_view.setMinimumHeight(200)
        chart_layout.addWidget(self.chart_view)

        self.similarity_label = QLabel("")
        self.similarity_label.setStyleSheet(f"font-size: 20px; font-weight: bold;")
        self.similarity_label.setAlignment(Qt.AlignCenter)
        chart_layout.addWidget(self.similarity_label)

        chart_group.setLayout(chart_layout)
        layout.addWidget(chart_group)

        layout.addSpacing(15)

        # Details table
        details_group = QGroupBox("Details")
        details_layout = QVBoxLayout()

        self.details_table = QTableWidget()
        self.details_table.setColumnCount(2)
        self.details_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.details_table.setRowCount(4)
        details_layout.addWidget(self.details_table)

        details_group.setLayout(details_layout)
        layout.addWidget(details_group)

        layout.addStretch()

    def _pick_file_a(self):
        """Pick file A."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Audio File", "", "Audio Files (*.wav *.mp3 *.flac *.ogg)"
        )
        if path:
            self.file_a = path
            self.file_a_edit.setText(os.path.basename(path))

    def _pick_file_b(self):
        """Pick file B."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Audio File", "", "Audio Files (*.wav *.mp3 *.flac *.ogg)"
        )
        if path:
            self.file_b = path
            self.file_b_edit.setText(os.path.basename(path))

    def _analyze(self):
        """Run speaker similarity analysis."""
        if not self.file_a or not self.file_b:
            self.similarity_label.setText("Please select both audio files")
            self.similarity_label.setStyleSheet(f"color: {COLORS['error']};")
            return

        try:
            engine = get_engine()
            self.results = engine.calculate_similarity(self.file_a, self.file_b)
            self._update_results()
        except Exception as e:
            self.similarity_label.setText(f"Error: {e}")
            self.similarity_label.setStyleSheet(f"color: {COLORS['error']};")

    def _update_results(self):
        """Update results display."""
        if not self.results:
            return

        similarity = self.results.get("similarity", 0)

        # Update chart
        bar_set = QBarSet("Similarity")
        bar_set.append(similarity)

        series = QBarSeries()
        series.append(bar_set)

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Speaker Similarity")

        axis_y = QValueAxis()
        axis_y.setRange(0, 100)
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        self.chart_view.setChart(chart)

        # Update label
        color = (
            COLORS["success"]
            if similarity > 70
            else COLORS["warning"]
            if similarity > 40
            else COLORS["error"]
        )
        self.similarity_label.setText(f"{similarity:.1f}% Similar")
        self.similarity_label.setStyleSheet(
            f"font-size: 20px; font-weight: bold; color: {color};"
        )

        # Update table
        self.details_table.setItem(0, 0, QTableWidgetItem("File A Quality"))
        self.details_table.setItem(
            0, 1, QTableWidgetItem(self.results.get("quality_a", "N/A"))
        )
        self.details_table.setItem(1, 0, QTableWidgetItem("File B Quality"))
        self.details_table.setItem(
            1, 1, QTableWidgetItem(self.results.get("quality_b", "N/A"))
        )
        self.details_table.setItem(2, 0, QTableWidgetItem("Duration A"))
        self.details_table.setItem(
            2, 1, QTableWidgetItem(f"{self.results.get('duration_a', 0):.1f}s")
        )
        self.details_table.setItem(3, 0, QTableWidgetItem("Duration B"))
        self.details_table.setItem(
            3, 1, QTableWidgetItem(f"{self.results.get('duration_b', 0):.1f}s")
        )
