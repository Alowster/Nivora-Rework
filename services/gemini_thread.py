import os
from pathlib import Path

from dotenv import load_dotenv
from google.genai import Client
from google.genai import types
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
