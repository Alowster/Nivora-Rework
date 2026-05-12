# Plan: Migrar UI de PySide6 a NiceGUI con diseño Glass AI Palette

## Contexto

Se abandona la UI de PySide6 (ventana pill con QPainter, PopupPanel, widgets Qt) y se reemplaza por NiceGUI corriendo en modo nativo (`pywebview`). El aspecto visual viene íntegramente del diseño **Glass AI Palette.html**: variables CSS, clases glass, componentes adaptados a NiceGUI.

El diseño tiene 3 herramientas en una toolbar circular:
- **Chat** → `ChatPanel` actual (Gemini, streaming, adjuntos, capturas)
- **Log** → `HistoryPanel` actual (conversaciones por mes)
- **Macros** → `MacrosPanel` actual (CRUD de macros + hotkeys)

Referencias:
- Diseño visual: `design-reference/Glass AI Palette.html`
- Plan de migración base: `MIGRACION_NICEGUI.md`

---

## Decisión de arquitectura

NiceGUI permite inyectar CSS arbitrario con `ui.add_css()` y aplicar clases personalizadas con `.classes('nombre-clase')` en cualquier elemento. Se reutiliza el CSS del diseño sin modificarlo (salvo eliminar el fondo de demo).

**Sin fondo artificial**: se eliminan `.desktop` y `.orb` del diseño. La ventana difuminará lo que haya debajo (escritorio u otras apps) usando **Windows DWM Acrylic** a nivel de sistema operativo. El `<body>` será `background: transparent`.

**Transparencia real (Windows)**: tras arrancar pywebview se obtiene el HWND de la ventana y se aplica `SetWindowCompositionAttribute` con efecto Acrylic. Esto hace que el OS difumine el contenido real del escritorio detrás de la ventana.

**Siempre encima**: `on_top=True` en `ui.run()`.

**CSS `backdrop-filter`**: se elimina de todos los elementos. El blur lo gestiona íntegramente el OS (DWM Acrylic). Los elementos glass simplemente tienen fondos semi-transparentes (`rgba`) que dejan ver el blur del escritorio a través de ellos.

---

## Archivos a crear / modificar

```
main.py                     ← reescribir (NiceGUI en vez de PySide6)
ui/
  styles.css                ← CSS extraído de Glass AI Palette.html
  chat_page.py              ← página de chat con streaming + adjuntos
  history_page.py           ← historial de conversaciones
  macros_page.py            ← gestión de macros
  state.py                  ← estado compartido entre páginas
services/
  gemini_service.py         ← ya existe, sin cambios
  hotkey_manager.py         ← refactorizar (quitar QObject/Signal)
  region_selector.py        ← ya existe (Tkinter overlay)
data/
  database.py               ← sin cambios
config.py                   ← limpiar constantes Qt
```

---

## Paso 1 — Extraer el CSS del diseño

Copiar el bloque `<style>` de `Glass AI Palette.html` a `ui/styles.css` eliminando solo:
- `.desktop { ... }` — el fondo de demo ya no se necesita
- `.orb { ... }` y `.orb.a/.b/.c { ... }` — los orbes de color
- `@keyframes drift { ... }` — animación de los orbes

Todo lo demás queda intacto: variables CSS, toolbar, panel, burbujas, composer, macros, log, animaciones `pop` y `blink`.

Además, eliminar de `ui/styles.css` todas las líneas con `backdrop-filter` y `-webkit-backdrop-filter` — el blur lo hace DWM, no CSS.

Añadir al final de `ui/styles.css`:
```css
html, body {
    background: transparent !important;
    margin: 0;
    padding: 0;
}
```

En `main.py` se inyecta con:
```python
from pathlib import Path
ui.add_css(Path("ui/styles.css").read_text())
```

---

## Paso 2 — Transparencia real con Windows DWM Acrylic

Crear `services/windows_blur.py` que se llama una vez tras el arranque de pywebview:

```python
import ctypes
import ctypes.wintypes

class _ACCENTPOLICY(ctypes.Structure):
    _fields_ = [
        ('AccentState',   ctypes.c_uint),
        ('AccentFlags',   ctypes.c_uint),
        ('GradientColor', ctypes.c_uint),
        ('AnimationId',   ctypes.c_uint),
    ]

class _WINCOMPATTRDATA(ctypes.Structure):
    _fields_ = [
        ('Attribute',   ctypes.c_uint),
        ('Data',        ctypes.c_void_p),
        ('SizeOfData',  ctypes.c_size_t),
    ]

ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
WCA_ACCENT_POLICY = 19

def apply_acrylic(hwnd: int, tint_color: int = 0x00FFFFFF):
    """Aplica efecto Acrylic (blur de escritorio) a la ventana con el HWND dado."""
    accent = _ACCENTPOLICY()
    accent.AccentState   = ACCENT_ENABLE_ACRYLICBLURBEHIND
    accent.AccentFlags   = 2
    accent.GradientColor = tint_color  # AABBGGRR — 0x00FFFFFF = sin tinte

    data = _WINCOMPATTRDATA()
    data.Attribute   = WCA_ACCENT_POLICY
    data.Data        = ctypes.cast(ctypes.byref(accent), ctypes.c_void_p)
    data.SizeOfData  = ctypes.sizeof(accent)

    ctypes.windll.user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))
```

En `main.py`, tras el arranque de NiceGUI:
```python
import pywebview
from services.windows_blur import apply_acrylic

@app.on_startup
async def startup():
    init_db()
    hotkey_manager.reload()
    # Aplicar blur tras breve espera para que pywebview cree la ventana
    import asyncio, ctypes
    await asyncio.sleep(0.5)
    hwnd = ctypes.windll.user32.FindWindowW(None, "Nivora")
    if hwnd:
        apply_acrylic(hwnd)
```

---

## Paso 3 — Refactorizar `hotkey_manager.py` (quitar Qt)

```python
import keyboard
from data.database import get_all_macros
import subprocess

class HotkeyManager:
    def __init__(self, on_shell_macro):
        self._on_shell_macro = on_shell_macro
        self._handles = []

    def reload(self):
        for h in self._handles:
            keyboard.remove_hotkey(h)
        self._handles = []
        for macro in get_all_macros():
            if not macro["hotkey"]:
                continue
            if macro["type"] == "text":
                h = keyboard.add_hotkey(macro["hotkey"], lambda m=macro: keyboard.write(m["content"]))
            else:
                h = keyboard.add_hotkey(macro["hotkey"], lambda m=macro: self._on_shell_macro(m))
            self._handles.append(h)

    def shutdown(self):
        for h in self._handles:
            keyboard.remove_hotkey(h)
```

---

## Paso 4 — `main.py` con NiceGUI

```python
from nicegui import ui, app
from pathlib import Path
from data.database import init_db
from services.hotkey_manager import HotkeyManager
from ui.chat_page import chat_page
from ui.history_page import history_page
from ui.macros_page import macros_page

hotkey_manager = HotkeyManager(on_shell_macro=lambda m: None)

@app.on_startup
async def startup():
    import asyncio, ctypes
    from services.windows_blur import apply_acrylic
    init_db()
    hotkey_manager.reload()
    await asyncio.sleep(0.5)
    hwnd = ctypes.windll.user32.FindWindowW(None, "Nivora")
    if hwnd:
        apply_acrylic(hwnd)

@app.on_shutdown
async def shutdown():
    hotkey_manager.shutdown()

@ui.page('/')
def index():
    ui.add_css(Path("ui/styles.css").read_text())

    with ui.element('div').classes('widget-wrap'):
        _toolbar()
        with ui.element('div').classes('panel glass') as panel:
            chat_page()

ui.run(
    title='Nivora',
    dark=False,
    reload=False,
    native=True,
    on_top=True,
    window_size=(440, 560),
    storage_secret='cambiar_por_secreto_aleatorio',
)
```

---

## Paso 5 — `ui/state.py`

```python
from nicegui import app

def get_active_conversation():
    return app.storage.user.get("conversation_id")

def set_active_conversation(conv_id: int):
    app.storage.user["conversation_id"] = conv_id
```

---

## Paso 6 — Toolbar interactiva

La toolbar del diseño usa las clases `.toolbar.glass`, `.tbtn`, `.tbtn.active`, `.tbtn-square`.

En NiceGUI:
- Estructura con `ui.element('div').classes('toolbar glass')`
- Botones con `ui.element('button').classes('tbtn')` + iconos SVG inline
- Estado activo: `element.classes(add='active', remove='')` / `element.classes(remove='active')`
- Menú: `ui.element('div').classes('menu glass')` con visibilidad toggle
- Minimizar: ocultar el panel con `.set_visibility(False)` + reducir ventana
- Siempre encima: gestionado por `on_top=True` en `ui.run()`
- El blur de fondo lo hace DWM — los fondos `rgba()` de toolbar y panel simplemente dejan pasar el blur del OS

**Drag de ventana** desde la toolbar via JavaScript inyectado:
```javascript
let drag = false, ox = 0, oy = 0;
document.querySelector('.toolbar').addEventListener('mousedown', e => {
    drag = true; ox = e.screenX - window.screenX; oy = e.screenY - window.screenY;
});
document.addEventListener('mousemove', e => { if(drag) window.moveTo(e.screenX - ox, e.screenY - oy); });
document.addEventListener('mouseup', () => drag = false);
```

---

## Paso 7 — `ui/chat_page.py`

Estructura visual del `ChatPanel` del diseño:

```
.panel-head   → icono + "AI Chat" + chip modelo
.panel-body   → .chat-list con .bubble.ai / .bubble.user
.panel-foot   → .composer
                  botón 📎 .iconbtn   → adjuntar archivo
                  input texto
                  botón captura .iconbtn → region_selector → PNG a Gemini
                  botón enviar .iconbtn.primary → stream_response
```

- Burbujas añadidas dinámicamente con `ui.html(f'<div class="bubble user">...</div>')`
- Streaming: `async for chunk in stream_response(messages)` + actualización directa de un `ui.html` element
- Adjuntos pendientes: chips `.chip` sobre el composer antes de enviar
- Captura: `select_region(callback)` → PNG en `/tmp` → adjunto
- Archivo: `ui.upload()` → guardado en `/tmp` → adjunto
- El panel no se cierra al abrir el file dialog (pywebview usa ventana nativa, no `Qt.Popup`)

Reutiliza: `data/database.py`, `services/gemini_service.py`, `services/region_selector.py`, `ui/state.py`

---

## Paso 8 — `ui/history_page.py`

Mapea al panel **Log** del diseño:

```
.panel-head   → "Historial" + chips de mes (.chip / .chip.on)
.panel-body   → conversaciones como .log-row clicables
                  .log-pill → mes abreviado
                  .log-text → nombre de conversación
                  .log-time → fecha
```

Al clicar: `set_active_conversation(id)` y navegar al chat cargando la conversación.

Reutiliza: `data/database.get_all_conversations()`, `ui/state.py`

---

## Paso 9 — `ui/macros_page.py`

Usa `.macro-card`, `.macro-icon`, `.toggle`, `.run-btn` del diseño:

```
.panel-head   → "Macros" + botón "+ Nueva"
.panel-body   → por cada macro: .macro-card
                  .macro-icon  → icono ⚡
                  .macro-info  → nombre + .kbd (hotkey) + descripción
                  .run-btn     → ejecutar (macros tipo shell)
                  .toggle      → activar/desactivar hotkey
```

Al guardar/eliminar: `hotkey_manager.reload()`.

Reutiliza: `data/database` (CRUD macros)

---

## Paso 10 — Limpiar código PySide6

Eliminar tras verificar que NiceGUI funciona:
- `ui/widgets/` completo
- `ui/panels/` completo
- `services/gemini_thread.py`
- `services/ai_service.py`
- `services/ocr_service.py`
- `services/ollama_manager.py`
- `assets/icons.py`, `assets/styles.qss`
- Dependencias: `PySide6`, `markdown`, `ollama`, `rapidocr-onnxruntime`

---

## Orden de trabajo recomendado

1. Extraer CSS a `ui/styles.css` (sin desktop/orbs, con `body { background: transparent }`)
2. Crear `services/windows_blur.py` y probar que aplica el blur al escritorio
3. Montar `main.py` con toolbar vacía → verificar ventana nativa, siempre encima y blur real
4. Refactorizar `hotkey_manager.py` (quitar Qt)
5. Implementar drag desde toolbar
6. Implementar `ui/chat_page.py` — texto simple → streaming → adjuntos
7. Implementar `ui/history_page.py`
8. Implementar `ui/macros_page.py`
9. Conectar `hotkey_manager` con macros_page
10. Limpiar archivos PySide6

---

## Verificación

- `python main.py` → ventana nativa sin bordes, siempre encima, difuminando escritorio/apps debajo
- Mover ventana desde toolbar → se desplaza correctamente
- Cambiar entre Chat / Historial / Macros → swap con animación `pop`
- Enviar mensaje → burbujas `.bubble.user` y `.bubble.ai`, streaming visible token a token
- Adjuntar imagen o PDF → chip en composer, enviado a Gemini
- Captura de pantalla → overlay Tkinter, PNG enviado a Gemini
- Historial → conversaciones en formato `.log-row`, clicables
- Macros → cards con toggle y run, hotkeys activos fuera de la ventana
- Menú → minimiza a toolbar, cierra la app
