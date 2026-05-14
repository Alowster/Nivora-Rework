from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QTextEdit, QPushButton,
    QScrollArea, QFrame, QSizePolicy, QLabel, QButtonGroup
)
from PySide6.QtCore import Qt, QTimer, QEvent, Signal
from PySide6.QtGui import QKeySequence


from data.database import get_all_macros, create_macro, update_macro_hotkey, delete_macro
import subprocess


class _ContentTextEdit(QTextEdit):
    """QTextEdit sin rich text (evita convertir URLs) y con Space funcional en Popup."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptRichText(False)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self.insertPlainText(" ")
            event.accept()
            return
        super().keyPressEvent(event)


_STYLE_IDLE = (
    "border: 1px solid rgba(255,255,255,0.15);"
    "border-radius: 6px;"
    "background: rgba(255,255,255,0.06);"
    "color: rgba(255,255,255,0.7);"
    "font-size: 11px;"
    "padding: 2px 6px;"
)
_STYLE_CAPTURING = (
    "border: 1.5px solid rgba(123,104,238,0.9);"
    "border-radius: 6px;"
    "background: rgba(123,104,238,0.18);"
    "color: white;"
    "font-size: 11px;"
    "font-weight: bold;"
    "padding: 2px 6px;"
)


class HotkeyCapture(QLineEdit):
    confirmed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setPlaceholderText("Click para asignar...")
        self.setStyleSheet(_STYLE_IDLE)
        self._capturing = False
        self._held_keys = []   # teclas no-modificadoras acumuladas

    def mousePressEvent(self, event):
        self._capturing = True
        self._held_keys = []
        self.setText("")
        self.setPlaceholderText("Pulsa teclas… Enter para confirmar")
        self.setStyleSheet(_STYLE_CAPTURING)
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if not self._capturing:
            return

        key = event.key()

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._capturing = False
            self._held_keys = []
            self.setPlaceholderText("Click para asignar...")
            self.setStyleSheet(_STYLE_IDLE)
            self.confirmed.emit()
            return

        if key == Qt.Key.Key_Escape:
            self._capturing = False
            self._held_keys = []
            self.clear()
            self.setPlaceholderText("Click para asignar...")
            self.setStyleSheet(_STYLE_IDLE)
            return

        # Teclas modificadoras solas: no añadir, solo refrescar display
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift,
                   Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            self._update_display(event.modifiers())
            return

        # Obtener texto de la tecla
        key_text = event.text()
        if not key_text or not key_text.isprintable():
            key_text = QKeySequence(key).toString().lower()
        key_text = key_text.lower()

        # Acumular sin duplicados
        if key_text and key_text not in self._held_keys:
            self._held_keys.append(key_text)

        self._update_display(event.modifiers())

    def _update_display(self, modifiers):
        parts = []
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            parts.append("ctrl")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            parts.append("shift")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            parts.append("alt")
        parts.extend(self._held_keys)
        self.setText("+".join(parts))

class ClickableLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class HotkeyBadge(QWidget):
    changed = Signal()

    def __init__(self, macro_id, hotkey):
        super().__init__()
        self.macro_id = macro_id
        self._confirming = False
        self._destroyed = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.badge = QPushButton(hotkey if hotkey else "+")
        self.badge.setProperty("class", "HotkeyBadge" if hotkey else "HotkeyBadge--empty")
        self.badge.setCursor(Qt.CursorShape.PointingHandCursor)
        self.badge.setFixedHeight(24)
        self.badge.clicked.connect(self._enter_edit)

        self.editor = HotkeyCapture()
        self.editor.setFixedWidth(90)
        self.editor.setFixedHeight(24)
        self.editor.hide()
        self.editor.confirmed.connect(self._confirm)
        self.editor.installEventFilter(self)

        layout.addWidget(self.badge)
        layout.addWidget(self.editor)

    def _enter_edit(self):
        texto_actual = self.badge.text()
        self.editor.setText("" if texto_actual == "+" else texto_actual)
        self.badge.hide()
        self.editor.show()
        self.editor.setFocus()

    def _confirm(self):
        if self._confirming or self._destroyed:
            return
        self._confirming = True
        try:
            nuevo = self.editor.text().strip()
            update_macro_hotkey(self.macro_id, nuevo or None)
            self.badge.setText(nuevo if nuevo else "+")
            clase = "HotkeyBadge" if nuevo else "HotkeyBadge--empty"
            self.badge.setProperty("class", clase)
            self.badge.style().unpolish(self.badge)
            self.badge.style().polish(self.badge)
            self.editor.hide()
            self.badge.show()
            self.changed.emit()
        finally:
            self._confirming = False

    def eventFilter(self, obj, event):
        if obj is self.editor and event.type() == QEvent.Type.FocusOut:
            QTimer.singleShot(0, self._safe_confirm)
        return super().eventFilter(obj, event)

    def _safe_confirm(self):
        try:
            if self._destroyed or not self.editor or not self.editor.isVisible():
                return
            self._confirm()
        except RuntimeError:
            pass

    def closeEvent(self, event):
        self._destroyed = True
        super().closeEvent(event)

class MacroRow(QFrame):
    delete_requested = Signal(int)
    executed = Signal(dict)

    def __init__(self, macro):
        super().__init__()
        self.macro_id = macro["id"]
        self.macro_data = macro
        self.setFixedHeight(38)
        self.setProperty("class", "MacroRow")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 8, 0)
        layout.setSpacing(8)

        tipo_icon = QLabel("📋" if macro["type"] == "text" else "⚡")
        tipo_icon.setFixedWidth(18)
        tipo_icon.setProperty("class", "TypeIcon")

        self.lbl_nombre = ClickableLabel(macro["name"])
        self.lbl_nombre.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.lbl_nombre.setProperty("class", "MacroRowLabel")
        self.lbl_nombre.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lbl_nombre.clicked.connect(lambda: self.executed.emit(self.macro_data))

        self.badge = HotkeyBadge(macro["id"], macro["hotkey"])

        btn_delete = QPushButton("✕")
        btn_delete.setFixedSize(22, 22)
        btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_delete.setProperty("class", "DeleteButton")
        btn_delete.clicked.connect(lambda: self.delete_requested.emit(self.macro_id))

        layout.addWidget(tipo_icon)
        layout.addWidget(self.lbl_nombre)
        layout.addWidget(self.badge)
        layout.addWidget(btn_delete)


class MacrosPanel(QWidget):
    macro_triggered = Signal(str)
    macros_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._cargar_macros()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # ── Formulario superior ──
        form = QWidget()
        form_layout = QVBoxLayout(form)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(6)

        lbl_nueva = QLabel("Nueva macro")
        lbl_nueva.setProperty("class", "SectionLabel")

        self.input_nombre = QLineEdit()
        self.input_nombre.setPlaceholderText("Nombre de la macro...")
        self.input_nombre.setFixedHeight(32)
        self.input_nombre.setProperty("class", "GlassInput")

        # Toggle tipo con QButtonGroup para exclusividad real
        tipo_row = QHBoxLayout()
        tipo_row.setSpacing(6)
        self.btn_text = QPushButton("Pegar texto")
        self.btn_shell = QPushButton("Ejecutar")
        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)
        for i, btn in enumerate((self.btn_text, self.btn_shell)):
            btn.setFixedHeight(28)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("class", "ToggleButton")
            self._btn_group.addButton(btn, i)
        self.btn_text.setChecked(True)
        self._btn_group.idClicked.connect(self._on_tipo_changed)
        self._tipo = "text"
        tipo_row.addWidget(self.btn_text)
        tipo_row.addWidget(self.btn_shell)

        self.lbl_tipo_desc = QLabel("El contenido se pegará en el chat al ejecutar.")
        self.lbl_tipo_desc.setProperty("class", "DescLabel")
        self.lbl_tipo_desc.setWordWrap(True)

        self.input_contenido = _ContentTextEdit()
        self.input_contenido.setPlaceholderText("Escribe el texto a pegar...")
        self.input_contenido.setFixedHeight(55)
        self.input_contenido.setProperty("class", "GlassTextEdit")

        btn_guardar = QPushButton("+ Añadir macro")
        btn_guardar.setFixedHeight(30)
        btn_guardar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_guardar.setProperty("class", "AddButton")
        btn_guardar.clicked.connect(self._guardar_macro)

        form_layout.addWidget(lbl_nueva)
        form_layout.addWidget(self.input_nombre)
        form_layout.addLayout(tipo_row)
        form_layout.addWidget(self.lbl_tipo_desc)
        form_layout.addWidget(self.input_contenido)
        form_layout.addWidget(btn_guardar)

        # ── Separador ──
        separador = QFrame()
        separador.setFrameShape(QFrame.Shape.HLine)
        separador.setProperty("class", "HSeparator")

        # ── Lista inferior ──
        lbl_lista = QLabel("Mis macros")
        lbl_lista.setProperty("class", "SectionLabel")

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

        main_layout.addWidget(form)
        main_layout.addWidget(separador)
        main_layout.addWidget(lbl_lista)
        main_layout.addWidget(self._scroll)

    def _on_tipo_changed(self, btn_id):
        self._tipo = "text" if btn_id == 0 else "shell"
        if self._tipo == "text":
            self.lbl_tipo_desc.setText("El contenido se pegará en el chat al ejecutar.")
            self.input_contenido.setPlaceholderText("Escribe el texto a pegar...")
        else:
            self.lbl_tipo_desc.setText("El contenido se ejecutará como comando de sistema.")
            self.input_contenido.setPlaceholderText("Ej: notepad.exe  /  start chrome https://www.youtube.com/")

    def _guardar_macro(self):
        nombre = self.input_nombre.text().strip()
        contenido = self.input_contenido.toPlainText().strip()
        if not nombre or not contenido:
            return
        create_macro(nombre, contenido, self._tipo)
        self.input_nombre.clear()
        self.input_contenido.clear()
        self._cargar_macros()
        self.macros_changed.emit()

    def _cargar_macros(self):
        while self._lista_layout.count() > 1:
            item = self._lista_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        macros = get_all_macros()
        if not macros:
            lbl = QLabel("Sin macros. ¡Crea una arriba!")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setProperty("class", "EmptyLabel")
            self._lista_layout.insertWidget(0, lbl)
            return

        for macro in macros:
            row = MacroRow(macro)
            row.delete_requested.connect(self._eliminar)
            row.executed.connect(self._ejecutar)
            row.badge.changed.connect(self.macros_changed.emit)
            self._lista_layout.insertWidget(self._lista_layout.count() - 1, row)

    def _ejecutar(self, macro):
        if macro["type"] == "text":
            self.macro_triggered.emit(macro["content"])
        else:
            try:
                subprocess.Popen(macro["content"], shell=True)
            except Exception as e:
                print(f"Error ejecutando macro shell: {e}")

    def _eliminar(self, macro_id):
        delete_macro(macro_id)
        QTimer.singleShot(0, self._cargar_macros)
        self.macros_changed.emit()
