from __future__ import annotations

import mimetypes
import os
import tempfile

from nicegui import ui

from data.database import (
    create_conversation, add_message, get_messages,
    rename_conversation,
)
from services.gemini_service import stream_response
from ui.state import set_active_conversation

_SPARKLES   = '<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" style="color:var(--accent)"><path d="M12 2l1.6 4.4L18 8l-4.4 1.6L12 14l-1.6-4.4L6 8l4.4-1.6z"/><path d="M19 14l.8 2.2L22 17l-2.2.8L19 20l-.8-2.2L16 17l2.2-.8z"/></svg>'
_NEW_CHAT   = '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>'
_ATTACH     = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m21 12-9 9a5 5 0 0 1-7-7l9-9a3.5 3.5 0 1 1 5 5l-9 9a2 2 0 0 1-3-3l8-8"/></svg>'
_SCREENSHOT = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 8V5a1 1 0 0 1 1-1h3"/><path d="M20 8V5a1 1 0 0 0-1-1h-3"/><path d="M4 16v3a1 1 0 0 0 1 1h3"/><path d="M20 16v3a1 1 0 0 1-1 1h-3"/><rect x="8" y="9" width="8" height="6" rx="1"/></svg>'
_SEND       = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2 11 13"/><path d="M22 2l-7 20-4-9-9-4 20-7z"/></svg>'

# ID único para el input file de esta sesión
_FILE_INPUT_ID = "chat-file-input"


def chat_page(on_new_chat=None):
    state = {
        "conversation_id": None,
        "pending": [],
        "streaming": False,
        "total_tokens": 0,
    }

    # Input file nativo oculto
    ui.html(f'<input type="file" id="{_FILE_INPUT_ID}" accept="image/*,.pdf,.txt,.csv" style="display:none" multiple>')
    ui.add_body_html(f'''<script>
    (function(){{
      function _initFileInput(){{
        var inp = document.getElementById("{_FILE_INPUT_ID}");
        if(!inp) return;
        inp.addEventListener("change", function(){{
          var files = inp.files;
          for(var i=0;i<files.length;i++){{
            (function(f){{
              var reader = new FileReader();
              reader.onload = function(e){{
                emitEvent("chat_file_selected", {{
                  name: f.name,
                  mime: f.type || "application/octet-stream",
                  data: e.target.result
                }});
              }};
              reader.readAsDataURL(f);
            }})(files[i]);
          }}
          inp.value = "";
        }});
      }}
      if(document.readyState === "loading"){{
        document.addEventListener("DOMContentLoaded", _initFileInput);
      }} else {{
        _initFileInput();
      }}
    }})();
    </script>''')


    # ── Head ──────────────────────────────────────────────────────────────────
    with ui.element("div").classes("panel-head"):
        with ui.element("div"):
            with ui.element("h2"):
                ui.html(_SPARKLES)
                ui.label("AI Chat")
            with ui.element("div").classes("subtitle"):
                ui.label("Gemini · Chatea con la IA")
        with ui.element("div").style("display:flex;gap:6px;align-items:center;"):
            new_chat_btn = ui.element("span").classes("chip").style(
                "cursor:pointer;display:flex;align-items:center;gap:4px;"
            )
            with new_chat_btn:
                ui.html(_NEW_CHAT)
                ui.label("Nuevo")
            with ui.element("span").classes("chip on").style("cursor:default;"):
                token_lbl = ui.label("0 tk")

    # ── Body ──────────────────────────────────────────────────────────────────
    with ui.element("div").classes("panel-body"):
        chat_list = ui.element("div").classes("chat-list")

    # ── Foot ──────────────────────────────────────────────────────────────────
    with ui.element("div").classes("panel-foot"):
        attach_row = ui.element("div").style(
            "display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px;"
        )

        with ui.element("div").classes("composer"):

            # Botón adjuntar — dispara el input file nativo
            with ui.element("button").classes("iconbtn").style("width:28px;height:28px;") as attach_btn:
                ui.html(_ATTACH)
            attach_btn.on("click", lambda: ui.run_javascript(
                f'document.getElementById("{_FILE_INPUT_ID}").click();'
            ))

            # Input de texto
            txt = ui.input(placeholder="Pregunta cualquier cosa…").props("borderless dense").style(
                "flex:1;border:0;background:transparent;outline:none;"
                "font-size:13px;font-family:inherit;"
            )

            # Captura de pantalla
            def _screenshot():
                from services.region_selector import select_region

                def _on_region(path: str):
                    state["pending"].append({"path": path, "mime_type": "image/png", "name": "captura.png"})
                    _refresh_chips(state, attach_row)

                select_region(_on_region)

            with ui.element("button").classes("iconbtn").style("width:28px;height:28px;").on("click", _screenshot):
                ui.html(_SCREENSHOT)

            # Enviar
            with ui.element("button").classes("iconbtn primary").on(
                "click", lambda: ui.timer(0, lambda: _enviar(state, txt, chat_list, attach_row, send_btn, token_lbl), once=True)
            ) as send_btn:
                ui.html(_SEND)

        txt.on("keydown.enter", lambda: ui.timer(
            0, lambda: _enviar(state, txt, chat_list, attach_row, send_btn, token_lbl), once=True
        ))

    # Recibir archivos seleccionados desde el input file nativo
    def _on_file_selected(e):
        import base64
        data_url = e.args.get("data", "")
        name = e.args.get("name", "archivo")
        mime = e.args.get("mime", "application/octet-stream")

        # Decodificar base64 y guardar en temp
        if "," in data_url:
            b64 = data_url.split(",", 1)[1]
        else:
            b64 = data_url
        raw = base64.b64decode(b64)
        suffix = os.path.splitext(name)[1] or ".bin"
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        tmp.write(raw)
        tmp.close()

        state["pending"].append({"path": tmp.name, "mime_type": mime, "name": name})
        _refresh_chips(state, attach_row)

    ui.on("chat_file_selected", _on_file_selected)

    # ── Nuevo chat ────────────────────────────────────────────────────────────
    def _new_chat():
        if state["streaming"]:
            return
        state["conversation_id"] = None
        state["pending"] = []
        state["total_tokens"] = 0
        set_active_conversation(None)
        chat_list.clear()
        _refresh_chips(state, attach_row)
        txt.set_value("")
        token_lbl.set_text("0 tk")
        if on_new_chat:
            on_new_chat()

    new_chat_btn.on("click", _new_chat)

    # ── Cargar conversación existente ─────────────────────────────────────────
    def _load_conversation(conv_id: int):
        if state["streaming"]:
            return
        state["conversation_id"] = conv_id
        state["pending"] = []
        state["total_tokens"] = 0
        set_active_conversation(conv_id)
        chat_list.clear()
        _refresh_chips(state, attach_row)
        txt.set_value("")
        token_lbl.set_text("0 tk")
        messages = get_messages(conv_id)
        with chat_list:
            for msg in messages:
                if msg["role"] == "user":
                    with ui.element("div").classes("bubble user"):
                        ui.label(msg["content"])
                else:
                    with ui.element("div").classes("bubble ai"):
                        ui.html(_render_md(msg["content"]))
        _init_copy_buttons()
        _scroll_bottom()

    return _load_conversation


def _refresh_chips(state: dict, attach_row):
    attach_row.clear()
    for i, att in enumerate(state["pending"]):
        idx = i
        with attach_row:
            with ui.element("span").classes("attach-chip"):
                ui.label(f"📎 {att['name']}")
                with ui.element("button").style(
                    "background:none;border:none;cursor:pointer;padding:0 2px;"
                    "font-size:10px;color:var(--ink-soft);"
                ).on("click", lambda _i=idx: _remove_attach(state, _i, attach_row)):
                    ui.label("✕")


def _remove_attach(state: dict, idx: int, attach_row):
    if 0 <= idx < len(state["pending"]):
        state["pending"].pop(idx)
    _refresh_chips(state, attach_row)


async def _enviar(state: dict, txt_input, chat_list, attach_row, send_btn, token_lbl):
    texto = txt_input.value.strip()
    if not texto and not state["pending"]:
        return
    if state["streaming"]:
        return

    state["streaming"] = True
    send_btn.props(add="disabled")

    if state["conversation_id"] is None:
        conv_id = create_conversation()
        nombre = texto[:45] + "..." if len(texto) > 45 else texto
        rename_conversation(conv_id, nombre or "Archivo adjunto")
        state["conversation_id"] = conv_id
        set_active_conversation(conv_id)

    add_message(state["conversation_id"], "user", texto)

    with chat_list:
        with ui.element("div").classes("bubble user"):
            if state["pending"]:
                chips_html = " ".join(
                    f'<span class="attach-chip">📎 {a["name"]}</span>'
                    for a in state["pending"]
                )
                ui.html(chips_html)
            if texto:
                ui.label(texto)

    historial = get_messages(state["conversation_id"])
    if state["pending"] and historial:
        historial[-1] = dict(historial[-1])
        historial[-1]["attachments"] = list(state["pending"])

    txt_input.set_value("")
    state["pending"] = []
    _refresh_chips(state, attach_row)

    # Burbuja IA con typing indicator
    with chat_list:
        with ui.element("div").classes("bubble ai"):
            typing_dots = ui.element("div").classes("typing")
            with typing_dots:
                ui.element("span")
                ui.element("span")
                ui.element("span")
            ai_label = ui.html("").style("display:none;")

    _scroll_bottom()

    full_response = ""
    meta = {}
    try:
        async for chunk in stream_response(historial, meta=meta):
            if not full_response:
                typing_dots.set_visibility(False)
                ai_label.style("display:block;")
            full_response += chunk
            ai_label.set_content(_render_md(full_response))
            _scroll_bottom()
    except Exception as e:
        typing_dots.set_visibility(False)
        ai_label.style("display:block;")
        ai_label.set_content(f"<em>Error: {e}</em>")

    if full_response:
        add_message(state["conversation_id"], "assistant", full_response)

    if meta.get("total_tokens"):
        state["total_tokens"] += meta["total_tokens"]
        token_lbl.set_text(_fmt_tokens(state["total_tokens"]))

    state["streaming"] = False
    send_btn.props(remove="disabled")
    _init_copy_buttons()
    _scroll_bottom()


def _init_copy_buttons():
    ui.run_javascript('''
    (function() {
      var CHECK = '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';
      var COPY  = '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';
      document.querySelectorAll('.code-copy:not([data-init])').forEach(function(btn) {
        btn.setAttribute('data-init', '1');
        btn.addEventListener('click', function() {
          var code = btn.closest('.code-block').querySelector('code').textContent.replace(/\\n$/, '');
          navigator.clipboard.writeText(code).then(function() {
            btn.innerHTML = CHECK;
            btn.classList.add('copied');
            setTimeout(function() {
              btn.innerHTML = COPY;
              btn.classList.remove('copied');
            }, 1500);
          });
        });
      });
    })();
    ''')


def _scroll_bottom():
    ui.run_javascript(
        'var el=document.querySelector(".panel-body");if(el)el.scrollTop=el.scrollHeight;'
    )


def _fmt_tokens(n: int) -> str:
    if n >= 1000:
        return f"{n / 1000:.1f}k tk"
    return f"{n} tk"


def _render_md(text: str) -> str:
    import re

    # Bloques de código (```lang\n...\n```) — procesar antes que el resto
    _COPY_SVG = '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>'

    def _code_block(m):
        lang = m.group(1).strip()
        code = m.group(2)
        code_escaped = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        header = (
            f'<div class="code-header">'
            f'<span class="code-lang">{lang}</span>'
            f'<button class="code-copy">{_COPY_SVG}</button>'
            f'</div>'
        )
        return f'<div class="code-block">{header}<pre><code>{code_escaped}</code></pre></div>'

    text = re.sub(r"```(\w*)\n?(.*?)```", _code_block, text, flags=re.DOTALL)

    # Formato inline (no dentro de bloques ya procesados)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)

    # Listas numeradas
    text = re.sub(r"(?m)^\d+\.\s+(.+)$", r"<li>\1</li>", text)
    text = re.sub(r"(<li>.*?</li>)", r"<ol>\1</ol>", text, flags=re.DOTALL)

    # Saltos de línea (solo fuera de bloques de código)
    text = re.sub(r"(?<!<\/div>)\n", "<br>", text)

    return text
