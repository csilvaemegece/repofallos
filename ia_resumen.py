# -*- coding: utf-8 -*-
"""Resumen de la causa asistido por IA (Fase 3), a partir del texto del
fallo ya extraído (manual o vía "Buscar PDF en SITCORTE"). El resultado
siempre se entrega como borrador para revisar/editar antes de guardar —
nunca se persiste solo, sin que alguien lo confirme.

Usa OpenRouter (https://openrouter.ai) en vez de una cuenta propia de un
proveedor de IA — OpenRouter da acceso a modelos gratuitos con una API
compatible con OpenAI (endpoint /chat/completions). La lista de modelos
gratuitos cambia con el tiempo; confirmá el actual en
https://openrouter.ai/models?max_price=0 y ajustá OPENROUTER_MODEL si hace
falta.
"""
import os

import requests

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")

MIN_LARGO_TEXTO = 200

SYSTEM_PROMPT = """Sos un asistente que redacta resúmenes breves y precisos de fallos \
judiciales de la Corte de Apelaciones de Rancagua (Chile), para un repositorio de \
conocimiento interno.

Resumí ÚNICAMENTE en base al texto del fallo que se te entrega — no inventes hechos, \
partes, fechas ni argumentos que no estén en el texto. Si algo no queda claro en el \
texto, decilo en vez de adivinar.

Estructurá la respuesta en estas 4 secciones, exactamente con estos títulos:

Hechos: (resumen breve de los hechos y antecedentes de la causa)
Cuestión jurídica: (el problema o pregunta jurídica que debía resolver la Corte)
Decisión: (qué resolvió la Corte y el resultado concreto)
Argumento central: (el razonamiento principal que sostiene la decisión)

Sé conciso — no más de 250 palabras en total. Español formal, sin lenguaje grandilocuente."""


class IAError(Exception):
    """Error de negocio (sin API key, texto insuficiente, error de la API) para
    mostrar al usuario."""


def generar_resumen(texto_fallo, materia="", tipo_recurso="", resultado="", caratula=""):
    texto_fallo = (texto_fallo or "").strip()
    if len(texto_fallo) < MIN_LARGO_TEXTO:
        raise IAError(
            "El texto del fallo es muy corto o está vacío (puede que el PDF sea un "
            "escaneo sin capa de texto). Completá o corregí texto_fallo antes de generar el resumen.")

    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise IAError(
            "Falta configurar OPENROUTER_API_KEY (conseguí una gratis en "
            "https://openrouter.ai/keys) antes de generar el resumen.")

    contexto = "\n".join(
        f"{etiqueta}: {valor}"
        for etiqueta, valor in [
            ("Carátula", caratula), ("Materia", materia),
            ("Tipo de recurso", tipo_recurso), ("Resultado", resultado),
        ] if valor
    )
    mensaje_usuario = (
        (f"Datos de la causa (metadata de SITCORTE, puede ser incompleta):\n{contexto}\n\n"
         if contexto else "")
        + f"Texto del fallo:\n\n{texto_fallo}"
    )

    try:
        r = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": mensaje_usuario},
                ],
                "max_tokens": 2000,
            },
            timeout=90,
        )
    except requests.RequestException as e:
        raise IAError(f"No se pudo conectar con OpenRouter: {e}")

    if r.status_code == 401:
        raise IAError("OPENROUTER_API_KEY inválida o vencida.")
    if r.status_code == 429:
        raise IAError(
            f"Se alcanzó el límite de uso del modelo gratuito ({MODEL}) en OpenRouter — "
            "probá de nuevo en un momento, o cambiá OPENROUTER_MODEL por otro modelo gratuito.")
    if r.status_code != 200:
        raise IAError(f"Error de OpenRouter (HTTP {r.status_code}): {r.text[:300]}")

    try:
        data = r.json()
    except ValueError:
        raise IAError("OpenRouter devolvió una respuesta que no se pudo interpretar.")

    if data.get("error"):
        raise IAError(f"Error de OpenRouter: {data['error'].get('message', data['error'])}")

    choices = data.get("choices") or []
    if not choices:
        raise IAError("OpenRouter no devolvió una respuesta utilizable.")

    texto = ((choices[0].get("message") or {}).get("content") or "").strip()
    if not texto:
        raise IAError("El modelo no devolvió texto para el resumen.")
    return texto
