# Plan: Ampliar ventana de Ajustes

## Contexto
La ventana de ajustes actual solo tiene dos sliders (opacidad y tamaño UI). El usuario quiere añadir 7 opciones nuevas organizadas en secciones, cubrir persistencia entre sesiones y conectar todo con la lógica existente de IslandWindow, GeminiThread y HotkeyManager.

---

## Opciones a añadir

| Opción | Control | Sección |
|---|---|---|
| Posición de la píldora | 3 botones L/C/R | Posición |
| Always on top | Toggle | Comportamiento |
| Auto-ocultar por inactividad | Toggle + slider tiempo (5-120 s) | Comportamiento |
| Arrancar minimizado | Toggle | Comportamiento |
| Modelo de Gemini | QComboBox | IA |
| System prompt | QTextEdit (3 líneas) | IA |
| Hotkey global mostrar/ocultar | Campo captura de teclas | Hotkey |

---

## Archivos a modificar

| Archivo | Cambios |
|---|---|
| `ui/widgets/settings_window.py` | Rediseño completo: scroll area, secciones, nuevos controles y señales |
| `ui/widgets/island_bar.py` | Conectar nuevas señales; `_apply_position`, `_apply_always_on_top`, `_apply_auto_hide`, `_apply_model`, `_apply_system_prompt`, `_apply_show_hide_hotkey` |
| `services/gemini_thread.py` | Añadir parámetro `system_prompt` en `__init__` y anteponer al historial |
| `services/hotkey_manager.py` | Añadir `register_show_hide(hotkey_str, callback)` y `unregister_show_hide()` |
| `main.py` | Leer `start_minimized` de QSettings al arrancar; no llamar `window.show()` si está activo |
| `config.py` | Añadir `GEMINI_MODELS` (lista de modelos disponibles) |

---

## Persistencia

Usar **QSettings** (`QSettings("Nivora", "NivoraApp")`) para guardar y restaurar:
- `opacity` (float)
- `scale` (float)
- `position` ("left"/"center"/"right")
- `always_on_top` (bool)
- `auto_hide` (bool)
- `auto_hide_delay` (int, segundos)
- `start_minimized` (bool)
- `gemini_model` (str)
- `system_prompt` (str)
- `show_hide_hotkey` (str)

Cargar en `SettingsWindow.__init__` para inicializar los controles con los valores guardados. Guardar cada vez que cambia un control.

---

## Diseño visual de SettingsWindow

- Tamaño: `260 × 520` (fijo)
- Interior: `QScrollArea` sin borde para que quepa todo
- Secciones separadas por `QLabel` con clase `.SectionLabel` + `QFrame` con clase `.HSeparator`
- Bordes redondeados: radio 20 (igual que ahora)

```
─ APARIENCIA ─────────────────
Opacidad de la ventana   ━━●── 100%
Tamaño de la interfaz    ──●── 100%

─ POSICIÓN ───────────────────
[ Izquierda ] [ Centro ] [ Derecha ]

─ COMPORTAMIENTO ─────────────
Siempre visible          [ ON ]
Auto-ocultar             [ OFF ]
  Tiempo (seg)      ──●── 30s
Arrancar minimizado      [ OFF ]

─ MODELO IA ──────────────────
▼ gemini-2.0-flash-lite

─ SYSTEM PROMPT ──────────────
┌─────────────────────────────┐
│ Eres un asistente...        │
└─────────────────────────────┘

─ HOTKEY GLOBAL ──────────────
Mostrar / ocultar pill
[ Ctrl+Alt+Space             ]
```

---

## Señales nuevas de SettingsWindow

```python
position_changed        = Signal(str)   # "left"/"center"/"right"
always_on_top_changed   = Signal(bool)
auto_hide_changed       = Signal(bool)
auto_hide_delay_changed = Signal(int)   # segundos
start_minimized_changed = Signal(bool)
model_changed           = Signal(str)
system_prompt_changed   = Signal(str)
show_hide_hotkey_changed = Signal(str)
```

---

## Detalles de implementación

### Posición de la píldora
- Tres `QPushButton` checkable en `QButtonGroup` (exclusivos)
- En `IslandWindow._apply_position(pos)`:
  - `"left"` → `x = 20`
  - `"center"` → `x = (screen_w - window_w) // 2` (comportamiento actual)
  - `"right"` → `x = screen_w - window_w - 20`
  - Llama `self.move(x, config.WINDOW_TOP_MARGIN)`

### Always on top
- En `IslandWindow._apply_always_on_top(value)`:
  - Añadir/quitar `Qt.WindowStaysOnTopHint` con `setWindowFlags()`
  - Llamar `self.show()` tras cambiar flags (necesario para que surta efecto)

### Auto-ocultar
- `QTimer` en `IslandWindow` con timeout → `self.hide()`
- Reset del timer en `mouseMoveEvent`, `mousePressEvent`, y al abrir el popup
- El slider en settings controla el delay (5–120 s)
- Si el toggle está OFF, el timer no se activa

### Arrancar minimizado
- Solo persiste en QSettings
- En `main.py`: `if settings.value("start_minimized", False, bool): pass` (no llamar `window.show()`)
- El tray icon ya está siempre activo, el usuario puede recuperar la pill desde ahí

### Selector de modelo Gemini
- `config.GEMINI_MODELS = ["models/gemini-2.0-flash-lite", "models/gemini-2.0-flash", "models/gemini-1.5-pro"]`
- `QComboBox` en settings
- Al cambiar → `config.GEMINI_MODEL = nuevo_modelo`; el próximo `GeminiThread` usará el nuevo valor (ya lee `config.GEMINI_MODEL` en `run()`)

### System prompt
- `QTextEdit` de 3 líneas con clase `.GlassTextEdit`
- Al perder foco o tras 500 ms sin escribir → emite señal
- En `IslandWindow`: guarda en `self._system_prompt`
- En `ChatPanel.send_message()`: pasar `system_prompt` al construir `GeminiThread`
- En `GeminiThread.__init__`: aceptar `system_prompt=""` y usar el campo `system_instruction` de la API de Gemini

### Hotkey global mostrar/ocultar
- Campo `QLineEdit` de solo lectura que captura teclas al hacer click
- Click activa modo captura → `keyPressEvent` acumula teclas → Enter confirma
- Misma lógica que los HotkeyBadge de macros (reusar patrón de `MacrosPanel`)
- En `HotkeyManager.register_show_hide(hotkey_str, callback)`: usa `keyboard.add_hotkey()`
- `unregister_show_hide()`: llama `keyboard.remove_hotkey()` sobre el anterior
- El callback hace `window.show()` si está oculta, `window.hide()` si está visible

---

## Reutilización de código existente

- Clases QSS ya existentes: `.ToggleButton`, `.HotkeyBadge`, `.HotkeyBadge--empty`, `.GlassTextEdit`, `.SectionLabel`, `.HSeparator` → usar sin cambios en `styles.qss`
- `SettingsSlider` (QSS de sesión anterior) → reusar para el slider de tiempo de auto-ocultar
- `SettingsDesc` / `SettingsValue` → reusar para las etiquetas de los nuevos sliders
- Patrón de captura de hotkeys de `MacrosPanel` → replicar en el campo hotkey global

---

## Verificación

1. Lanzar app → ajustes abre a la derecha de la pill
2. Mover slider opacidad → las 3 ventanas cambian a la vez
3. Cambiar posición → pill se mueve al lado seleccionado
4. Activar "always on top" → desactivar, verificar que otras ventanas la tapan
5. Activar auto-ocultar 5 s → esperar → pill desaparece; mover ratón sobre pill → timer reinicia
6. Activar "arrancar minimizado" → cerrar y relanzar → pill no aparece pero sí el tray
7. Cambiar modelo → enviar mensaje → verificar el modelo usado en logs
8. Escribir system prompt → enviar mensaje → la IA responde siguiendo las instrucciones
9. Capturar hotkey Ctrl+Alt+Space → pulsar fuera de la app → pill aparece/desaparece