from pathlib import Path

from nicegui import app, ui

from data.database import init_db
from services.hotkey_manager import HotkeyManager
from ui.chat_page import chat_page
from ui.history_page import history_page
from ui.macros_page import macros_page

hotkey_manager = HotkeyManager()

# ── SVG Icons ─────────────────────────────────────────────────────────────────

_I_CHAT  = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/></svg>'
_I_LOG   = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5h16M4 10h16M4 15h10M4 20h7"/></svg>'
_I_MACRO = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M13 3 5 13h6l-1 8 8-10h-6l1-8z"/></svg>'
_I_MENU  = '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><circle cx="5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="19" cy="12" r="1.6"/></svg>'
_I_MIN   = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M5 18h14"/></svg>'
_I_PIN   = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 17v5M8 3h8l-1 5 3 4H6l3-4-1-5z"/></svg>'
_I_COG   = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.8.3l-.1-.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3h0a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8v0a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg>'
_I_CLOSE = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>'
_I_SPARK = '<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" style="color:var(--accent)"><path d="M12 2l1.6 4.4L18 8l-4.4 1.6L12 14l-1.6-4.4L6 8l4.4-1.6z"/></svg>'


# ── Lifecycle ─────────────────────────────────────────────────────────────────

@app.on_startup
async def _startup():
    init_db()
    hotkey_manager.reload()


@app.on_shutdown
async def _shutdown():
    hotkey_manager.shutdown()


# ── Página ────────────────────────────────────────────────────────────────────

@ui.page("/")
def index():
    ui.add_css(Path("ui/styles.css").read_text(encoding="utf-8"))

    # Drag de ventana (sólo funciona en modo native)
    ui.add_body_html("""
    <script>
    document.addEventListener('DOMContentLoaded', function(){
      var drag=false, ox=0, oy=0;
      var tb = document.querySelector('.toolbar');
      if(!tb) return;
      tb.addEventListener('mousedown', function(e){
        if(e.target.closest('button, .tbtn')) return;
        drag=true; ox=e.screenX-window.screenX; oy=e.screenY-window.screenY;
        e.preventDefault();
      });
      document.addEventListener('mousemove',function(e){ if(drag) window.moveTo(e.screenX-ox,e.screenY-oy); });
      document.addEventListener('mouseup',function(){ drag=false; });
    });
    </script>
    """)

    app_state = {"panel": "chat", "win": "open", "menu_open": False}

    # ── Reopen pill (visible cuando está cerrado) ──────────────────────────────
    reopen_el = ui.element("div").classes("reopen glass").style("display:none;cursor:pointer;")
    with reopen_el:
        ui.html(_I_SPARK)
        ui.label("Abrir AI Palette")

    # ── Widget wrap ───────────────────────────────────────────────────────────
    widget_el = ui.element("div").classes("widget-wrap")

    with widget_el:

        # Wrapper relativo para el menú dropdown
        with ui.element("div").style("position:relative;align-self:center;"):

            # ── Toolbar ───────────────────────────────────────────────────────
            with ui.element("div").classes("toolbar glass"):

                btn_chat  = ui.element("button").classes("tbtn active").tooltip("AI Chat")
                with btn_chat:  ui.html(_I_CHAT)

                btn_log   = ui.element("button").classes("tbtn").tooltip("AI Log")
                with btn_log:
                    ui.html(_I_LOG)
                    # Dot de notificación
                    ui.element("span").classes("dot")

                btn_macro = ui.element("button").classes("tbtn").tooltip("AI Macros")
                with btn_macro: ui.html(_I_MACRO)

                ui.element("div").style("width:1px;height:24px;background:rgba(255,255,255,0.4);margin:0 4px;")

                btn_menu  = ui.element("button").classes("tbtn tbtn-square").tooltip("Menú")
                with btn_menu:  ui.html(_I_MENU)

            # ── Menú dropdown ─────────────────────────────────────────────────
            menu_el = ui.element("div").classes("menu glass").style("display:none;")
            with menu_el:
                item_min  = ui.element("div").classes("item")
                with item_min:
                    ui.html(_I_MIN)
                    ui.label("Minimizar a toolbar")

                item_pin  = ui.element("div").classes("item")
                with item_pin:
                    ui.html(_I_PIN)
                    ui.label("Fijar en pantalla")

                item_pref = ui.element("div").classes("item")
                with item_pref:
                    ui.html(_I_COG)
                    ui.label("Preferencias…")

                ui.element("div").classes("sep")

                item_close = ui.element("div").classes("item danger")
                with item_close:
                    ui.html(_I_CLOSE)
                    ui.label("Cerrar")

        # ── Panel ─────────────────────────────────────────────────────────────
        panel_el = ui.element("div").classes("panel glass")
        with panel_el:

            _view_style = "display:flex;flex-direction:column;height:100%;overflow:hidden;"
            _chat_ref = {}  # forward ref para load_conversation

            def _on_open_chat(cid):
                _switch_panel("chat", app_state, btn_chat, btn_log, btn_macro, view_chat, view_log, view_macro)
                if _chat_ref.get("load"):
                    _chat_ref["load"](cid)

            with ui.element("div").style(_view_style) as view_log:
                refresh_history = history_page(on_open_chat=_on_open_chat)

            with ui.element("div").style(_view_style) as view_chat:
                _chat_ref["load"] = chat_page(on_new_chat=refresh_history)

            with ui.element("div").style(_view_style) as view_macro:
                macros_page(hotkey_manager=hotkey_manager)

        view_log.set_visibility(False)
        view_macro.set_visibility(False)

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def _toggle_menu():
        app_state["menu_open"] = not app_state["menu_open"]
        menu_el.style("display:block;" if app_state["menu_open"] else "display:none;")
        if app_state["menu_open"]:
            btn_menu.classes(add="active")
        else:
            btn_menu.classes(remove="active")

    def _minimize():
        app_state["menu_open"] = False
        menu_el.style("display:none;")
        btn_menu.classes(remove="active")
        if app_state["win"] == "open":
            app_state["win"] = "minimized"
            panel_el.set_visibility(False)
        else:
            app_state["win"] = "open"
            panel_el.set_visibility(True)

    def _close():
        app.shutdown()

    def _reopen():
        app_state["win"] = "open"
        widget_el.set_visibility(True)
        panel_el.set_visibility(True)
        reopen_el.style("display:none;")

    def _switch_chat():
        if app_state["win"] == "minimized":
            app_state["win"] = "open"
            panel_el.set_visibility(True)
        _switch_panel("chat", app_state, btn_chat, btn_log, btn_macro, view_chat, view_log, view_macro)
        app_state["menu_open"] = False
        menu_el.style("display:none;")

    def _switch_log():
        if app_state["win"] == "minimized":
            app_state["win"] = "open"
            panel_el.set_visibility(True)
        _switch_panel("log", app_state, btn_chat, btn_log, btn_macro, view_chat, view_log, view_macro)
        app_state["menu_open"] = False
        menu_el.style("display:none;")

    def _switch_macro():
        if app_state["win"] == "minimized":
            app_state["win"] = "open"
            panel_el.set_visibility(True)
        _switch_panel("macro", app_state, btn_chat, btn_log, btn_macro, view_chat, view_log, view_macro)
        app_state["menu_open"] = False
        menu_el.style("display:none;")

    btn_chat.on("click",  _switch_chat)
    btn_log.on("click",   _switch_log)
    btn_macro.on("click", _switch_macro)
    btn_menu.on("click",  _toggle_menu)
    item_min.on("click",  _minimize)
    item_close.on("click", _close)
    reopen_el.on("click", _reopen)


def _switch_panel(panel: str, app_state: dict,
                  btn_chat, btn_log, btn_macro,
                  view_chat, view_log, view_macro):
    app_state["panel"] = panel

    for btn, name in [(btn_chat, "chat"), (btn_log, "log"), (btn_macro, "macro")]:
        if name == panel:
            btn.classes(add="active")
        else:
            btn.classes(remove="active")

    view_chat.set_visibility(panel == "chat")
    view_log.set_visibility(panel == "log")
    view_macro.set_visibility(panel == "macro")


# ── Arranque ──────────────────────────────────────────────────────────────────

ui.run(
    title="Nivora",
    dark=False,
    reload=False,
    native=False,
    port=8765,
    storage_secret="nivora_secret_2024",
)
