
import sys
import math

from PySide6.QtCore import Qt, QRectF, QTimer
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget
from PySide6.QtGui import (
    QPainter, QColor, QPen, QFont, QRadialGradient
)


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

        # Center the reactor
        center_x = self.width() / 2
        center_y = self.height() / 2

        # Reactor size
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
                radius * 3.6
            )
        )

        # Draw concentric rings
        for index, (ring_radius, width, alpha) in enumerate([
            (1.00, 3, 230),
            (0.88, 1, 170),
            (0.72, 2, 210),
            (0.56, 1, 150),
        ]):
            painter.save()

            # Rotate the third ring
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
                    r * 2
                )
            )

            painter.restore()

        # Draw rotating glowing points
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

        # Pulsating central core
        core_radius = radius * (
            0.34 + 0.03 * math.sin(self.pulse)
        )

        core = QRadialGradient(
            center_x, center_y, core_radius
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
                core_radius * 2
            )
        )

        # Title
        painter.setPen(QColor("#65E7FF"))
        painter.setFont(
            QFont("Consolas", 21, QFont.Weight.Bold)
        )

        title_rect = QRectF(
            0, center_y - radius - 65,
            self.width(), 40
        )

        painter.drawText(
            title_rect,
            Qt.AlignmentFlag.AlignCenter,
            "T.I.M.O.T.H.Y."
        )

        # System status
        painter.setPen(QColor("#8BAFBE"))
        painter.setFont(QFont("Consolas", 10))

        status_rect = QRectF(
            0, center_y + radius + 30,
            self.width(), 30
        )

        painter.drawText(
            status_rect,
            Qt.AlignmentFlag.AlignCenter,
            "SYSTEM ONLINE  |  VOICE MODULE OFFLINE"
        )


class TimothyWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("T.I.M.O.T.H.Y.")
        self.resize(1000, 750)
        self.setMinimumSize(700, 650)

        self.setStyleSheet(
            "QMainWindow { background-color: #050914; }"
        )

        self.reactor = Reactor()
        self.setCentralWidget(self.reactor)


app = QApplication(sys.argv)

window = TimothyWindow()
window.show()

sys.exit(app.exec())
