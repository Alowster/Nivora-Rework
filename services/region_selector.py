import threading
import tkinter as tk
from PIL import ImageGrab


def select_region(callback):
    """
    Abre un overlay fullscreen para seleccionar una región con el ratón.
    Llama a callback(path: str) con la ruta del PNG capturado al soltar.
    """
    def _run():
        root = tk.Tk()
        root.attributes("-fullscreen", True)
        root.attributes("-alpha", 0.25)
        root.attributes("-topmost", True)
        root.configure(bg="black")
        root.update_idletasks()

        canvas = tk.Canvas(root, cursor="crosshair", bg="black", highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        start = {}
        rect_id = [None]

        def on_press(e):
            start["x"], start["y"] = e.x_root, e.y_root

        def on_drag(e):
            if rect_id[0]:
                canvas.delete(rect_id[0])
            x0 = start["x"] - root.winfo_rootx()
            y0 = start["y"] - root.winfo_rooty()
            x1 = e.x - root.winfo_rootx()
            y1 = e.y - root.winfo_rooty()
            rect_id[0] = canvas.create_rectangle(x0, y0, x1, y1, outline="white", width=2)

        def on_release(e):
            x1 = min(start["x"], e.x_root)
            y1 = min(start["y"], e.y_root)
            x2 = max(start["x"], e.x_root)
            y2 = max(start["y"], e.y_root)
            root.destroy()
            if x2 - x1 < 5 or y2 - y1 < 5:
                return
            import tempfile, os
            img = ImageGrab.grab(bbox=(x1, y1, x2, y2), all_screens=True)
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            img.save(tmp.name)
            tmp.close()
            callback(tmp.name)

        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)
        root.bind("<Escape>", lambda e: root.destroy())
        root.mainloop()

    threading.Thread(target=_run, daemon=True).start()
