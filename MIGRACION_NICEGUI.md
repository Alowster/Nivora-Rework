# Plan de migración: PySide6 → NiceGUI + Gemini API

## Resumen

Reemplazar toda la capa de UI (PySide6) por NiceGUI y sustituir Ollama local por la API de Gemini. La app se abre como **ventana nativa de escritorio** (Chromium embebido, sin navegador externo) usando `pywebview`.

**Por qué Gemini en vez de Ollama local**: ver `sostenibilidad.md`.

---

## Qué se conserva sin tocar

| Archivo | Motivo |
|---|---|
| `data/database.py` | Puro SQLite, sin dependencias de Qt |
| `services/hotkey_manager.py` | Eliminar herencia de `QObject/Signal`; la lógica `keyboard` se queda igual |
| `config.py` | Quitar constantes de Qt y de Ollama. Añadir `GEMINI_MODEL` |

---

## Qué se elimina

- `ui/` completo (panels, widgets)
- `assets/icons.py` y `assets/styles.qss`
- `services/ollama_manager.py` (ya no se gestiona proceso local)
- `services/ocr_service.py` (Gemini interpreta imágenes directamente, OCR local es redundante)
- Dependencias: `PySide6`, `markdown`, `ollama`, `rapidocr-onnxruntime`, `numpy`

---

## Arquitectura nueva

```
main.py                  ← arranca NiceGUI en modo nativo + hilo de hotkeys
ui/
  chat_page.py           ← página de chat con streaming + adjuntos
  history_page.py        ← historial paginado por mes
  macros_page.py         ← CRUD de macros + asignación de hotkeys
  state.py               ← estado compartido entre páginas
services/
  gemini_service.py      ← cliente async de Gemini (texto + imágenes + archivos)
  hotkey_manager.py      ← clase pura con threading (sin QObject)
  region_selector.py     ← overlay Tkinter para captura de región → imagen a Gemini
data/
  database.py            ← sin cambios
config.py                ← reducido
```

---

## Pasos de implementación

### Paso 1 — Preparar el entorno

```
pip install nicegui pywebview google-generativeai pillow keyboard
pip uninstall PySide6 markdown ollama
```

`pywebview` es el componente que hace que NiceGUI abra una ventana de escritorio real en vez de un navegador.

Configurar la API key de Gemini (una sola vez):

```powershell
# Windows — permanente para el usuario actual
[System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "tu_key_aqui", "User")
```

### Paso 2 — Refactorizar servicios (quitar Qt)

**`services/gemini_service.py`** — nuevo servicio, reemplaza `ai_service.py` y `ollama_manager.py`:

```python
import os, base64, asyncio
from pathlib import Path
from typing import AsyncGenerator
import google.generativeai as genai
from config import GEMINI_MODEL

def _init_model():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Falta variable de entorno GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(GEMINI_MODEL)

def _build_contents(messages: list) -> list:
    contents = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        parts = [m["content"]]
        for att in m.get("attachments", []):
            data = base64.b64encode(Path(att["path"]).read_bytes()).decode()
            parts.append({"inline_data": {"mime_type": att["mime_type"], "data": data}})
        contents.append({"role": role, "parts": parts})
    return contents

async def stream_response(messages: list) -> AsyncGenerator[str, None]:
    model = _init_model()
    response = await model.generate_content_async(_build_contents(messages), stream=True)
    async for chunk in response:
        if chunk.text:
            yield chunk.text
```

Formato de mensaje con adjunto opcional:

```python
# Sin adjunto:
{"role": "user", "content": "¿Qué hay en esta imagen?"}

# Con imagen adjunta:
{"role": "user", "content": "¿Qué hay aquí?",
 "attachments": [{"path": "/tmp/captura.png", "mime_type": "image/png"}]}
```

**`services/hotkey_manager.py`** — eliminar `QObject` y `Signal`. Usar callbacks directos:

```python
class HotkeyManager:
    def __init__(self, on_shell_macro):
        self._on_shell_macro = on_shell_macro
        self._handles = []

    def reload(self):
        # misma lógica keyboard.add_hotkey
        ...
```

### Paso 3 — Selector de región (overlay Tkinter)

El selector captura la región como imagen PNG y la añade directamente como adjunto al mensaje. Gemini la interpreta sin necesidad de OCR local.

Crear `services/region_selector.py`:

```python
import tkinter as tk
import threading

def select_region(callback):
    """Abre overlay fullscreen, llama callback(x, y, w, h) al soltar."""
    def _run():
        root = tk.Tk()
        root.attributes("-fullscreen", True, "-alpha", 0.3, "-topmost", True)
        root.configure(bg="black")
        start = {}
        canvas = tk.Canvas(root, cursor="crosshair", bg="black")
        canvas.pack(fill="both", expand=True)
        rect_id = None

        def on_press(e):
            start["x"], start["y"] = e.x_root, e.y_root
        def on_drag(e):
            nonlocal rect_id
            if rect_id: canvas.delete(rect_id)
            rect_id = canvas.create_rectangle(
                start["x"] - root.winfo_rootx(), start["y"] - root.winfo_rooty(),
                e.x - root.winfo_rootx(), e.y - root.winfo_rooty(),
                outline="white", width=2)
        def on_release(e):
            x1, y1 = min(start["x"], e.x_root), min(start["y"], e.y_root)
            x2, y2 = max(start["x"], e.x_root), max(start["y"], e.y_root)
            root.destroy()
            if x2 - x1 > 5 and y2 - y1 > 5:
                callback(x1, y1, x2 - x1, y2 - y1)

        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)
        root.bind("<Escape>", lambda e: root.destroy())
        root.mainloop()

    threading.Thread(target=_run, daemon=True).start()
```

El callback recibe `(x, y, w, h)` en píxeles físicos. En `chat_page.py` se usa Pillow para capturar esa región como PNG y añadirla a `pending_attachments`.

> **Advertencia Windows**: si Tkinter da problemas en hilo secundario, sustituir el overlay por inputs numéricos en NiceGUI para definir la región manualmente.

### Paso 4 — `main.py` con NiceGUI en modo nativo

```python
from nicegui import ui, app
from services.hotkey_manager import HotkeyManager
from data.database import init_db
from ui.chat_page import chat_page
from ui.history_page import history_page
from ui.macros_page import macros_page

hotkey_manager = HotkeyManager(on_shell_macro=lambda m: None)

@app.on_startup
async def startup():
    init_db()
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

ui.run(
    title='Nivora',
    dark=True,
    reload=False,
    native=True,           # abre ventana de escritorio, no navegador
    window_size=(420, 650),
    storage_secret='cambia_por_un_secreto_aleatorio',
)
```

`native=True` usa `pywebview` para renderizar la UI en una ventana Chromium embebida. El usuario no necesita abrir ningún navegador; la app aparece directamente en el escritorio como cualquier otra aplicación.

### Paso 5 — `ui/state.py`

```python
from nicegui import app

def get_active_conversation():
    return app.storage.user.get("conversation_id")

def set_active_conversation(conv_id: int):
    app.storage.user["conversation_id"] = conv_id
```

### Paso 6 — `ui/chat_page.py`

Funciones a implementar:

- `ui.chat_message` o `ui.card` + `ui.markdown` para cada burbuja
- `ui.input` para el campo de texto + botones enviar / detener / cámara / adjuntar
- Streaming: `async for chunk in stream_response(messages)` + actualización directa del elemento
- Botón cámara: `select_region()` → captura región con Pillow → guarda PNG en `/tmp` → añade a `pending_attachments` → Gemini interpreta la imagen
- Botón adjuntar: `ui.upload(accept='image/*,.pdf')` → guarda en `/tmp` → añade a `pending_attachments`
- Chips visuales para adjuntos pendientes con botón X
- Al enviar: incluir `pending_attachments` en el mensaje, luego limpiar la lista

Reutiliza: `data/database.py`, `services/gemini_service.py`, `services/region_selector.py`

### Paso 7 — `ui/history_page.py`

- Botones `<` / `>` para navegar entre meses
- Lista de conversaciones con `ui.list` + `ui.item` clicables
- Al clicar: `set_active_conversation(id)` y navegar a `/`

Reutiliza: `data/database.get_all_conversations()`, `ui/state.py`

### Paso 8 — `ui/macros_page.py`

- Lista de `ui.card` con nombre, hotkey, tipo
- Formulario para crear macro: nombre, tipo (shell/text), contenido, hotkey
- Campo hotkey con captura de teclas vía `on_keydown` en JavaScript
- Al guardar/eliminar: `hotkey_manager.reload()`

Reutiliza: `data/database.get_all_macros()`, `create_macro()`, `update_macro_hotkey()`, `delete_macro()`

---

## Gestión del estado entre páginas

NiceGUI usa estado por sesión vía `app.storage.user`. Requiere el parámetro `storage_secret` en `ui.run()` (ya incluido en Paso 4). Ver implementación en `ui/state.py` (Paso 5).

---

## Hotkeys globales — hilo de fondo

`HotkeyManager` usa la librería `keyboard` en un hilo de fondo independiente de NiceGUI. Los callbacks de macros tipo `shell` ejecutan `subprocess.run()` directamente. Los de tipo `text` usan `keyboard.write()`. No se necesita integración especial con NiceGUI.

---

## Dependencias finales

```
nicegui
pywebview
google-generativeai
pillow
keyboard
```

---

## Orden de trabajo recomendado

1. Crear `services/gemini_service.py` y probar streaming en terminal con una API key real
2. Refactorizar `services/hotkey_manager.py` (quitar Qt)
3. Crear `services/region_selector.py` (Tkinter)
4. Montar `main.py` con las tres tabs vacías y verificar que la ventana nativa abre
5. Implementar `ui/chat_page.py` con chat básico (solo texto)
6. Añadir streaming de Gemini al chat
7. Añadir adjuntos: imágenes vía upload y vía captura de región con Pillow
8. Añadir adjuntos: PDFs y otros archivos
9. Implementar `ui/history_page.py`
10. Implementar `ui/macros_page.py`
11. Conectar `hotkey_manager` con `macros_page`
12. Limpiar dependencias y archivos PySide6 / Ollama

---

## Verificación

- `python main.py` → se abre una ventana de escritorio (no el navegador)
- Enviar mensaje de texto → respuesta de Gemini en streaming token a token
- Adjuntar captura de pantalla → Gemini describe su contenido
- Adjuntar PDF → Gemini resume el documento
- Sin `GEMINI_API_KEY` en env → error claro al intentar enviar
- Capturar región → imagen enviada a Gemini → Gemini describe / extrae el texto directamente
- Crear macro tipo `shell` + hotkey → ejecutar fuera de la ventana
- Crear macro tipo `text` → hotkey escribe el texto en la app activa
- Navegar al historial → conversaciones por mes → clicar y abrir en chat
