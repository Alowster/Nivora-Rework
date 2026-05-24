from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QScrollArea
from PySide6.QtCore import Qt, Signal

from data.database import get_all_conversations, delete_conversation
from translations import t

class HistoryPanel(QWidget):
    conversation_selected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setContentsMargins(15, 15, 15, 15)

        self.cargar_y_agrupar()
        self.init_ui()

    def init_ui(self):
        fila = QHBoxLayout()

        self.btn_anterior = QPushButton("<")
        self.btn_anterior.clicked.connect(self._mes_anterior)
        self.btn_anterior.setProperty("class", "NavButton")
        self.btn_anterior.setCursor(Qt.CursorShape.PointingHandCursor)

        self.lbl_mes = QLabel()
        self.lbl_mes.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_siguiente = QPushButton(">")
        self.btn_siguiente.clicked.connect(self._mes_siguiente)
        self.btn_siguiente.setProperty("class", "NavButton")
        self.btn_siguiente.setCursor(Qt.CursorShape.PointingHandCursor)

        fila.addWidget(self.btn_anterior)
        fila.addWidget(self.lbl_mes)
        fila.addWidget(self.btn_siguiente)
        self.layout_principal.addLayout(fila)

        self._lista_widget = QWidget()

        self._lista_layout = QVBoxLayout(self._lista_widget)
        self._lista_layout.setContentsMargins(0, 0, 0, 0)
        self._lista_layout.setSpacing(4)
        self._lista_layout.addStretch()

        self._scroll = QScrollArea()
        self._scroll.setWidget(self._lista_widget)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self._scroll.viewport().setStyleSheet("QWidget { background: transparent; }")
        self.layout_principal.addWidget(self._scroll)

        self._actualizar_header()

    def cargar_y_agrupar(self):
        conversaciones = get_all_conversations()
        self._grupos = {}
        for conv in conversaciones:
            fecha = conv["created_at"][:7]
            anyo, mes = fecha.split("-")
            clave = (int(anyo), int(mes))
            self._grupos.setdefault(clave, []).append(conv)
        self._meses = sorted(self._grupos.keys(), reverse=True)
        self._mes_idx = 0

    def _actualizar_header(self):
        if not self._meses:
            self.lbl_mes.setText(t("no_conversations"))
            self.btn_anterior.setEnabled(False)
            self.btn_siguiente.setEnabled(False)
            return
        anyo, mes = self._meses[self._mes_idx]
        month_names = t("month_names")
        self.lbl_mes.setText(f"{month_names[mes - 1]} {anyo}")
        self.btn_anterior.setEnabled(self._mes_idx < len(self._meses) - 1)
        self.btn_siguiente.setEnabled(self._mes_idx > 0)
        self._mostrar_mes()

    def _mostrar_mes(self):
        while self._lista_layout.count() > 1:
            item = self._lista_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        convs = self._grupos[self._meses[self._mes_idx]]
        for conv in convs:
            fila = QWidget()
            fila_layout = QHBoxLayout(fila)
            fila_layout.setContentsMargins(0, 0, 0, 0)
            fila_layout.setSpacing(4)

            btn = QPushButton(conv["name"])
            btn.setProperty("class", "TaskItem")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, cid=conv["id"]: self.conversation_selected.emit(cid))

            btn_del = QPushButton("✕")
            btn_del.setProperty("class", "DeleteButton")
            btn_del.setFixedSize(24, 24)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.clicked.connect(lambda _, cid=conv["id"]: self._eliminar_conversacion(cid))

            fila_layout.addWidget(btn)
            fila_layout.addWidget(btn_del)
            self._lista_layout.insertWidget(self._lista_layout.count() - 1, fila)

    def _eliminar_conversacion(self, conversation_id):
        delete_conversation(conversation_id)
        self.refresh()

    def _mes_anterior(self):
        if self._mes_idx < len(self._meses) - 1:
            self._mes_idx += 1
            self._actualizar_header()

    def _mes_siguiente(self):
        if self._mes_idx > 0:
            self._mes_idx -= 1
            self._actualizar_header()

    def refresh(self):
        self.cargar_y_agrupar()
        self._actualizar_header()

    def retranslate_ui(self):
        self._actualizar_header()
