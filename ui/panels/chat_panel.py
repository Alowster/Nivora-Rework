import mimetypes
import os

import markdown as md
from PySide6.QtCore import Qt, QTimer, Signal, QSize
from translations import t
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QVBoxLayout,
    QScrollArea, QLabel, QPushButton, QTextEdit, QFileDialog,
)

from assets.icons import get_send_icon, get_camera_icon, get_stop_icon, get_attach_icon
from data.database import (
    create_conversation, add_message, get_messages,
    rename_conversation, get_conversation_name,
)
from services.gemini_thread import GeminiThread
from ui.widgets.icon_button import create_icon_button


class ChatPanel(QWidget):
    region_ready = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.conversation_id = None
        self.pending = []
        self._pending_render = False
        self._render_timer = QTimer()
        self._render_timer.setInterval(50)
        self._render_timer.timeout.connect(self._flush_render)
        self.region_ready.connect(self._on_region_captured)
        self.init_ui()
        self._actualizar_nombre()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)

        self.lbl_conv_name = QLabel()
        self.lbl_conv_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_conv_name.setStyleSheet("color: rgba(255,255,255,100); font-size: 11px;")
        main_layout.addWidget(self.lbl_conv_name)

        self.new_chat_btn = QPushButton(t("new_conversation"))
        self.new_chat_btn.setFixedHeight(28)
        self.new_chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_chat_btn.clicked.connect(self.nueva_conversacion)
        self.new_chat_btn.setStyleSheet("border-radius: 12px")
        main_layout.addWidget(self.new_chat_btn)

        self.messages_widget = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.setAlignment(Qt.AlignTop)
        self.messages_layout.setSpacing(8)
        self.messages_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.messages_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.scroll_area.viewport().setStyleSheet("QWidget { background: transparent; }")
        main_layout.addWidget(self.scroll_area)

        self._auto_scroll = True
        self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll_changed)

        # Fila de chips para adjuntos pendientes
        self.chips_widget = QWidget()
        self.chips_layout = QHBoxLayout(self.chips_widget)
        self.chips_layout.setContentsMargins(0, 4, 0, 0)
        self.chips_layout.setSpacing(4)
        self.chips_layout.addStretch()
        self.chips_widget.setVisible(False)
        main_layout.addWidget(self.chips_widget)

        # Fila de input
        input_container = QHBoxLayout()
        input_container.setSpacing(6)

        self.btn_attach = create_icon_button(get_attach_icon(), "GradientButton", "attach", lambda _: self._abrir_archivo())
        self.btn_attach.setObjectName("BtnAttach")
        self.btn_attach.setFixedSize(34, 34)
        self.btn_attach.setIconSize(QSize(17, 17))

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(t("ask_placeholder"))
        self.input_field.setFixedHeight(36)
        self.input_field.setObjectName("ChatInput")
        self.input_field.returnPressed.connect(self.enviar_mensaje)

        self.btn_enviar = create_icon_button(get_send_icon(), "GradientButton", "enviar", lambda _: self.enviar_mensaje())
        self.btn_enviar.setObjectName("BtnEnviar")
        self.btn_enviar.setFixedSize(34, 34)
        self.btn_enviar.setIconSize(QSize(17, 17))

        self.btn_extra = create_icon_button(get_camera_icon(), "GradientButton", "camara", lambda _: self.iniciar_captura())
        self.btn_extra.setObjectName("BtnExtra")
        self.btn_extra.setFixedSize(34, 34)
        self.btn_extra.setIconSize(QSize(17, 17))

        self.btn_stop = create_icon_button(get_stop_icon(), "GradientButton", "stop", lambda _: self.detener_generacion())
        self.btn_stop.setObjectName("BtnStop")
        self.btn_stop.setFixedSize(34, 34)
        self.btn_stop.setIconSize(QSize(17, 17))
        self.btn_stop.setVisible(False)

        input_container.addWidget(self.btn_attach)
        input_container.addWidget(self.input_field)
        input_container.addWidget(self.btn_stop)
        input_container.addWidget(self.btn_extra)
        input_container.addWidget(self.btn_enviar)
        main_layout.addLayout(input_container)

    # ── Nombre conversación ───────────────────────────────────────────────────

    def _actualizar_nombre(self):
        if self.conversation_id is None:
            self.lbl_conv_name.setText("")
            return
        self.lbl_conv_name.setText(get_conversation_name(self.conversation_id))

    # ── Interfaz pública ──────────────────────────────────────────────────────

    def focus_input(self):
        self.input_field.setFocus()

    def retranslate_ui(self):
        self.new_chat_btn.setText(t("new_conversation"))
        self.input_field.setPlaceholderText(t("ask_placeholder"))

    def insertar_texto(self, texto):
        self.input_field.setText(texto)
        self.input_field.setFocus()

    # ── Adjuntos ──────────────────────────────────────────────────────────────

    def _abrir_archivo(self):
        # PopupPanel es Qt.WindowType.Popup y se cierra al perder foco.
        # Abrimos el diálogo sin parent (None) con WindowStaysOnTopHint
        # y re-mostramos el popup después.
        popup = self.parent()

        dialog = QFileDialog(None, t("attach_file"), "", t("images_docs"))
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)

        if dialog.exec():
            paths = dialog.selectedFiles()
            if paths:
                path = paths[0]
                mime, _ = mimetypes.guess_type(path)
                mime = mime or "application/octet-stream"
                self.pending.append({
                    "path": path,
                    "mime_type": mime,
                    "name": os.path.basename(path),
                })
                self._refresh_chips()

        if popup and not popup.isVisible():
            popup.show()

    def _refresh_chips(self):
        # Limpiar chips existentes (preservar el stretch al final)
        while self.chips_layout.count() > 1:
            item = self.chips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, att in enumerate(self.pending):
            chip = QPushButton(f"📎 {att['name']}  ✕")
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.setStyleSheet(
                "background-color: rgba(123,104,238,0.20);"
                "border: 1px solid rgba(123,104,238,0.40);"
                "border-radius: 8px;"
                "color: rgba(255,255,255,0.85);"
                "font-size: 11px;"
                "padding: 2px 6px;"
            )
            chip.clicked.connect(lambda checked, idx=i: self._remove_attach(idx))
            self.chips_layout.insertWidget(self.chips_layout.count() - 1, chip)

        self.chips_widget.setVisible(bool(self.pending))

    def _remove_attach(self, idx: int):
        if 0 <= idx < len(self.pending):
            self.pending.pop(idx)
        self._refresh_chips()

    # ── Captura de pantalla ───────────────────────────────────────────────────

    def iniciar_captura(self):
        self.window().hide()
        from services.region_selector import select_region
        select_region(lambda path: self.region_ready.emit(path))

    def _on_region_captured(self, path: str):
        self.window().show()
        popup = self.parent()
        if popup and not popup.isVisible():
            popup.show()
        self.pending.append({
            "path": path,
            "mime_type": "image/png",
            "name": "captura.png",
        })
        self._refresh_chips()

    # ── Scroll ────────────────────────────────────────────────────────────────

    def _on_scroll_changed(self, value):
        sb = self.scroll_area.verticalScrollBar()
        self._auto_scroll = value >= sb.maximum() - 30

    def _scroll_to_bottom(self):
        if self._auto_scroll:
            sb = self.scroll_area.verticalScrollBar()
            sb.setValue(sb.maximum())

    # ── Burbujas ──────────────────────────────────────────────────────────────

    def _create_ai_bubble(self):
        bubble = QTextEdit()
        bubble.setReadOnly(True)
        bubble.setFixedWidth(260)
        bubble.setFixedHeight(36)
        bubble.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        bubble.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        bubble.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        bubble.setObjectName("AIBubble")
        bubble.document().setDocumentMargin(12)
        bubble.viewport().setStyleSheet("background: transparent;")
        return bubble

    def _update_bubble_height(self, bubble):
        bubble.document().setTextWidth(260)
        doc_height = int(bubble.document().size().height())
        bubble.setFixedHeight(doc_height + 20)

    def add_bubble(self, text, role, attachments=None):
        if role == "user" and attachments:
            # Fila de chips de adjuntos encima de la burbuja de texto
            for name in attachments:
                chip = QLabel(f"📎 {name}")
                chip.setContentsMargins(8, 4, 8, 4)
                chip.setStyleSheet(
                    "background-color: rgba(123,104,238,0.25);"
                    "border: 1px solid rgba(123,104,238,0.45);"
                    "border-radius: 8px;"
                    "color: rgba(255,255,255,0.85);"
                    "font-size: 11px;"
                )
                self.messages_layout.addWidget(chip, alignment=Qt.AlignmentFlag.AlignRight)

        if not text:
            self._scroll_to_bottom()
            return

        bubble = QLabel(text)
        bubble.setWordWrap(True)
        bubble.setFixedWidth(220)
        bubble.setContentsMargins(12, 8, 12, 8)
        bubble.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        if role == "user":
            bubble.setStyleSheet(
                "background-color: rgba(123, 104, 238, 0.18);"
                "border: 1px solid rgba(123, 104, 238, 0.25);"
                "border-radius: 12px;"
                "color: rgba(255, 255, 255, 0.90);"
                "font-size: 13px;"
            )
            self.messages_layout.addWidget(bubble, alignment=Qt.AlignmentFlag.AlignRight)
        else:
            bubble.setStyleSheet(
                "background-color: rgba(255, 255, 255, 0.06);"
                "border: 1px solid rgba(255, 255, 255, 0.08);"
                "border-radius: 12px;"
                "color: rgba(255, 255, 255, 0.80);"
                "font-size: 13px;"
            )
            self.messages_layout.addWidget(bubble, alignment=Qt.AlignmentFlag.AlignLeft)

        h = bubble.heightForWidth(220)
        if h > 0:
            bubble.setFixedHeight(h)

        self._scroll_to_bottom()

    # ── Enviar ────────────────────────────────────────────────────────────────

    def enviar_mensaje(self):
        texto = self.input_field.text().strip()
        if not texto and not self.pending:
            return

        self._auto_scroll = True

        if self.conversation_id is None:
            self.conversation_id = create_conversation()
            nombre = texto[:45] + "..." if len(texto) > 45 else texto
            rename_conversation(self.conversation_id, nombre or "Archivo adjunto")
            self._actualizar_nombre()

        add_message(self.conversation_id, "user", texto)
        self.add_bubble(texto, "user", attachments=[a["name"] for a in self.pending])
        self.input_field.clear()
        self.input_field.setEnabled(False)

        self.current_response = ""
        self.ai_bubble = self._create_ai_bubble()
        self.messages_layout.addWidget(self.ai_bubble, alignment=Qt.AlignLeft)

        historial = get_messages(self.conversation_id)

        from datetime import datetime
        system_msg = {
            "role": "user",
            "content": f"[Sistema: Fecha y hora actual: {datetime.now().strftime('%A, %d de %B de %Y, %H:%M')}]"
        }
        historial = [system_msg] + list(historial)

        if self.pending and historial:
            historial[-1] = dict(historial[-1])
            historial[-1]["attachments"] = list(self.pending)

        self.pending = []
        self._refresh_chips()

        self.worker = GeminiThread(historial)
        self.worker.chunk_received.connect(self.on_chunk)
        self.worker.completed.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.btn_stop.setVisible(True)
        self.btn_enviar.setVisible(False)
        self.worker.start()

    # ── Detener ───────────────────────────────────────────────────────────────

    def detener_generacion(self):
        self._render_timer.stop()
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.stop()
        if hasattr(self, 'current_response') and self.current_response:
            add_message(self.conversation_id, "assistant", self.current_response)
            html = md.markdown(self.current_response, extensions=["fenced_code", "tables"])
            self.ai_bubble.setHtml(f'<div style="color:white;">{html}</div>')
            self._update_bubble_height(self.ai_bubble)
        self.btn_stop.setVisible(False)
        self.btn_enviar.setVisible(True)
        self.input_field.setEnabled(True)
        self.input_field.setFocus()

    # ── Cargar / nueva conversación ───────────────────────────────────────────

    def load_conversation(self, conversation_id):
        self._render_timer.stop()
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.completed.disconnect()
            self.worker.chunk_received.disconnect()
            self.worker.error.disconnect()
            self.worker.stop()
        self.btn_stop.setVisible(False)
        self.btn_enviar.setVisible(True)
        self.input_field.setEnabled(True)
        self.pending = []
        self._refresh_chips()

        self.conversation_id = conversation_id
        self._actualizar_nombre()

        while self.messages_layout.count():
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for msg in get_messages(conversation_id):
            if msg["role"] == "user":
                self.add_bubble(msg["content"], "user")
            else:
                bubble = self._create_ai_bubble()
                html = md.markdown(msg["content"], extensions=["fenced_code", "tables"])
                bubble.setHtml(f'<div style="color:white;">{html}</div>')
                self.messages_layout.addWidget(bubble, alignment=Qt.AlignLeft)
                self._update_bubble_height(bubble)

    def nueva_conversacion(self):
        self._render_timer.stop()
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.completed.disconnect()
            self.worker.chunk_received.disconnect()
            self.worker.error.disconnect()
            self.worker.stop()
        self.btn_stop.setVisible(False)
        self.btn_enviar.setVisible(True)
        self.input_field.setEnabled(True)
        self.pending = []
        self._refresh_chips()
        self.conversation_id = None
        self._actualizar_nombre()
        while self.messages_layout.count():
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    # ── Streaming ─────────────────────────────────────────────────────────────

    def _flush_render(self):
        if self._pending_render:
            self.ai_bubble.setPlainText(self.current_response)
            self._update_bubble_height(self.ai_bubble)
            self._scroll_to_bottom()
            self._pending_render = False
        else:
            self._render_timer.stop()

    def on_chunk(self, text):
        self.current_response += text
        self._pending_render = True
        if not self._render_timer.isActive():
            self._render_timer.start()

    def on_finished(self):
        self._render_timer.stop()
        add_message(self.conversation_id, "assistant", self.current_response)
        html = md.markdown(self.current_response, extensions=["fenced_code", "tables"])
        self.ai_bubble.setHtml(f'<div style="color:white;">{html}</div>')
        self._update_bubble_height(self.ai_bubble)
        self.btn_stop.setVisible(False)
        self.btn_enviar.setVisible(True)
        self.input_field.setEnabled(True)
        self.input_field.setFocus()

    def on_error(self, error_msg):
        self._render_timer.stop()
        self.ai_bubble.setPlainText(f"Error: {error_msg}")
        self._update_bubble_height(self.ai_bubble)
        self.btn_stop.setVisible(False)
        self.btn_enviar.setVisible(True)
        self.input_field.setEnabled(True)
