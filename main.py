
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel
from PySide6.QtCore import Qt

app = QApplication(sys.argv)

window = QMainWindow()
window.setWindowTitle("T.I.M.O.T.H.Y.")
window.resize(1000, 700)
window.setStyleSheet("""
    QMainWindow {
        background-color: #050914;
    }
""")

title = QLabel("T . I . M . O . T . H . Y .")
title.setAlignment(Qt.AlignmentFlag.AlignCenter)
title.setStyleSheet("""
    color: #65E7FF;
    font-size: 32px;
    font-weight: bold;
    letter-spacing: 5px;
""")

window.setCentralWidget(title)
window.show()

sys.exit(app.exec())
