# Plan de migración: PySide6 → NiceGUI

## Resumen

Reemplazar toda la capa de UI (PySide6) por NiceGUI manteniendo intacta la lógica de negocio. Los servicios, la base de datos y los helpers de hotkeys/OCR se reutilizan sin cambios relevantes.

---

## Qué se conserva sin tocar

| Archivo | Motivo |
|---|---|
| `data/database.py` | Puro SQLite, sin dependencias de Qt |
| `services/ocr_service.py` | Eliminar herencia de `QThread`; la lógica PIL/RapidOCR se queda igual |
| `services/ollama_manager.py` | Subprocess puro, sin cambios |
| `services/hotkey_manager.py` | Eliminar herencia de `QObject/Signal`; la lógica `keyboard` se queda igual |
| `config.py` | Quitar constantes de Qt (colores RGBA, tamaños de ventana). Mantener `OLLAMA_MODEL`, `OLLAMA_MAX_TOKENS`, `DB_PATH` |

---

## Qué se elimina

- `ui/` completo (panels, widgets)
- `assets/icons.py` y `assets/styles.qss`
- Dependencias: `PySide6`, `markdown` (NiceGUI renderiza markdown nativamente)

---

## Arquitectura nueva

```
main.py                  ← arranca NiceGUI + hilo de hotkeys
ui/
  chat_page.py           ← página de chat con streaming
  history_page.py        ← historial paginado por mes
  macros_page.py         ← CRUD de macros + asignación de hotkeys
services/
  ai_service.py          ← generador async (sin QThread)
  ocr_service.py         ← función síncrona (sin QThread)
  hotkey_manager.py      ← clase pura con threading (sin QObject)
  ollama_manager.py      ← sin cambios
data/
  database.py            ← sin cambios
config.py                ← reducido
```

---

## Pasos de implementación

### Paso 1 — Preparar el entorno

```
pip install nicegui ollama rapidocr-onnxruntime pillow keyboard
pip uninstall PySide6 markdown
```

### Paso 2 — Refactorizar servicios (quitar Qt)

**`services/ai_service.py`** — convertir de `QThread` a generador `async`:

```python
import ollama
from config import OLLAMA_MODEL, OLLAMA_MAX_TOKENS

async def stream_response(messages: list) -> AsyncGenerator[str, None]:
    stream = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": m["role"], "content": m["content"]} for m in messages],
        stream=True,
        options={"num_predict": OLLAMA_MAX_TOKENS}
    )
    for chunk in stream:
        yield chunk["message"]["content"]
```

**`services/ocr_service.py`** — convertir de `QThread` a función síncrona:

```python
def run_ocr(x, y, w, h) -> str:
    imagen = ImageGrab.grab(bbox=(x, y, x + w, y + h))
    # ... mismo procesamiento PIL/RapidOCR ...
    return texto
```

**`services/hotkey_manager.py`** — eliminar `QObject` y `Signal`. Usar callbacks directos:

```python
import keyboard, threading
from data.database import get_all_macros

class HotkeyManager:
    def __init__(self, on_shell_macro):
        self._on_shell_macro = on_shell_macro  # callable(macro: dict)
        self._handles = []

    def reload(self):
        try:
            self._unregister_all()
            for macro in get_all_macros():
                hotkey = (macro.get("hotkey") or "").strip()
                if not hotkey:
                    continue
                try:
                    handle = keyboard.add_hotkey(
                        hotkey,
                        self._make_callback(macro),
                        suppress=True,
                    )
                    self._handles.append(handle)
                except Exception as e:
                    print(f"Error registrando {hotkey}: {e}")
        except Exception as e:
            # Importante: keyboard requiere permisos de Admin en Windows
            print(f"Error crítico en HotkeyManager (¿faltan permisos de Admin?): {e}")
```

### Paso 3 — Selector de región (overlay Tkinter)

Crear `services/region_selector.py` como proceso auxiliar con Tkinter (incluido en Python, sin instalar nada extra):

```python
import tkinter as tk
from PIL import ImageGrab
import threading

def select_region(callback):
    """Abre overlay fullscreen Tkinter, llama callback(x, y, w, h) al soltar."""
    def _run():
        root = tk.Tk()
        root.attributes("-fullscreen", True)
        root.attributes("-alpha", 0.3)
        root.configure(bg="black")
        root.attributes("-topmost", True)

        start = {}
        canvas = tk.Canvas(root, cursor="crosshair", bg="black")
        canvas.pack(fill="both", expand=True)
        rect_id = None

        def on_press(e):
            start["x"], start["y"] = e.x_root, e.y_root
        def on_drag(e):
            nonlocal rect_id
            if rect_id:
                canvas.delete(rect_id)
            rect_id = canvas.create_rectangle(
                start["x"] - root.winfo_rootx(), start["y"] - root.winfo_rooty(),
                e.x - root.winfo_rootx(), e.y - root.winfo_rooty(),
                outline="white", width=2
            )
        def on_release(e):
            x1, y1 = min(start["x"], e.x_root), min(start["y"], e.y_root)
            x2, y2 = max(start["x"], e.x_root), max(start["y"], e.y_root)
            root.quit() # Salir del mainloop de forma segura
            root.destroy()
            if x2 - x1 > 5 and y2 - y1 > 5:
                # El callback debe ser rápido o usar ui.run_javascript / app.queue_btn
                callback(x1, y1, x2 - x1, y2 - y1)

        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)
        root.bind("<Escape>", lambda e: root.destroy())
        root.mainloop()

    threading.Thread(target=_run, daemon=True).start()
```

### Paso 4 — `main.py` con NiceGUI

```python
from nicegui import ui, app
from services.ollama_manager import ensure_ollama_running
from services.hotkey_manager import HotkeyManager
from data.database import init_db
from ui.chat_page import chat_page
from ui.history_page import history_page
from ui.macros_page import macros_page

hotkey_manager = HotkeyManager(on_shell_macro=lambda m: None)

@app.on_startup
async def startup():
    init_db()
    ensure_ollama_running()
    hotkey_manager.reload()

@app.on_shutdown
async def shutdown():
    hotkey_manager.shutdown()

@ui.page('/')
def index():
    with ui.tabs().classes('w-full') as tabs:
        chat_tab    = ui.tab('Chat')
        history_tab = ui.tab('Historial')
        macros_tab  = ui.tab('Macros')
    with ui.tab_panels(tabs, value=chat_tab).classes('w-full'):
        with ui.tab_panel(chat_tab):
            chat_page()
        with ui.tab_panel(history_tab):
            history_page()
        with ui.tab_panel(macros_tab):
            macros_page(hotkey_manager)

ui.run(title='Nivora', dark=True, port=8080, reload=False, storage_secret='nivora_secret_key_123')
```

### Paso 5 — `ui/chat_page.py`

Funciones a implementar usando API de NiceGUI:

- `ui.chat_message` para cada burbuja (o `ui.markdown` dentro de `ui.card`)
- `ui.input` para el campo de texto + `ui.button` enviar/detener/cámara
- Streaming: `async for chunk in stream_response(messages)` + `ui.notify` o actualización directa del elemento
- Botón cámara: llama a `select_region()` → `run_ocr()` → inserta texto en el input
- Botón "Nueva conversación": llama `create_conversation()` y limpia el scroll
- El nombre de la conversación se muestra con `ui.label` en la parte superior

Reutiliza directamente: `data/database.py` (todas sus funciones), `services/ai_service.py`, `services/ocr_service.py`, `services/region_selector.py`

### Paso 6 — `ui/history_page.py`

- `ui.select` o botones `<` / `>` para navegar entre meses
- Lista de conversaciones con `ui.list` + `ui.item` clicables
- Al clicar una conversación: navegar a `/` con el `conversation_id` como query param o mediante estado compartido

Reutiliza: `data/database.get_all_conversations()`

### Paso 7 — `ui/macros_page.py`

- Tabla con `ui.table` o lista de `ui.card` mostrando nombre, hotkey, tipo
- Formulario inline para crear macro: nombre, tipo (shell/text), contenido, hotkey
- Campo de hotkey: `ui.input` con captura de teclas vía JavaScript (`on_keydown`)
- Botón eliminar por fila
- Al guardar/eliminar: llamar `hotkey_manager.reload()`

Reutiliza: `data/database.get_all_macros()`, `create_macro()`, `update_macro_hotkey()`, `delete_macro()`

---

## Gestión del estado entre páginas (chat ↔ historial)

NiceGUI usa estado por sesión. Crear `state.py`:

```python
from nicegui import storage

def get_active_conversation() -> int | None:
    return app.storage.user.get("conversation_id")

def set_active_conversation(conv_id: int):
    app.storage.user["conversation_id"] = conv_id
```

---

## Hotkeys globales — hilo de fondo

`HotkeyManager` sigue usando la librería `keyboard` en un hilo de fondo independiente de NiceGUI. Los callbacks de macros de tipo `shell` ejecutan `subprocess.run()` directamente. Los de tipo `text` siguen usando `keyboard.write()`. No se necesita ninguna integración especial con NiceGUI.

---

## Dependencias finales

```
nicegui
ollama
rapidocr-onnxruntime
pillow
keyboard
```

---

## Orden de trabajo recomendado

1. Refactorizar `ai_service.py`, `ocr_service.py`, `hotkey_manager.py` (quitar Qt)
2. Crear `services/region_selector.py` (Tkinter)
3. Montar `main.py` con las tres tabs vacías y verificar que arranca
4. Implementar `ui/chat_page.py` con chat básico sin OCR
5. Añadir streaming de IA al chat
6. Añadir captura de región + OCR al chat
7. Implementar `ui/history_page.py`
8. Implementar `ui/macros_page.py`
9. Conectar hotkey_manager con macros_page (reload tras cambios)
10. Limpiar dependencias y archivos PySide6

---

## Verificación

- Arrancar con `python main.py` y abrir `http://localhost:8080`
- Enviar mensaje → respuesta en streaming aparece token a token
- Capturar región → el texto OCR aparece en el input
- Crear macro tipo `shell` con hotkey → ejecutar con la hotkey fuera del navegador
- Crear macro tipo `text` → hotkey escribe el texto en la app activa
- Navegar al historial → ver conversaciones por mes → clicar una y abrirla en el chat
