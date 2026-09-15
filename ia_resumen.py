# -*- coding: utf-8 -*-
"""Resumen de la causa asistido por IA (Fase 3), a partir del texto del
fallo ya extraído (manual o vía "Buscar PDF en SITCORTE"). El resultado
siempre se entrega como borrador para revisar/editar antes de guardar —
nunca se persiste solo, sin que alguien lo confirme."""
import anthropic

MODEL = "claude-opus-5"

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
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": mensaje_usuario}],
        )
    except anthropic.AuthenticationError:
        raise IAError(
            "No se pudo autenticar con la API de Claude — falta configurar "
            "ANTHROPIC_API_KEY (o el perfil de `ant auth login`) en esta máquina.")
    except anthropic.RateLimitError:
        raise IAError("Se alcanzó el límite de uso de la API de Claude — probá de nuevo en un momento.")
    except anthropic.APIStatusError as e:
        raise IAError(f"Error de la API de Claude ({e.status_code}): {e.message}")
    except anthropic.APIConnectionError as e:
        raise IAError(f"No se pudo conectar con la API de Claude: {e}")

    if response.stop_reason == "refusal":
        raise IAError("El modelo no pudo generar el resumen para este texto.")

    texto = "\n".join(b.text for b in response.content if b.type == "text").strip()
    if not texto:
        raise IAError("El modelo no devolvió texto para el resumen.")
    return texto
