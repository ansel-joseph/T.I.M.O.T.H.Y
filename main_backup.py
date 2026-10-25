
import psutil
import sys
import math

from PySide6.QtCore import Qt, QRectF, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QFrame,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
)
from PySide6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QFont,
    QRadialGradient,
)


# =========================================================
# REACTOR
# =========================================================

class Reactor(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(600, 600)

        self.angle = 0
        self.pulse = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(30)

    def animate(self):
        self.angle = (self.angle + 2) % 360
        self.pulse = (self.pulse + 0.08) % (2 * math.pi)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center_x = self.width() / 2
        center_y = self.height() / 2
        radius = min(self.width(), self.height()) * 0.29

        # Background glow
        glow = QRadialGradient(center_x, center_y, radius * 1.8)
        glow.setColorAt(0, QColor(0, 160, 255, 35))
        glow.setColorAt(1, QColor(0, 0, 0, 0))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glow)

        painter.drawEllipse(
            QRectF(
                center_x - radius * 1.8,
                center_y - radius * 1.8,
                radius * 3.6,
                radius * 3.6,
            )
        )

        # Concentric rings
        for index, (ring_radius, width, alpha) in enumerate([
            (1.00, 3, 230),
            (0.88, 1, 170),
            (0.72, 2, 210),
            (0.56, 1, 150),
        ]):
            painter.save()

            if index == 2:
                painter.translate(center_x, center_y)
                painter.rotate(self.angle)
                painter.translate(-center_x, -center_y)

            pen = QPen(QColor(65, 220, 255, alpha))
            pen.setWidth(width)

            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            r = radius * ring_radius

            painter.drawEllipse(
                QRectF(
                    center_x - r,
                    center_y - r,
                    r * 2,
                    r * 2,
                )
            )

            painter.restore()

        # Rotating energy segments
        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(-self.angle * 0.6)

        segment_pen = QPen(QColor(65, 220, 255, 210))
        segment_pen.setWidth(4)
        segment_pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        painter.setPen(segment_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        segment_radius = radius * 0.78

        for i in range(8):
            start_angle = i * 45 + 5
            span_angle = 25

            painter.drawArc(
                QRectF(
                    -segment_radius,
                    -segment_radius,
                    segment_radius * 2,
                    segment_radius * 2,
                ),
                int(start_angle * 16),
                int(span_angle * 16),
            )

        painter.restore()

        # Radial markings
        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(self.angle)

        for i in range(60):
            painter.save()
            painter.rotate(i * 6)

            if i % 5 == 0:
                tick_length = 12
                tick_color = QColor(101, 231, 255, 220)
                tick_width = 2
            else:
                tick_length = 5
                tick_color = QColor(65, 180, 210, 120)
                tick_width = 1

            tick_pen = QPen(tick_color)
            tick_pen.setWidth(tick_width)
            painter.setPen(tick_pen)

            outer = radius * 0.96
            inner = outer - tick_length

            painter.drawLine(
                0, int(-outer),
                0, int(-inner),
            )

            painter.restore()

        painter.restore()

        # Glowing outer points
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#65E7FF"))

        for i in range(36):
            angle = math.radians(i * 10 + self.angle)
            dot_radius = radius * 1.07

            x = center_x + math.cos(angle) * dot_radius
            y = center_y + math.sin(angle) * dot_radius

            painter.drawEllipse(
                QRectF(x - 2, y - 2, 4, 4)
            )

        # Pulsating core
        core_radius = radius * (
            0.34 + 0.03 * math.sin(self.pulse)
        )

        core = QRadialGradient(
            center_x,
            center_y,
            core_radius,
        )

        core.setColorAt(0, QColor("#D8FAFF"))
        core.setColorAt(0.35, QColor("#42DFFF"))
        core.setColorAt(1, QColor(0, 100, 190, 20))

        painter.setPen(QPen(QColor("#65E7FF"), 2))
        painter.setBrush(core)

        painter.drawEllipse(
            QRectF(
                center_x - core_radius,
                center_y - core_radius,
                core_radius * 2,
                core_radius * 2,
            )
        )

        # Reactor title
        painter.setPen(QColor("#65E7FF"))
        painter.setFont(
            QFont("Consolas", 21, QFont.Weight.Bold)
        )

        painter.drawText(
            QRectF(
                0,
                center_y - radius - 65,
                self.width(),
                40,
            ),
            Qt.AlignmentFlag.AlignCenter,
            "T.I.M.O.T.H.Y.",
        )

        # Reactor status
        painter.setPen(QColor("#8BAFBE"))
        painter.setFont(QFont("Consolas", 10))

        painter.drawText(
            QRectF(
                0,
                center_y + radius + 30,
                self.width(),
                30,
            ),
            Qt.AlignmentFlag.AlignCenter,
            "SYSTEM ONLINE  |  VOICE MODULE OFFLINE",
        )


# =========================================================
# DASHBOARD PANEL HELPER
# =========================================================

def create_panel(title):
    panel = QFrame()
    panel.setObjectName("dashboardPanel")
    panel.setMinimumWidth(205)
    panel.setMaximumWidth(260)

    layout = QVBoxLayout(panel)
    layout.setContentsMargins(16, 18, 16, 18)
    layout.setSpacing(16)

    heading = QLabel(title)
    heading.setObjectName("panelHeading")
    heading.setWordWrap(True)

    layout.addWidget(heading)

    return panel, layout


def create_metric(label_text, value_text):
    container = QWidget()

    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(5)

    label = QLabel(label_text)
    label.setObjectName("metricLabel")

    value = QLabel(value_text)
    value.setObjectName("metricValue")

    layout.addWidget(label)
    layout.addWidget(value)

    return container


# =========================================================
# MAIN WINDOW
# =========================================================

class TimothyWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("T.I.M.O.T.H.Y.")
        self.resize(1400, 800)
        self.setMinimumSize(1100, 700)

        self.setStyleSheet("""
            QMainWindow, QWidget#root {
                background-color: #050914;
            }

            QFrame#dashboardPanel {
                background-color: #0A1423;
                border: 1px solid #18374A;
                border-radius: 12px;
            }

            QLabel#panelHeading {
                color: #65E7FF;
                font-family: Consolas;
                font-size: 15px;
                font-weight: bold;
                padding-bottom: 10px;
                border-bottom: 1px solid #18374A;
            }

            QLabel#metricLabel {
                color: #7899AC;
                font-family: Consolas;
                font-size: 10px;
            }

            QLabel#metricValue {
                color: #BDEFFF;
                font-family: Consolas;
                font-size: 15px;
                font-weight: bold;
            }

            QLabel#infoText {
                color: #91ADBF;
                font-family: Consolas;
                font-size: 11px;
            }

            QLabel#statusBar {
                color: #65E7FF;
                font-family: Consolas;
                font-size: 10px;
                padding: 8px;
            }
        """)

        # Main root widget
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)

        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(18, 16, 18, 10)
        main_layout.setSpacing(8)

        # Three-column dashboard
        dashboard = QHBoxLayout()
        dashboard.setSpacing(16)

        # LEFT PANEL: SYSTEM MONITOR
        left_panel, left_layout = create_panel("SYSTEM MONITOR")

        # CPU metric
        cpu_metric = create_metric("CPU USAGE", "0%")
        left_layout.addWidget(cpu_metric)

        # RAM metric
        ram_metric = create_metric("MEMORY", "Loading...")
        left_layout.addWidget(ram_metric)

        # Keep references to the value labels
        self.cpu_value = cpu_metric.findChild(
            QLabel, "metricValue"
        )
        self.ram_value = ram_metric.findChild(
            QLabel, "metricValue"
        )

        left_layout.addWidget(
            create_metric("GPU", "STANDBY")
        )
        left_layout.addWidget(
            create_metric("AI ENGINE", "QWEN3")
        )

        left_layout.addStretch()

        left_note = QLabel(
            "MONITORING MODULE\nLIVE SYSTEM DATA"
        )
        left_note.setObjectName("infoText")
        left_note.setWordWrap(True)
        left_layout.addWidget(left_note)

        # CENTER: REACTOR
        self.reactor = Reactor()

        # RIGHT PANEL: AI INFORMATION
        right_panel, right_layout = create_panel("INFORMATION")

        response_label = QLabel("RESPONSE STREAM")
        response_label.setObjectName("metricLabel")
        right_layout.addWidget(response_label)

        response_text = QLabel(
            "T.I.M.O.T.H.Y. is online.\n\n"
            "AI response display is ready.\n\n"
            "Awaiting connection to the local AI engine..."
        )
        response_text.setObjectName("infoText")
        response_text.setWordWrap(True)
        response_text.setAlignment(
            Qt.AlignmentFlag.AlignTop
        )
        right_layout.addWidget(response_text)

        right_layout.addStretch()

        connection_label = QLabel(
            "LOCAL MODEL\nQWEN3:4B\n\n"
            "VOICE MODULE\nOFFLINE"
        )
        connection_label.setObjectName("metricValue")
        connection_label.setWordWrap(True)
        right_layout.addWidget(connection_label)

        # Assemble dashboard
        dashboard.addWidget(left_panel)
        dashboard.addWidget(self.reactor, 1)
        dashboard.addWidget(right_panel)

        main_layout.addLayout(dashboard, 1)

        # Initialize CPU monitoring
        psutil.cpu_percent(interval=None)

        # Update system metrics every second
        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(
            self.update_system_metrics
        )
        self.monitor_timer.start(1000)

        # Display initial readings
        self.update_system_metrics()

        # Bottom status bar
        status = QLabel(
            "T.I.M.O.T.H.Y.  |  INTERFACE ONLINE  |  "
            "AI CONNECTION PENDING"
        )
        status.setObjectName("statusBar")
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(status)

    def update_system_metrics(self):
        # CPU usage percentage
        cpu_usage = psutil.cpu_percent(interval=None)
        self.cpu_value.setText(f"{cpu_usage:.0f}%")

        # RAM usage
        memory = psutil.virtual_memory()

        used_gb = memory.used / (1024 ** 3)
        total_gb = memory.total / (1024 ** 3)

        self.ram_value.setText(
            f"{used_gb:.1f} / {total_gb:.1f} GB"
        )


# =========================================================
# START APPLICATION
# =========================================================

app = QApplication(sys.argv)

window = TimothyWindow()
window.show()

sys.exit(app.exec())
