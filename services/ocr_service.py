import numpy as np
from PIL import ImageGrab, Image, ImageEnhance
from rapidocr_onnxruntime import RapidOCR
from PySide6.QtCore import QThread, Signal

class OcrService(QThread):
    completed = Signal(str)
    error = Signal(str)

    def __init__(self, x, y, w, h):
        super().__init__()
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def run(self):
        try:
            imagen = ImageGrab.grab(bbox=(self.x, self.y, self.x + self.w, self.y + self.h))
            imagen = imagen.resize((imagen.width * 2, imagen.height * 2), Image.LANCZOS)
            imagen = imagen.convert("L")
            imagen = ImageEnhance.Contrast(imagen).enhance(2.0)
            imagen_np = np.array(imagen)
            ocr = RapidOCR()
            resultado, _ = ocr(imagen_np)
            if not resultado:
                self.completed.emit("")
                return
            texto = "\n".join([linea[1] for linea in resultado])
            self.completed.emit(texto)
        except Exception as e:
            self.error.emit(str(e))