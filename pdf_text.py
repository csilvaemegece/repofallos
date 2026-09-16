# -*- coding: utf-8 -*-
"""Extracción de texto de un PDF de sentencia (best-effort, para dejar
texto_fallo pre-cargado y listo para el resumen asistido por IA de la
Fase 3). Si el PDF es un escaneo sin capa de texto, devuelve cadena vacía
— no se hace OCR aquí."""
import io
import re

from pypdf import PdfReader


def _tolerante(txt):
    """Arma un patrón que matchea `txt` letra por letra, tolerando
    cualquier espacio/salto de línea (incluso cero) entre medio — la
    extracción de PDFs con columnas suele pegar o separar palabras de forma
    errática, así que un match literal o por palabras no sirve aquí."""
    return r"\s*".join(re.escape(c) for c in txt)


# Marca de agua de verificación que el Poder Judicial pega en cada página
# del PDF (código variable + aviso de firma electrónica + URL de validación).
# Ej.: "Código: GZXPCYRKKFDEstedocumento tienefirmaelectrónica
#       ysuoriginalpuedeservalidado en http://verificadoc.pjud.cl"
_PATRON_FIRMA = re.compile(
    r"C[oó]digo\s*:\s*[A-Z0-9]+\s*"
    + _tolerante("Estedocumentotienefirmaelectr")
    + "[oó]" + _tolerante("nicaysuoriginalpuedeservalidadoen")
    + r"\s*http\s*:\s*/\s*/\s*verificadoc\s*\.\s*pjud\s*\.\s*cl",
    re.IGNORECASE,
)


def _limpiar(texto):
    texto = _PATRON_FIRMA.sub("", texto)
    return re.sub(r"\n{3,}", "\n\n", texto).strip()


def extraer_texto(pdf_bytes):
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        paginas = [page.extract_text() or "" for page in reader.pages]
        texto = "\n\n".join(p.strip() for p in paginas if p.strip()).strip()
        return _limpiar(texto)
    except Exception:
        return ""
