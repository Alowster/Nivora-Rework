# Implementaciones completadas

## Integración Gemini API

- Sustituido Ollama local por la API de Gemini (`gemini-3.1-flash-lite`)
- API key gestionada via `.env` + `python-dotenv` (excluida del repo con `.gitignore`)
- `services/gemini_thread.py` — QThread que llama a Gemini en streaming con soporte de texto, imágenes y archivos adjuntos (reemplaza `AIService` + Ollama)
- `services/gemini_service.py` — versión async del mismo servicio (preparada para la migración a NiceGUI)
- `services/region_selector.py` — overlay Tkinter para seleccionar región de pantalla y guardarla como PNG

## Chat panel

- Captura de pantalla regional enviada directamente a Gemini como imagen (eliminado OCR local con RapidOCR)
- Botón 📎 para adjuntar archivos (imágenes, PDF, etc.) desde el explorador de archivos
- Corrección: el panel no se cierra al abrir el explorador de archivos (swap temporal de `Qt.WindowType.Popup` → `Tool`)
- Los adjuntos pendientes se muestran encima del input antes de enviar
