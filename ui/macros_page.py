from __future__ import annotations

import subprocess

from nicegui import ui

from data.database import get_all_macros, create_macro, delete_macro, update_macro_hotkey

_MACRO_ICON_SVG = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" style="color:var(--accent)"><path d="M13 3 5 13h6l-1 8 8-10h-6l1-8z"/></svg>'
_MACRO_ICON_CARD = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" style="color:white"><path d="M13 3 5 13h6l-1 8 8-10h-6l1-8z"/></svg>'
_PLAY_ICON = '<svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>'


def macros_page(hotkey_manager=None):
    macros = get_all_macros()
    active_count = len(macros)
    hot_count = sum(1 for m in macros if m.get("hotkey"))

    # ── Head ──────────────────────────────────────────────────────────────────
    with ui.element("div").classes("panel-head"):
        with ui.element("div"):
            with ui.element("h2"):
                ui.html(_MACRO_ICON_SVG)
                ui.label("AI Macros")
            with ui.element("div").classes("subtitle"):
                ui.label(f"{active_count} activas · {hot_count} con hotkey")

        with ui.element("button").classes("run-btn").style(
            "background:rgba(255,255,255,0.55);color:var(--ink);"
        ) as new_btn:
            ui.label("+ Nueva")

    # ── Body ──────────────────────────────────────────────────────────────────
    with ui.element("div").classes("panel-body"):
        macro_list = ui.element("div")

    def _reload():
        macro_list.clear()
        _render_macros(macro_list, hotkey_manager, _reload)

    new_btn.on("click", lambda: _dialog_nueva(hotkey_manager, _reload))
    _reload()


def _render_macros(macro_list, hotkey_manager, reload_fn):
    macros = get_all_macros()
    if not macros:
        with macro_list:
            with ui.element("div").classes("empty"):
                ui.html(_MACRO_ICON_SVG)
                ui.label("Sin macros creadas")
        return

    with macro_list:
        for macro in macros:
            _macro_card(macro, hotkey_manager, reload_fn)


def _macro_card(macro: dict, hotkey_manager, reload_fn):
    running_state = {"running": False}

    with ui.element("div").classes("macro-card"):
        # Icono
        with ui.element("div").classes("macro-icon"):
            ui.html(_MACRO_ICON_CARD)

        # Info
        with ui.element("div").classes("macro-info"):
            with ui.element("div").classes("macro-title"):
                ui.label(macro["name"])
                if macro.get("hotkey"):
                    with ui.element("span").classes("kbd"):
                        ui.label(macro["hotkey"])
            with ui.element("div").classes("macro-meta"):
                ui.label((macro.get("content") or "")[:50])

        # Run button
        run_btn_el = ui.element("button").classes("run-btn")
        with run_btn_el:
            ui.html(f'{_PLAY_ICON} <span style="margin-left:3px;">Run</span>')

        def _run(m=macro):
            if running_state["running"]:
                return
            running_state["running"] = True
            run_btn_el.classes(add="running")
            run_btn_el.clear()
            with run_btn_el:
                ui.label("● Running")
            try:
                subprocess.Popen(m["content"], shell=True)
            except Exception as e:
                ui.notify(f"Error: {e}", type="negative")

            def _reset():
                running_state["running"] = False
                run_btn_el.classes(remove="running")
                run_btn_el.clear()
                with run_btn_el:
                    ui.html(f'{_PLAY_ICON} <span style="margin-left:3px;">Run</span>')

            ui.timer(1.5, _reset, once=True)

        run_btn_el.on("click", _run)

        # Toggle (habilitado/deshabilitado)
        is_on = bool(macro.get("hotkey"))
        toggle_el = ui.element("div").classes("toggle" + (" on" if is_on else ""))

        def _toggle(m=macro):
            # Activar/desactivar hotkey: si tiene hotkey la quitamos, si no la ponemos
            # Por simplicidad: abre diálogo de edición de hotkey
            _dialog_hotkey(m, hotkey_manager, reload_fn)

        toggle_el.on("click", _toggle)

        # Botón eliminar (pequeño, al hover)
        del_btn = ui.element("button").style(
            "background:none;border:none;cursor:pointer;color:var(--ink-faint);"
            "font-size:16px;padding:0 4px;margin-left:4px;"
        )
        with del_btn:
            ui.label("×")
        del_btn.on("click", lambda m=macro: _delete(m, hotkey_manager, reload_fn))


def _delete(macro: dict, hotkey_manager, reload_fn):
    delete_macro(macro["id"])
    if hotkey_manager:
        hotkey_manager.reload()
    reload_fn()


def _dialog_hotkey(macro: dict, hotkey_manager, reload_fn):
    with ui.dialog() as dlg, ui.card().style("min-width:300px;border-radius:18px;"):
        ui.label(f"Hotkey — {macro['name']}").style("font-size:14px;font-weight:600;margin-bottom:10px;")
        hotkey_input = ui.input("Hotkey (ej: ctrl+shift+a)", value=macro.get("hotkey") or "").props("dense outlined").style("width:100%;")

        with ui.row().style("justify-content:flex-end;gap:8px;margin-top:8px;"):
            ui.button("Cancelar", on_click=dlg.close).props("flat")

            def _guardar():
                update_macro_hotkey(macro["id"], hotkey_input.value.strip() or None)
                if hotkey_manager:
                    hotkey_manager.reload()
                reload_fn()
                dlg.close()

            with ui.element("button").classes("run-btn").on("click", _guardar):
                ui.label("Guardar")

    dlg.open()


def _dialog_nueva(hotkey_manager, reload_fn):
    with ui.dialog() as dlg, ui.card().style("min-width:320px;border-radius:18px;"):
        ui.label("Nueva macro").style("font-size:15px;font-weight:600;margin-bottom:12px;")

        nombre = ui.input("Nombre").props("dense outlined").style("width:100%;")
        hotkey_input = ui.input("Hotkey (ej: ctrl+shift+a)").props("dense outlined").style("width:100%;")
        tipo = ui.select(["text", "shell"], value="shell", label="Tipo").props("dense outlined").style("width:100%;")
        contenido = ui.textarea("Contenido / comando").props("dense outlined").style("width:100%;")

        with ui.row().style("justify-content:flex-end;gap:8px;margin-top:8px;"):
            ui.button("Cancelar", on_click=dlg.close).props("flat")

            def _guardar():
                if not nombre.value.strip():
                    ui.notify("El nombre es obligatorio", type="warning")
                    return
                create_macro(
                    nombre.value.strip(),
                    contenido.value,
                    tipo.value,
                    hotkey_input.value.strip() or None,
                )
                if hotkey_manager:
                    hotkey_manager.reload()
                reload_fn()
                dlg.close()

            with ui.element("button").classes("run-btn").on("click", _guardar):
                ui.label("Guardar")

    dlg.open()
