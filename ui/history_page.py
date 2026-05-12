from __future__ import annotations

from datetime import datetime

from nicegui import ui

from data.database import get_all_conversations, delete_conversation

_LOG_ICON  = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" style="color:var(--accent)"><path d="M4 5h16M4 10h16M4 15h10M4 20h7"/></svg>'
_TRASH_ICON = '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>'
_SEARCH_ICON = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" style="color:var(--ink-faint)"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>'


def history_page(on_open_chat=None):
    state = {"month": None, "query": ""}

    conversations = get_all_conversations()

    # Extraer meses únicos ordenados (más reciente primero)
    months = _get_months(conversations)

    # ── Head ──────────────────────────────────────────────────────────────────
    with ui.element("div").classes("panel-head"):
        with ui.element("div"):
            with ui.element("h2"):
                ui.html(_LOG_ICON)
                ui.label("AI Log")
            with ui.element("div").classes("subtitle"):
                subtitle_lbl = ui.label(f"{len(conversations)} conversaciones")

        # Chips de mes (scroll horizontal si hay muchos)
        with ui.element("div").classes("log-tabs").style("overflow-x:auto;max-width:200px;"):
            month_btns: dict[str | None, object] = {}

            # Chip "Todo"
            btn_all = ui.element("span").classes("chip on").style("white-space:nowrap;cursor:pointer;")
            with btn_all:
                ui.label("Todo")
            month_btns[None] = btn_all

            for ym in months:
                btn = ui.element("span").classes("chip").style("white-space:nowrap;cursor:pointer;")
                with btn:
                    ui.label(_ym_label(ym))
                month_btns[ym] = btn

    # ── Body ──────────────────────────────────────────────────────────────────
    with ui.element("div").classes("panel-body"):
        # Barra de búsqueda
        with ui.element("div").classes("composer").style("margin-bottom:10px;padding:4px 12px;"):
            ui.html(_SEARCH_ICON)
            search_input = ui.input(placeholder="Buscar…").props("borderless dense").style(
                "flex:1;border:0;background:transparent;outline:none;"
                "font-size:13px;font-family:inherit;padding:6px 0;"
            )

        list_el = ui.element("div").style("display:flex;flex-direction:column;gap:2px;")

    # ── Lógica de filtros ─────────────────────────────────────────────────────

    def _set_month(ym: str | None):
        state["month"] = ym
        for k, b in month_btns.items():
            if k == ym:
                b.classes(add="on")
            else:
                b.classes(remove="on")
        _rebuild()

    def _on_search(e):
        val = e.args if isinstance(e.args, str) else (
            e.args.get("value", "") if isinstance(e.args, dict) else ""
        )
        state["query"] = val
        _rebuild()

    for ym_key in month_btns:
        k = ym_key
        month_btns[k].on("click", lambda _k=k: _set_month(_k))

    search_input.on("keyup", _on_search)

    def _rebuild():
        convs = get_all_conversations()
        # Filtrar por mes
        if state["month"]:
            convs = [c for c in convs if _conv_ym(c) == state["month"]]
        # Filtrar por búsqueda
        q = state["query"].strip().lower()
        if q:
            convs = [c for c in convs if q in c["name"].lower()]
        # Actualizar subtitle
        subtitle_lbl.set_text(f"{len(convs)} conversaciones")
        _render_list(list_el, convs, on_open_chat, _rebuild)

    _rebuild()
    return _rebuild


def _get_months(conversations: list) -> list[str]:
    seen: list[str] = []
    for c in conversations:
        ym = _conv_ym(c)
        if ym and ym not in seen:
            seen.append(ym)
    return seen


def _conv_ym(conv: dict) -> str | None:
    try:
        dt = datetime.fromisoformat(conv["created_at"])
        return dt.strftime("%Y-%m")
    except Exception:
        return None


def _ym_label(ym: str) -> str:
    try:
        dt = datetime.strptime(ym, "%Y-%m")
        return dt.strftime("%b %Y")
    except Exception:
        return ym


def _render_list(list_el, conversations: list, on_open_chat, rebuild):
    list_el.clear()

    if not conversations:
        with list_el:
            with ui.element("div").classes("empty"):
                ui.html(_LOG_ICON)
                ui.label("Sin conversaciones")
        return

    with list_el:
        for conv in conversations:
            _conv_row(conv, on_open_chat, rebuild)


def _conv_row(conv: dict, on_open_chat, rebuild):
    try:
        dt = datetime.fromisoformat(conv["created_at"])
        pill_text = dt.strftime("%b").upper()
        time_text = dt.strftime("%d/%m")
    except Exception:
        pill_text = "---"
        time_text = ""

    def _abrir():
        if on_open_chat:
            on_open_chat(conv["id"])

    def _eliminar():
        delete_conversation(conv["id"])
        rebuild()

    with ui.element("div").classes("log-row"):
        with ui.element("div").classes("log-row-body").style("cursor:pointer;").on("click", _abrir):
            with ui.element("span").classes("log-pill ok"):
                ui.label(pill_text)
            with ui.element("span").classes("log-text"):
                ui.label(conv["name"])
            with ui.element("span").classes("log-time"):
                ui.label(time_text)
        del_btn = ui.element("button").classes("log-del").on("click", _eliminar)
        with del_btn:
            ui.html(_TRASH_ICON)
