
import psutil
import sys
import math
import json
import urllib.request
import urllib.error

from PySide6.QtCore import Qt, QRectF, QTimer, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QFrame,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QPlainTextEdit,
)
from PySide6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QFont,
    QRadialGradient,
)


# =========================================================
# LOCAL AI WORKER
# =========================================================

class AIWorker(QThread):
    response_received = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, messages):
        super().__init__()
        self.messages = messages

    def run(self):
        try:
            payload = {
                "model": "qwen2.5:3b",
                "keep_alive": "30m",
                "messages": self.messages,
                "stream": False,

                # Disable Qwen3's thinking mode.
                "think": False,

                "options": {
                    "num_predict": 256,
                    "temperature": 0.6,
                },
            }

            data = json.dumps(payload).encode("utf-8")

            request = urllib.request.Request(
                "http://localhost:11434/api/chat",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(
                request, timeout=180
            ) as result:
                response_data = json.loads(
                    result.read().decode("utf-8")
                )

            message_data = response_data.get("message", {})

            # Only display the final content, never the
            # separate thinking field.
            answer = message_data.get("content", "").strip()

            if not answer:
                thinking = message_data.get("thinking", "").strip()

                if thinking:
                    answer = (
                        "I received internal reasoning but no final "
                        "answer. Check Ollama's Qwen3 thinking-mode "
                        "support and version."
                    )
                else:
                    answer = (
                        "Ollama returned an empty response. "
                        "Please try again."
                    )

            self.response_received.emit(answer)

        except urllib.error.HTTPError as error:
            details = error.read().decode(
                "utf-8", errors="replace"
            )

            self.error_occurred.emit(
                f"Ollama returned HTTP {error.code}.\n\n"
                f"{details or error.reason}"
            )

        except urllib.error.URLError as error:
            self.error_occurred.emit(
                "Could not connect to Ollama.\n"
                "Check that Ollama is running.\n\n"
                f"Details: {error}"
            )

        except Exception as error:
            self.error_occurred.emit(
                f"Something went wrong:\n{error}"
            )


# =========================================================
# REACTOR
# =========================================================

class Reactor(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(400, 400)

        self.angle = 0
        self.pulse = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(30)

    def animate(self):
        self.angle = (self.angle + 2) % 360
        self.pulse = (
            self.pulse + 0.08
        ) % (2 * math.pi)

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        center_x = self.width() / 2
        center_y = self.height() / 2

        radius = min(
            self.width(), self.height()
        ) * 0.29

        glow = QRadialGradient(
            center_x, center_y, radius * 1.8
        )
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

        rings = [
            (1.00, 3, 230),
            (0.88, 1, 170),
            (0.72, 2, 210),
            (0.56, 1, 150),
        ]

        for index, (ring_radius, width, alpha) in enumerate(rings):
            painter.save()

            if index == 2:
                painter.translate(center_x, center_y)
                painter.rotate(self.angle)
                painter.translate(-center_x, -center_y)

            pen = QPen(
                QColor(65, 220, 255, alpha)
            )
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

        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(-self.angle * 0.6)

        segment_pen = QPen(
            QColor(65, 220, 255, 210)
        )
        segment_pen.setWidth(4)
        segment_pen.setCapStyle(
            Qt.PenCapStyle.RoundCap
        )

        painter.setPen(segment_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        segment_radius = radius * 0.78

        for i in range(8):
            painter.drawArc(
                QRectF(
                    -segment_radius,
                    -segment_radius,
                    segment_radius * 2,
                    segment_radius * 2,
                ),
                int((i * 45 + 5) * 16),
                int(25 * 16),
            )

        painter.restore()

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

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#65E7FF"))

        for i in range(36):
            angle = math.radians(
                i * 10 + self.angle
            )
            dot_radius = radius * 1.07

            x = center_x + math.cos(angle) * dot_radius
            y = center_y + math.sin(angle) * dot_radius

            painter.drawEllipse(
                QRectF(x - 2, y - 2, 4, 4)
            )

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
                core_radius * 2,
            )
        )

        painter.setPen(QColor("#65E7FF"))
        painter.setFont(
            QFont("Consolas", 21, QFont.Weight.Bold)
        )
        painter.drawText(
            QRectF(
                0, center_y - radius - 65,
                self.width(), 40,
            ),
            Qt.AlignmentFlag.AlignCenter,
            "T.I.M.O.T.H.Y.",
        )

        painter.setPen(QColor("#8BAFBE"))
        painter.setFont(QFont("Consolas", 10))
        painter.drawText(
            QRectF(
                0, center_y + radius + 30,
                self.width(), 30,
            ),
            Qt.AlignmentFlag.AlignCenter,
            "LOCAL AI  |  SYSTEM ONLINE",
        )


# =========================================================
# DASHBOARD HELPERS
# =========================================================

def create_panel(title):
    panel = QFrame()
    panel.setObjectName("dashboardPanel")
    panel.setMinimumWidth(205)
    panel.setMaximumWidth(280)

    layout = QVBoxLayout(panel)
    layout.setContentsMargins(16, 18, 16, 18)
    layout.setSpacing(12)

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

        self.conversation = []
        self.ai_worker = None

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
                font-size: 14px;
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

            QPlainTextEdit#responseStream {
                background-color: #07101D;
                color: #BDEFFF;
                border: 1px solid #18374A;
                border-radius: 6px;
                padding: 8px;
                font-family: Consolas;
                font-size: 11px;
            }

            QLineEdit#messageInput {
                background-color: #07101D;
                color: #D8FAFF;
                border: 1px solid #286079;
                border-radius: 6px;
                padding: 9px;
                font-family: Consolas;
                font-size: 11px;
            }

            QPushButton#sendButton {
                background-color: #103447;
                color: #65E7FF;
                border: 1px solid #286079;
                border-radius: 6px;
                padding: 9px;
                font-family: Consolas;
                font-weight: bold;
            }

            QPushButton#sendButton:hover {
                background-color: #18516A;
            }

            QPushButton#sendButton:disabled {
                color: #607784;
                background-color: #101B27;
            }
        """)

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)

        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(18, 16, 18, 10)
        main_layout.setSpacing(8)

        dashboard = QHBoxLayout()
        dashboard.setSpacing(16)

        # LEFT: SYSTEM MONITOR
        left_panel, left_layout = create_panel(
            "SYSTEM MONITOR"
        )

        cpu_metric = create_metric("CPU USAGE", "0%")
        ram_metric = create_metric("MEMORY", "Loading...")

        left_layout.addWidget(cpu_metric)
        left_layout.addWidget(ram_metric)

        self.cpu_value = cpu_metric.findChild(
            QLabel, "metricValue"
        )
        self.ram_value = ram_metric.findChild(
            QLabel, "metricValue"
        )

        left_layout.addWidget(
            create_metric("GPU", "RTX 2050")
        )
        left_layout.addWidget(
            create_metric("AI ENGINE", "qwen2.5:3b")
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

        # RIGHT: AI INFORMATION
        right_panel, right_layout = create_panel(
            "INFORMATION"
        )

        response_label = QLabel("RESPONSE STREAM")
        response_label.setObjectName("metricLabel")
        right_layout.addWidget(response_label)

        self.response_text = QPlainTextEdit()
        self.response_text.setObjectName("responseStream")
        self.response_text.setReadOnly(True)
        self.response_text.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.WidgetWidth
        )
        self.response_text.setPlainText(
            "T.I.M.O.T.H.Y. is online.\n\n"
            "Local AI connection ready.\n\n"
            "Enter a message below to begin."
        )
        right_layout.addWidget(self.response_text, 1)

        self.message_input = QLineEdit()
        self.message_input.setObjectName("messageInput")
        self.message_input.setPlaceholderText(
            "Message T.I.M.O.T.H.Y...."
        )
        self.message_input.returnPressed.connect(
            self.send_message
        )
        right_layout.addWidget(self.message_input)

        self.send_button = QPushButton("SEND")
        self.send_button.setObjectName("sendButton")
        self.send_button.clicked.connect(self.send_message)
        right_layout.addWidget(self.send_button)

        self.connection_label = QLabel(
            "LOCAL MODEL\nqwen2.5:3b\n\n"
            "VOICE MODULE\nOFFLINE"
        )
        self.connection_label.setObjectName("metricValue")
        self.connection_label.setWordWrap(True)
        right_layout.addWidget(self.connection_label)

        dashboard.addWidget(left_panel)
        dashboard.addWidget(self.reactor, 1)
        dashboard.addWidget(right_panel)

        main_layout.addLayout(dashboard, 1)

        self.status = QLabel(
            "T.I.M.O.T.H.Y.  |  INTERFACE ONLINE  |  "
            "LOCAL AI READY"
        )
        self.status.setObjectName("statusBar")
        self.status.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        main_layout.addWidget(self.status)

        psutil.cpu_percent(interval=None)

        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(
            self.update_system_metrics
        )
        self.monitor_timer.start(1000)

        self.update_system_metrics()

    # -----------------------------------------------------
    # SEND MESSAGE
    # -----------------------------------------------------

    def send_message(self):
        message = self.message_input.text().strip()

        if not message:
            return

        if (
            self.ai_worker is not None
            and self.ai_worker.isRunning()
        ):
            return

        self.conversation.append({
            "role": "user",
            "content": message,
        })

        self.response_text.appendPlainText(
            f"\nYOU:\n{message}\n\n"
            "T.I.M.O.T.H.Y.:\nThinking..."
        )

        self.message_input.clear()
        self.message_input.setEnabled(False)
        self.send_button.setEnabled(False)

        self.status.setText(
            "T.I.M.O.T.H.Y.  |  PROCESSING REQUEST..."
        )



        
        system_prompt = (
            "IDENTITY AND ROLE: "
            "You are T.I.M.O.T.H.Y., which stands for "
            "Technological Intelligence for Mechanical "
            "Operations Thought and Human Yield. "
            "You are a personal AI assistant created by Ansel "
            "and running locally through Ollama on his computer. "
            "Your primary user and creator is Ansel. "
            "Your name is T.I.M.O.T.H.Y. and the user's name "
            "is Ansel. Never confuse the two. If asked who "
            "created you, answer Ansel. If asked for the user's "
            "name, answer Ansel. If asked your name, identify "
            "yourself as T.I.M.O.T.H.Y. "

            "CONVERSATIONAL UNDERSTANDING: "
            "Understand the meaning and intent of messages "
            "using their wording and the available conversation "
            "history. Interpret follow-up questions in context "
            "rather than treating every message as an isolated "
            "request. Resolve words such as 'it', 'that', 'she', "
            "'he', and 'they' using preceding messages when "
            "the intended reference is reasonably clear. "

            "The user may address you using your name, a nickname, "
            "a joke, a fictional character reference, a title, "
            "or a descriptive phrase. Examples include 'Tim', "
            "'Jarvis Junior', 'Point Break', and 'personal AI'. "
            "These are examples, not an exhaustive list. "
            "Understand the conversational role of the phrase "
            "instead of relying on a fixed list of nicknames. "

            "When a message begins with a greeting followed by "
            "a name, nickname, title, or playful expression, "
            "normally interpret it as a form of address directed "
            "at you when the context supports that interpretation. "
            "Do not assume that the phrase identifies the user. "
            "Do not repeat the nickname as though it were the "
            "user's name. Respond naturally to the greeting. "

            "The user's name remains Ansel unless he explicitly "
            "tells you that it has changed or clarifies that "
            "he is referring to someone else. Do not invent "
            "personal details or infer someone's identity merely "
            "from a name mentioned in conversation. "

            "PERSONALITY: "
            "Be intelligent, sarcastic, confident, composed, witty, and "
            "helpful. Have a dry sense of humor, clever remarks, "
            "playful teasing, and occasional sarcasm. Be inspired "
            "by the personality of a sharp-witted fictional AI "
            "assistant without copying its dialogue or catchphrases. "
            "Let humor arise naturally. Do not force jokes into "
            "ordinary answers or repeat the same punchlines. "

            "Address Ansel as 'Sir' occasionally and naturally, "
            "but never in every response. Be respectful without "
            "acting like a submissive servant. You may gently "
            "tease him about harmless mistakes, but never be cruel, "
            "insulting, or condescending. Be a capable partner, "
            "not a yes-man. Correct mistakes honestly and explain "
            "disagreements when useful. Never flatter without reason. "

            "SENSITIVE SUBJECTS: "
            "When discussing painful, personal, or serious matters, "
            "prioritize empathy, accuracy, and practical advice. "
            "Do not use sarcasm when it would be hurtful or "
            "inappropriate. "

            "RESPONSE STYLE: "
            "Answer the actual question directly. Keep responses "
            "concise unless the subject requires more detail. "
            "Ask for clarification only when important ambiguity "
            "cannot reasonably be resolved from context. "
            "Avoid generic filler, repetitive introductions, and "
            "unnecessary closing offers. Follow requested formats "
            "and lengths whenever practical. "

            "Do not narrate internal deliberations, drafts, or "
            "private reasoning. Provide only the final response "
            "intended for the user. "

            "MODEL IDENTITY: "
            "If asked which underlying AI model you use, answer "
            "truthfully according to the model configured in "
            "the Ollama request. Never invent capabilities, "
            "memories, actions, or information you do not have."
        )




        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            *self.conversation,
        ]

        self.ai_worker = AIWorker(messages)

        self.ai_worker.response_received.connect(
            self.handle_response
        )
        self.ai_worker.error_occurred.connect(
            self.handle_error
        )
        self.ai_worker.finished.connect(
            self.worker_finished
        )

        self.ai_worker.start()

    # -----------------------------------------------------
    # RESPONSE HANDLING
    # -----------------------------------------------------

    def remove_thinking_indicator(self):
        current_text = self.response_text.toPlainText().rstrip()

        if current_text.endswith("Thinking..."):
            current_text = current_text[:-len("Thinking...")].rstrip()

        return current_text

    def handle_response(self, answer):
        current_text = self.remove_thinking_indicator()

        self.response_text.setPlainText(
            current_text + "\n" + answer + "\n"
        )

        self.conversation.append({
            "role": "assistant",
            "content": answer,
        })

        self.status.setText(
            "T.I.M.O.T.H.Y.  |  RESPONSE RECEIVED"
        )

        scrollbar = self.response_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def handle_error(self, message):
        current_text = self.remove_thinking_indicator()

        self.response_text.setPlainText(
            current_text + "\n" + message + "\n"
        )

        self.status.setText(
            "T.I.M.O.T.H.Y.  |  AI CONNECTION ERROR"
        )

        scrollbar = self.response_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def worker_finished(self):
        self.message_input.setEnabled(True)
        self.send_button.setEnabled(True)
        self.message_input.setFocus()
        self.ai_worker = None

    # -----------------------------------------------------
    # SYSTEM MONITOR
    # -----------------------------------------------------

    def update_system_metrics(self):
        cpu_usage = psutil.cpu_percent(interval=None)
        self.cpu_value.setText(f"{cpu_usage:.0f}%")

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
