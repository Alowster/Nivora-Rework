from PySide6.QtCore import QThread, Signal
import ollama
from config import OLLAMA_MODEL, OLLAMA_MAX_TOKENS

class AIService(QThread):
    chunk_received = Signal(str)
    completed = Signal()
    error = Signal(str)

    def __init__(self, messages):
        super().__init__()
        self.messages = messages
        self._stop_requested = False
        self._stream = None

    def run(self):
        try:
            mensajes = [{"role": m["role"], "content": m["content"]} for m in self.messages]
            self._stream = ollama.chat(model=OLLAMA_MODEL, messages=mensajes, stream=True, options={"num_predict": OLLAMA_MAX_TOKENS})
            for chunk in self._stream:
                if self._stop_requested:
                    break
                text = chunk["message"]["content"]
                self.chunk_received.emit(text)
            else:
                self.completed.emit()
        except Exception as e:
                if not self._stop_requested:
                    self.error.emit(str(e))
        finally:
                self._stream = None

    def stop(self):
        self._stop_requested = True
        if self._stream is not None:
            try:
                self._stream.close()
            except Exception:
                pass