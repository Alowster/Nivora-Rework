import json
import os

TRANSLATIONS = {
    "es": {
        "settings_title": "Ajustes",
        "opacity": "Opacidad de la ventana",
        "ui_size": "Tamaño de la interfaz",
        "window_size": "Tamaño de la ventana",
        "language": "Idioma",
        "new_conversation": "+ Nueva conversación",
        "ask_placeholder": "Hazme una pregunta...",
        "attach_file": "Adjuntar archivo",
        "images_docs": "Imágenes y documentos (*.png *.jpg *.jpeg *.gif *.webp *.pdf *.txt *.csv)",
        "new_macro": "Nueva macro",
        "macro_name_placeholder": "Nombre de la macro...",
        "paste_text": "Pegar texto",
        "run": "Ejecutar",
        "paste_hint": "El contenido se pegará en el chat al ejecutar.",
        "paste_placeholder": "Escribe el texto a pegar...",
        "command_hint": "El contenido se ejecutará como comando de sistema.",
        "command_example": "Ej: notepad.exe  /  start chrome https://www.youtube.com/",
        "add_macro": "+ Añadir macro",
        "no_macros": "Sin macros. ¡Crea una arriba!",
        "my_macros": "Mis macros",
        "assign_hotkey": "Click para asignar...",
        "press_keys": "Pulsa teclas… Enter para confirmar",
        "show_island": "Mostrar Island",
        "exit_completely": "Salir por completo",
        "minimize": "Minimizar",
        "exit": "Salir",
        "no_conversations": "Sin conversaciones",
        "month_names": [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ],
        "settings_action": "Ajustes",
    },
    "en": {
        "settings_title": "Settings",
        "opacity": "Window opacity",
        "ui_size": "Interface size",
        "window_size": "Window size",
        "language": "Language",
        "new_conversation": "+ New conversation",
        "ask_placeholder": "Ask me a question...",
        "attach_file": "Attach file",
        "images_docs": "Images and documents (*.png *.jpg *.jpeg *.gif *.webp *.pdf *.txt *.csv)",
        "new_macro": "New macro",
        "macro_name_placeholder": "Macro name...",
        "paste_text": "Paste text",
        "run": "Run",
        "paste_hint": "Content will be pasted in chat when executed.",
        "paste_placeholder": "Write text to paste...",
        "command_hint": "Content will run as a system command.",
        "command_example": "Ex: notepad.exe  /  start chrome https://www.youtube.com/",
        "add_macro": "+ Add macro",
        "no_macros": "No macros. Create one above!",
        "my_macros": "My macros",
        "assign_hotkey": "Click to assign...",
        "press_keys": "Press keys… Enter to confirm",
        "show_island": "Show Island",
        "exit_completely": "Exit completely",
        "minimize": "Minimize",
        "exit": "Exit",
        "no_conversations": "No conversations",
        "month_names": [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ],
        "settings_action": "Settings",
    },
}

_current_lang = "es"
_SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "data", "settings.json")


def t(key: str) -> str:
    return TRANSLATIONS[_current_lang].get(key, key)


def get_language() -> str:
    return _current_lang


def set_language(lang: str) -> None:
    global _current_lang
    if lang in TRANSLATIONS:
        _current_lang = lang


def load_language() -> None:
    try:
        if os.path.exists(_SETTINGS_FILE):
            with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            lang = data.get("language", "es")
            if lang in TRANSLATIONS:
                set_language(lang)
    except Exception:
        pass


def save_language(lang: str) -> None:
    try:
        os.makedirs(os.path.dirname(_SETTINGS_FILE), exist_ok=True)
        data = {}
        if os.path.exists(_SETTINGS_FILE):
            try:
                with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass
        data["language"] = lang
        with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass
