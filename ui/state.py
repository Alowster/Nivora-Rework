from nicegui import app


def get_active_conversation() -> int | None:
    return app.storage.user.get("conversation_id")


def set_active_conversation(conv_id: int | None):
    app.storage.user["conversation_id"] = conv_id
