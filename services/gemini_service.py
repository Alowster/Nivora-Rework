import asyncio
import os
import base64
from pathlib import Path
from typing import AsyncGenerator

from dotenv import load_dotenv
from google.genai import Client
from google.genai import types

from config import GEMINI_MODEL

load_dotenv()


def _get_client() -> Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Falta GEMINI_API_KEY en el archivo .env")
    return Client(api_key=api_key)


def _build_contents(messages: list) -> list[types.Content]:
    """Convierte [{role, content, attachments?}] al formato Gemini."""
    contents = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        parts = []

        if m.get("content"):
            parts.append(types.Part.from_text(text=m["content"]))

        for att in m.get("attachments", []):
            mime = att.get("mime_type", "image/png")
            raw = Path(att["path"]).read_bytes()
            parts.append(types.Part.from_bytes(data=raw, mime_type=mime))

        if parts:
            contents.append(types.Content(role=role, parts=parts))

    return contents


def _sync_stream(client: Client, contents: list) -> tuple[list[str], int]:
    """Llama a Gemini de forma síncrona y devuelve (chunks, total_tokens)."""
    chunks = []
    last_chunk = None
    for chunk in client.models.generate_content_stream(
        model=GEMINI_MODEL,
        contents=contents,
    ):
        if chunk.text:
            chunks.append(chunk.text)
        last_chunk = chunk

    total_tokens = 0
    if last_chunk and getattr(last_chunk, "usage_metadata", None):
        total_tokens = getattr(last_chunk.usage_metadata, "total_token_count", 0) or 0

    return chunks, total_tokens


async def stream_response(messages: list, meta: dict | None = None) -> AsyncGenerator[str, None]:
    """
    Genera respuesta de Gemini en streaming.
    Soporta texto, imágenes y archivos adjuntos.
    Si se pasa meta, escribe {"total_tokens": N} al finalizar.
    """
    client = _get_client()
    contents = _build_contents(messages)

    chunks, total_tokens = await asyncio.to_thread(_sync_stream, client, contents)
    if meta is not None:
        meta["total_tokens"] = total_tokens
    for chunk in chunks:
        yield chunk
