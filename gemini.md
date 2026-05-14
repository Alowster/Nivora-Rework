# Gemini en Nivora — Referencia de implementación para PySide6

Documenta todas las funcionalidades del chat IA y del historial tal como están implementadas
en la rama `revision-punto-anterior`, para replicarlas en la rama `test` usando PySide6 +
Gemini en lugar de Ollama.

---

## 1. Librería y modelo

**Paquete**: `google-genai` (no `google.generativeai`)

```
pip install google-genai python-dotenv pillow
```

**Imports**:
```python
from google.genai import Client
from google.genai import types
```

**Modelo** en `config.py`:
```python
GEMINI_MODEL = "models/gemini-3.1-flash-lite"
```

**API key** en `.env` (raíz del proyecto, nunca al repo):
```
GEMINI_API_KEY=tu_key_aqui
```

---

## 2. `services/gemini_service.py`

Único archivo de integración con la API. Expone `stream_response`.

```python
import asyncio
import os
from pathlib import Path
from typing import AsyncGenerator

from dotenv import load_dotenv
from google.genai import Client
from google.genai import types

from config import GEMINI_MODEL

load_dotenv()


def _get_client() -> Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Falta GEMINI_API_KEY en el archivo .env")
    return Client(api_key=api_key)


def _build_contents(messages: list) -> list[types.Content]:
    """Convierte [{role, content, attachments?}] al formato Gemini."""
    contents = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        parts = []

        if m.get("content"):
            parts.append(types.Part.from_text(text=m["content"]))

        for att in m.get("attachments", []):
            mime = att.get("mime_type", "image/png")
            raw = Path(att["path"]).read_bytes()
            parts.append(types.Part.from_bytes(data=raw, mime_type=mime))

        if parts:
            contents.append(types.Content(role=role, parts=parts))

    return contents


def _sync_stream(client: Client, contents: list) -> tuple[list[str], int]:
    chunks = []
    last_chunk = None
    for chunk in client.models.generate_content_stream(
        model=GEMINI_MODEL,
        contents=contents,
    ):
        if chunk.text:
            chunks.append(chunk.text)
        last_chunk = chunk

    total_tokens = 0
    if last_chunk and getattr(last_chunk, "usage_metadata", None):
        total_tokens = getattr(last_chunk.usage_metadata, "total_token_count", 0) or 0

    return chunks, total_tokens


async def stream_response(messages: list, meta: dict | None = None) -> AsyncGenerator[str, None]:
    client = _get_client()
    contents = _build_contents(messages)
    chunks, total_tokens = await asyncio.to_thread(_sync_stream, client, contents)
    if meta is not None:
        meta["total_tokens"] = total_tokens
    for chunk in chunks:
        yield chunk
```

### Notas técnicas críticas

- `generate_content_stream()` es **síncrono** en `google.genai`. Se envuelve en
  `asyncio.to_thread()` para no bloquear el hilo principal.
- Los adjuntos se pasan como **bytes crudos** con `types.Part.from_bytes(data=raw, mime_type=mime)`.
  No se usa base64 en los mensajes internos — solo si el transporte lo requiere (ver sección 5).
- El rol de la IA en la DB es `"assistant"`. `_build_contents` lo convierte a `"model"` para
  la API. El rol `"user"` no cambia.
- Si `parts` queda vacío (mensaje sin texto ni adjuntos), ese `Content` **no se añade**.
- `meta["total_tokens"]` acumula el total de la llamada. Puede ser 0 si la API no lo devuelve.

### Uso desde PySide6 con QThread

Para llamar a Gemini desde un `QThread` (sin asyncio), usar `_sync_stream` directamente:

```python
# services/gemini_thread.py
import os
from pathlib import Path
from dotenv import load_dotenv
from google.genai import Client, types
from PySide6.QtCore import QThread, Signal
from config import GEMINI_MODEL

load_dotenv()

class GeminiThread(QThread):
    chunk_received = Signal(str)
    completed = Signal()
    error = Signal(str)

    def __init__(self, messages: list):
        super().__init__()
        self.messages = messages
        self._stop_requested = False

    def run(self):
        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                self.error.emit("Falta GEMINI_API_KEY en el archivo .env")
                return
            client = Client(api_key=api_key)
            contents = self._build_contents()
            for chunk in client.models.generate_content_stream(
                model=GEMINI_MODEL,
                contents=contents,
            ):
                if self._stop_requested:
                    break
                if chunk.text:
                    self.chunk_received.emit(chunk.text)
            if not self._stop_requested:
                self.completed.emit()
        except Exception as e:
            if not self._stop_requested:
                self.error.emit(str(e))

    def _build_contents(self) -> list[types.Content]:
        contents = []
        for m in self.messages:
            role = "user" if m["role"] == "user" else "model"
            parts = []
            if m.get("content"):
                parts.append(types.Part.from_text(text=m["content"]))
            for att in m.get("attachments", []):
                raw = Path(att["path"]).read_bytes()
                parts.append(types.Part.from_bytes(data=raw, mime_type=att.get("mime_type", "image/png")))
            if parts:
                contents.append(types.Content(role=role, parts=parts))
        return contents

    def stop(self):
        self._stop_requested = True
```

**En PySide6, `GeminiThread` reemplaza directamente a `AIService`** — mismas señales
(`chunk_received`, `completed`, `error`), mismo patrón `worker.start()` / `worker.stop()`.

---

## 3. Formato de mensajes

El historial que se pasa a `stream_response` o a `GeminiThread`:

```python
# Texto solo
{"role": "user", "content": "¿Qué es Python?"}

# Respuesta guardada en DB (role='assistant' → se convierte a 'model' internamente)
{"role": "assistant", "content": "Python es un lenguaje..."}

# Con imagen adjunta (captura de pantalla o archivo subido)
{
    "role": "user",
    "content": "¿Qué muestra esta imagen?",
    "attachments": [
        {"path": "/tmp/captura.png", "mime_type": "image/png", "name": "captura.png"}
    ]
}

# Con PDF
{
    "role": "user",
    "content": "Resume este documento.",
    "attachments": [
        {"path": "/tmp/doc.pdf", "mime_type": "application/pdf", "name": "informe.pdf"}
    ]
}

# Solo adjunto sin texto (válido)
{
    "role": "user",
    "content": "",
    "attachments": [{"path": "/tmp/img.png", "mime_type": "image/png", "name": "img.png"}]
}
```

El campo `"name"` es solo para mostrar en la UI (chip), no lo usa Gemini.

---

## 4. Funcionalidades del chat IA

### 4.1 Estado local del panel de chat

El panel mantiene este estado en memoria (no en DB):

```python
state = {
    "conversation_id": None,   # int o None si es chat nuevo
    "pending": [],             # lista de adjuntos pendientes de enviar
    "streaming": False,        # True mientras Gemini está respondiendo
    "total_tokens": 0,         # tokens acumulados en esta sesión de chat
}
```

### 4.2 Enviar mensaje

**Flujo completo al pulsar Enviar o Enter:**

1. Leer texto del input. Si está vacío Y no hay `pending`, no hacer nada.
2. Si `streaming == True`, ignorar (no se puede enviar mientras responde).
3. Si `conversation_id is None`: crear conversación nueva con `create_conversation()`,
   renombrarla con los primeros 45 caracteres del texto (o `"Archivo adjunto"` si solo hay fichero).
4. Guardar el mensaje en DB: `add_message(conv_id, "user", texto)`.
5. Mostrar burbuja de usuario en la UI (con chips de adjuntos si los hay).
6. Cargar historial completo: `get_messages(conv_id)`.
7. Si hay adjuntos pendientes (`state["pending"]`), añadirlos al **último mensaje** del historial
   antes de enviarlo a Gemini:
   ```python
   historial[-1] = dict(historial[-1])
   historial[-1]["attachments"] = list(state["pending"])
   ```
8. Limpiar el input y `state["pending"]`.
9. Mostrar indicador de "escribiendo..." (typing dots) en la burbuja de la IA.
10. Llamar a Gemini en streaming. Por cada chunk: ocultar typing dots (solo la primera vez),
    acumular texto, actualizar la burbuja de la IA.
11. Al terminar: guardar respuesta con `add_message(conv_id, "assistant", full_response)`.
12. Actualizar contador de tokens con `meta["total_tokens"]`.
13. Poner `streaming = False`, rehabilitar el botón de enviar.

### 4.3 Nuevo chat

- Solo actúa si `streaming == False`.
- Pone `conversation_id = None`, vacía `pending`, resetea `total_tokens`.
- Limpia todas las burbujas del área de chat.
- Llama al callback `on_new_chat()` si existe (para refrescar el historial).

### 4.4 Cargar conversación existente

Se llama desde el panel de historial al hacer clic en una conversación:

1. Si `streaming == True`, ignorar.
2. Poner `conversation_id = conv_id`, vaciar `pending`.
3. Limpiar burbujas actuales.
4. Cargar mensajes con `get_messages(conv_id)`.
5. Renderizar cada mensaje: burbujas de usuario a la derecha, burbujas de IA a la izquierda
   con markdown renderizado.

### 4.5 Detener generación

- Llamar a `worker.stop()` (en `GeminiThread`, pone `_stop_requested = True`).
- Guardar lo que haya llegado hasta ese momento con `add_message`.
- Rehabilitar el input y el botón de enviar.

---

## 5. Adjuntos — cómo se gestionan

### 5.1 Lista de adjuntos pendientes

`state["pending"]` es una lista de dicts:
```python
{"path": "/tmp/archivo.png", "mime_type": "image/png", "name": "archivo.png"}
```

Se muestra como chips en la UI (nombre + botón ✕ para quitar). Al enviar, se vacía.

### 5.2 Subir archivo desde disco

El usuario selecciona un archivo (imágenes, PDF, txt, csv). El flujo:

1. Abrir un diálogo de archivo (en PySide6: `QFileDialog.getOpenFileName()`).
2. Leer el archivo y guardarlo en un temporal si ya está en disco, o usar la ruta directa.
3. Detectar el MIME type:
   ```python
   import mimetypes
   mime, _ = mimetypes.guess_type(ruta)
   mime = mime or "application/octet-stream"
   ```
4. Añadir a `state["pending"]`:
   ```python
   state["pending"].append({
       "path": ruta,
       "mime_type": mime,
       "name": os.path.basename(ruta)
   })
   ```
5. Refrescar los chips en la UI.

En `revision-punto-anterior` (NiceGUI), el archivo llega como base64 desde el navegador,
se decodifica y se guarda en un temporal. En PySide6, se usa directamente la ruta del
archivo en disco — no hace falta base64.

### 5.3 Captura de pantalla (selector de región)

**`services/region_selector.py`** — el callback recibe la **ruta del PNG** ya guardado,
no las coordenadas:

```python
import threading
import tempfile
import tkinter as tk
from PIL import ImageGrab


def select_region(callback):
    """
    Overlay fullscreen para seleccionar una región con el ratón.
    Llama a callback(path: str) con la ruta del PNG capturado al soltar.
    """
    def _run():
        root = tk.Tk()
        root.attributes("-fullscreen", True)
        root.attributes("-alpha", 0.25)
        root.attributes("-topmost", True)
        root.configure(bg="black")
        root.update_idletasks()

        canvas = tk.Canvas(root, cursor="crosshair", bg="black", highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        start = {}
        rect_id = [None]

        def on_press(e):
            start["x"], start["y"] = e.x_root, e.y_root

        def on_drag(e):
            if rect_id[0]:
                canvas.delete(rect_id[0])
            x0 = start["x"] - root.winfo_rootx()
            y0 = start["y"] - root.winfo_rooty()
            x1 = e.x - root.winfo_rootx()
            y1 = e.y - root.winfo_rooty()
            rect_id[0] = canvas.create_rectangle(x0, y0, x1, y1, outline="white", width=2)

        def on_release(e):
            x1 = min(start["x"], e.x_root)
            y1 = min(start["y"], e.y_root)
            x2 = max(start["x"], e.x_root)
            y2 = max(start["y"], e.y_root)
            root.destroy()
            if x2 - x1 < 5 or y2 - y1 < 5:
                return
            img = ImageGrab.grab(bbox=(x1, y1, x2, y2), all_screens=True)
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            img.save(tmp.name)
            tmp.close()
            callback(tmp.name)

        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)
        root.bind("<Escape>", lambda e: root.destroy())
        root.mainloop()

    threading.Thread(target=_run, daemon=True).start()
```

**Integración en PySide6** (`ChatPanel`):

```python
def iniciar_captura(self):
    self.window().hide()  # ocultar ventana para que no salga en la captura
    from services.region_selector import select_region
    select_region(self._on_region_captured)

def _on_region_captured(self, path: str):
    self.window().show()
    self.state["pending"].append({
        "path": path,
        "mime_type": "image/png",
        "name": "captura.png"
    })
    self._refresh_chips()
```

Diferencia con el código actual en `test`: el `OcrService` ya no se usa. La imagen va
directamente a Gemini, que extrae texto e interpreta la imagen en el mismo paso.

---

## 6. Renderizado de markdown

La respuesta de Gemini llega en Markdown. Hay que convertirla a HTML para mostrarla
en un `QTextEdit` o `QLabel` con `setHtml()`.

La función `_render_md` de `revision-punto-anterior` hace una conversión manual con regex
porque NiceGUI trabaja con HTML. En PySide6, se puede usar la librería `markdown`:

```python
import markdown as md

def render_md(text: str) -> str:
    html = md.markdown(text, extensions=["fenced_code", "tables"])
    return f'<div style="color:white;">{html}</div>'
```

O replicar la función manual si se quiere el mismo comportamiento:

```python
import re

def _render_md(text: str) -> str:
    _COPY_SVG = '...'  # icono SVG de copiar

    def _code_block(m):
        lang = m.group(1).strip()
        code = m.group(2).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return (
            f'<div class="code-block">'
            f'<div class="code-header"><span>{lang}</span><button class="code-copy">{_COPY_SVG}</button></div>'
            f'<pre><code>{code}</code></pre></div>'
        )

    text = re.sub(r"```(\w*)\n?(.*?)```", _code_block, text, flags=re.DOTALL)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*",     r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+)`",     r"<code>\1</code>", text)
    text = re.sub(r"(?m)^\d+\.\s+(.+)$", r"<li>\1</li>", text)
    text = re.sub(r"(<li>.*?</li>)", r"<ol>\1</ol>", text, flags=re.DOTALL)
    text = re.sub(r"(?<!<\/div>)\n", "<br>", text)
    return text
```

---

## 7. Contador de tokens

Cada llamada a `stream_response` puede devolver el total de tokens en `meta["total_tokens"]`.
El panel acumula los tokens de la sesión actual:

```python
meta = {}
# ... llamada a Gemini ...
state["total_tokens"] += meta.get("total_tokens", 0)
# Mostrar: "1.2k tk" o "800 tk"
```

El contador se resetea al crear un nuevo chat o cargar una conversación del historial.

---

## 8. Funcionalidades del historial (AI Log)

### 8.1 Lista de conversaciones

- Fuente de datos: `data.database.get_all_conversations()` → lista de dicts
  `{id, name, created_at}` ordenada por `created_at DESC`.
- Cada fila muestra: nombre de la conversación, fecha (`dd/mm`), chip de mes (`ENE`, `FEB`...).

### 8.2 Filtro por mes

- Se extraen los meses únicos del campo `created_at` (formato `YYYY-MM`).
- Chips clicables: "Todo" + uno por mes. Solo uno activo a la vez.
- Al seleccionar un mes, se filtran las conversaciones localmente (sin nueva query a DB,
  se llama `get_all_conversations()` y se filtra en memoria).

### 8.3 Búsqueda por texto

- Campo de búsqueda que filtra por `conv["name"].lower()`.
- Se combina con el filtro de mes (ambos activos al mismo tiempo).
- El contador de conversaciones del header se actualiza con cada filtro.

### 8.4 Abrir conversación

- Clic en una fila → llama a `on_open_chat(conv_id)`.
- Ese callback (definido en `main.py`) cambia al panel de chat y llama a
  `_load_conversation(conv_id)`.

### 8.5 Eliminar conversación

- Botón de papelera en cada fila → `delete_conversation(conv_id)` → refresca la lista.
- No hay confirmación previa (elimina directo).

### 8.6 Refresco de la lista

La función `history_page` devuelve una función `_rebuild` (llamada `refresh_history` en
`main.py`). Se pasa como `on_new_chat` al panel de chat para que al crear un nuevo chat
se actualice el historial automáticamente.

---

## 9. Lo que se elimina de la rama `test`

| Archivo | Reemplazado por |
|---|---|
| `services/ai_service.py` | `services/gemini_thread.py` |
| `services/ollama_manager.py` | Nada (Gemini es API externa) |
| `services/ocr_service.py` | Nada (Gemini interpreta la imagen directamente) |

En `config.py`: eliminar `OLLAMA_MODEL` y `OLLAMA_MAX_TOKENS`, añadir `GEMINI_MODEL`.

En `main.py`: eliminar `ensure_ollama_running()` y `kill_ollama()`.

En `ui/panels/chat_panel.py`:
- `AIService` → `GeminiThread` (mismas señales, mismo patrón)
- El flujo de captura de pantalla: ya no llama a `OcrService`. Llama a `select_region()`
  y añade el PNG a `state["pending"]`. La imagen va directa a Gemini.
- El historial que se pasa a `GeminiThread` ya lleva el adjunto en el último mensaje
  (ver sección 4.2, paso 7).

---

## 10. Flujo completo de una captura de pantalla → Gemini

```
Usuario pulsa botón cámara
  → ChatPanel.iniciar_captura()
  → window().hide()
  → select_region(callback)          # abre overlay Tkinter en hilo separado
      → usuario dibuja rectángulo
      → on_release: ImageGrab.grab() → guarda PNG en tempfile → callback(path)
  → _on_region_captured(path)
  → window().show()
  → state["pending"].append({path, mime_type:"image/png", name:"captura.png"})
  → _refresh_chips()                 # muestra chip "📎 captura.png" en la UI

Usuario escribe texto (opcional) y pulsa Enviar
  → enviar_mensaje()
  → historial = get_messages(conv_id)
  → historial[-1]["attachments"] = state["pending"]
  → GeminiThread(historial).start()
      → _build_contents(): lee bytes del PNG → types.Part.from_bytes(data=raw, mime_type="image/png")
      → client.models.generate_content_stream(...)
      → Gemini recibe imagen + texto → responde describiendo / extrayendo texto
  → chunks llegan vía chunk_received Signal → se muestran en la burbuja IA
```