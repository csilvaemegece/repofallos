# -*- coding: utf-8 -*-
"""Extracción de texto de un PDF de sentencia (best-effort, para dejar
texto_fallo pre-cargado y listo para el resumen asistido por IA de la
Fase 3). Si el PDF es un escaneo sin capa de texto, devuelve cadena vacía
— no hacemos OCR acá."""
import io

from pypdf import PdfReader


def extraer_texto(pdf_bytes):
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        paginas = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(p.strip() for p in paginas if p.strip()).strip()
    except Exception:
        return ""
