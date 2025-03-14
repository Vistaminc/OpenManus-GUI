from PySide6.QtWidgets import (
    QMainWindow, QTextEdit, QLineEdit, QPushButton,
    QProgressBar, QVBoxLayout, QWidget, QHBoxLayout,
    QGraphicsDropShadowEffect, QApplication,QLabel
)
from PySide6.QtCore import Signal, QObject, Slot, Qt, QDateTime
from PySide6.QtGui import QColor
import asyncio
from app.agent.manus import Manus
from app.logger import logger

class LogEmitter(QObject):
    log_received = Signal(str, str)
    update_button = Signal()

class AsyncWorker(QObject):
    finished = Signal(str)
    error = Signal(str)
    status = Signal(str)
    
    def __init__(self, agent, log_emitter):
        super().__init__()
        self.agent = agent
        self.log_emitter = log_emitter
        self.log_handler_id = None
        self._cancelled = False
        self._current_task = None

    async def _async_execute(self, prompt):
        try:
            if not self.log_handler_id:
                self.log_handler_id = logger.add(
                    self._log_callback,
                    level="INFO",
                    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<7} | {message}"
                )
            
            if hasattr(self.agent, 'add_interrupt_check'):
                self.agent.add_interrupt_check(lambda: self._cancelled)
            
            self._current_task = asyncio.current_task()
            result = await self.agent.run(prompt)
            if not self._cancelled:
                self.finished.emit(result)
        except asyncio.CancelledError:
            self.error.emit("操作已取消")
        except Exception as e:
            self.error.emit(str(e))
        finally:
            if self.log_handler_id:
                logger.remove(self.log_handler_id)
                self.log_handler_id = None
            self.log_emitter.log_received.emit("info", "ready>")
            self.log_emitter.update_button.emit()

    def _log_callback(self, message):
        level = message.record["level"].name.lower()
        self.log_emitter.log_received.emit(level, message.record["message"])

    @Slot(str)
    def execute(self, prompt):
        self._cancelled = False
        asyncio.create_task(self._async_execute(prompt))

    def cancel(self):
        self._cancelled = True
        if self._current_task:
            self._current_task.cancel()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.themes = {
            "dark": {
                "background": "#1A1A1A",
                "primary": "#25292E",
                "secondary": "#3A3F45",
                "accent": "#8B5CF6",
                "text": "#D7DADC",
                "error": "#EF4444",
                "success": "#22C55E",
                "warning": "#F59E0B",
                "log_time": "#22C55E"
            },
            "light": {
                "background": "#F8FAFC",
                "primary": "#FFFFFF",
                "secondary": "#F1F5F9",
                "accent": "#6366F1",
                "text": "#1E293B",
                "error": "#DC2626",
                "success": "#00FF00",
                "warning": "#F59E0B",
                "log_time": "#16A34A"
            }
        }

        self.current_theme = "dark"
        self.is_running = False
        self.log_emitter = LogEmitter()
        self.log_emitter.log_received.connect(self.handle_log)
        self.agent = Manus()
        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        self.setWindowTitle("OpenManus AI Suite")
        self.resize(1000, 800)
        self.setMinimumSize(800, 600)

        # Theme toggle button
        self.theme_btn = QPushButton()
        self.theme_btn.setFixedSize(40, 40)
        self.theme_btn.clicked.connect(self.toggle_theme)
        self.theme_btn.setObjectName("ThemeButton")
        self.theme_btn.setCursor(Qt.PointingHandCursor)

        # Main container
        container = QWidget()
        container.setObjectName("MainContainer")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(25)

        # Header layout
        # 左侧项目信息
        self.project_info = QLabel(f"""
            <span style="font-size: 14px; color: {self.themes[self.current_theme]['text']};">
                <b>OpenManus-GUI</b> | 
                <a href="https://github.com/Vistaminc/OpenManus-GUI" style="color: {self.themes[self.current_theme]['accent']};">项目地址</a> | 
                基于 <a href="https://github.com/mannaandpoem/OpenManus" style="color: {self.themes[self.current_theme]['accent']};">OpenManus</a>
            </span>
        """)
        self.project_info.setOpenExternalLinks(True)
        
        header = QHBoxLayout()
        header.addWidget(self.project_info)
        header.addStretch()  # 将主题按钮推到右侧
        header.addWidget(self.theme_btn)

        # Output area
        self.output_area = QTextEdit()
        self.output_area.setObjectName("OutputArea")
        self.output_area.setReadOnly(True)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()

        # Input container
        input_container = QWidget()
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(15)

        # Input field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("输入指令...")

        # Send button
        self.send_btn = QPushButton("▶️ 发送")
        self.send_btn.setObjectName("SendButton")
        self.send_btn.setCursor(Qt.PointingHandCursor)

        # Assemble layout
        input_layout.addWidget(self.input_field, 5)
        input_layout.addWidget(self.send_btn, 1)
        
        layout.addLayout(header)
        layout.addWidget(self.output_area)
        layout.addWidget(self.progress_bar)
        layout.addWidget(input_container)

        # Set central widget FIRST
        self.setCentralWidget(container)
        # Then apply styling
        self.apply_theme()
        self._add_shadow_effects()
        self.setCentralWidget(container)

    def _add_shadow_effects(self):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(5, 5)
        self.output_area.setGraphicsEffect(shadow)

        btn_shadow = QGraphicsDropShadowEffect()
        btn_shadow.setBlurRadius(15)
        btn_shadow.setColor(QColor(0, 0, 0, 30))
        btn_shadow.setOffset(3, 3)
        self.send_btn.setGraphicsEffect(btn_shadow)

    def apply_theme(self):
        theme = self.themes[self.current_theme]
        self.output_area.document().setDefaultStyleSheet(f"""
            .log-time {{
                color: {theme['log_time']};  /* 使用动态时间颜色 */
                font-size: 13px;
            }}
        """)
        
        # Container style
        self.centralWidget().setStyleSheet(f"""
            QWidget#MainContainer {{
                background: {theme['background']};
            }}
            QPushButton#ThemeButton {{
                background: {theme['accent']};
                border-radius: 20px;
                color: white;
                font-size: 20px;
            }}
        """)
        
        # Update theme button icon
        self.theme_btn.setText("🌞" if self.current_theme == "dark" else "🌙")
        
        # Apply component styles
        self._apply_output_style()
        self._apply_input_style()
        self._apply_button_style()
        self._apply_progress_style()

    def _apply_output_style(self):
        theme = self.themes[self.current_theme]
        self.output_area.setStyleSheet(f"""
            QTextEdit {{
                background: {theme['primary']};
                color: {theme['text']};  /* 移除了重复的color定义 */
                text-shadow: { "0 1px 1px rgba(0,0,0,0.1)" if self.current_theme == "light" else "0 1px 1px rgba(255,255,255,0.1)" };
                border-radius: 16px;
                padding: 28px;
                font-size: 15px;
                border: 1px solid {theme['secondary']};
                line-height: 1.8;
                font-family: 'Segoe UI', system-ui;
                selection-background-color: {theme['accent']};
            }}
            QScrollBar:vertical {{
                width: 10px;
                background: {theme['secondary']};
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {theme['accent']};
                min-height: 30px;
                border-radius: 4px;
            }}
        """)

    def _apply_input_style(self):
        theme = self.themes[self.current_theme]
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                background: {theme['primary']};
                border: 2px solid {theme['secondary']};
                border-radius: 12px;
                padding: 18px 24px;
                color: {theme['text']};
                font-size: 15px;
                font-weight: 500;
            }}
            QLineEdit:focus {{
                border-color: {theme['accent']};
            }}
            QLineEdit::placeholder {{
                color: {theme['text']}80;
            }}
        """)

    def _apply_button_style(self):
        theme = self.themes[self.current_theme]
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background: {theme['success']};
                color: white;
                border-radius: 10px;
                padding: 14px 28px;
                font-size: 15px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {theme['success']}DD;
            }}
            QPushButton:pressed {{
                background: {theme['success']}BB;
            }}
            QPushButton#StopButton {{
                background: {theme['error']} !important;
            }}
        """)

    def _apply_progress_style(self):
        theme = self.themes[self.current_theme]
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                height: 8px;
                background: {theme['secondary']};
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(
                    x1:0, y1:0.5, x2:1, y2:0.5,
                    stop:0 {theme['accent']}, stop:1 {theme['success']}
                );
                border-radius: 4px;
            }}
        """)

    def toggle_theme(self):
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self.apply_theme()

    def setup_connections(self):
        self.worker = AsyncWorker(self.agent, self.log_emitter)
        self.send_btn.clicked.connect(self.toggle_operation)
        self.input_field.returnPressed.connect(self.toggle_operation)
        self.worker.finished.connect(self.handle_response)
        self.worker.error.connect(self.handle_error)
        self.log_emitter.update_button.connect(self.reset_ui_state)

    def toggle_operation(self):
        if not self.is_running:
            self.start_operation()
        else:
            self.cancel_operation()

    def start_operation(self):
        prompt = self.input_field.text().strip()
        if not prompt:
            return
        
        self.is_running = True
        self.append_message("👤 User Input", prompt, self.themes[self.current_theme]['accent'])
        self.input_field.clear()
        
        self.send_btn.setText("⏹️ 停止")
        self.send_btn.setObjectName("StopButton")
        self.send_btn.style().polish(self.send_btn)
        
        self.progress_bar.show()
        self.worker.execute(prompt)

    # 在MainWindow类中修改取消操作逻辑
    def cancel_operation(self):
        self.worker.cancel()
        self.reset_ui_state()  # 立即重置UI状态
        self.progress_bar.hide()
    
    # 修改发送按钮点击处理逻辑
    def toggle_operation(self):
        if self.send_btn.text() == "▶️ 发送":
            self.start_operation()
        else:
            self.cancel_operation()
    
    # 在AsyncWorker中增强取消机制
    class AsyncWorker(QObject):
        def __init__(self, agent, log_emitter):
            super().__init__()
            self._cancelled = False
            self._current_task = None  # 新增任务引用
    
        async def _async_execute(self, prompt):
            try:
                while not self._cancelled:
                    # 实际任务执行逻辑
                    result = await self.agent.run(prompt)
                    if self._cancelled:
                        break
                self.finished.emit(result)
            except asyncio.CancelledError:
                self.error.emit("操作已取消")
                self._current_task = None

    def reset_ui_state(self):
        self.is_running = False
        self.send_btn.setText("▶️ 发送")
        self.send_btn.setObjectName("SendButton")
        self.send_btn.setEnabled(True)
        self.send_btn.style().polish(self.send_btn)
        self.progress_bar.hide()

    def handle_response(self, result):
        self.append_message("🤖 Response", result, self.themes[self.current_theme]['success'])
        self.log_emitter.update_button.emit()

    def handle_error(self, error_msg):
        self.append_message("❌ Error", error_msg, self.themes[self.current_theme]['error'])
        self.log_emitter.update_button.emit()

    @Slot(str, str)
    def handle_log(self, level, message):
        colors = {
            "info": self.themes[self.current_theme]['accent'],
            "warning": self.themes[self.current_theme]['warning'],
            "error": self.themes[self.current_theme]['error'],
            "debug": "#63B3ED"
        }
        self.append_message(f"📝 {level.upper()}", message, colors.get(level, "#D7DADC"))

    def append_message(self, header: str, content: str, color: str):
        formatted_message = f"""
        <div style="margin-bottom: 25px;">
            <div style="color: {color}; font-weight: 500; margin-bottom: 8px;">{header}</div>
            <div class="log-content">{content}</div>  <!-- 使用CSS类 -->
            <div class="log-time">
                {QDateTime.currentDateTime().toString("hh:mm:ss AP")}
            </div>
        </div>
        """
        self.output_area.append(formatted_message)
        self.output_area.ensureCursorVisible()

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()