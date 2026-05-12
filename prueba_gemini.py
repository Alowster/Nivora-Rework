import asyncio
import sys
from services.gemini_service import stream_response


async def describir_imagen(ruta: str):
    print(f"=== Describiendo: {ruta} ===\n")
    mensajes = [
        {
            "role": "user",
            "content": "Describe detalladamente qué ves en esta imagen.",
            "attachments": [{"path": ruta, "mime_type": "image/png"}],
        }
    ]
    async for chunk in stream_response(mensajes):
        print(chunk, end="", flush=True)
    print("\n")


async def main():
    if len(sys.argv) < 2:
        print("Uso: python prueba_gemini.py <ruta_imagen>")
        print("Ejemplo: python prueba_gemini.py assets/foto.png")
        return
    await describir_imagen(sys.argv[1])


asyncio.run(main())
