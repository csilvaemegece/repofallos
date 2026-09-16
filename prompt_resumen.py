# -*- coding: utf-8 -*-
"""Construye el prompt para pedirle el resumen de un fallo a Copilot (la IA
autorizada acá) — no se llama a ninguna API de IA desde el servidor. El
usuario copia el prompt con un botón y lo pega él mismo en Copilot; el
resultado lo revisa y lo carga a mano en el formulario de edición."""

MIN_LARGO_TEXTO = 200

INSTRUCCIONES = """Actuá como asistente de redacción para el Repositorio de Fallos de la \
C.A. de Rancagua. Te paso el texto completo de un fallo judicial.

Necesito que generes un resumen estructurado, basado ÚNICAMENTE en el texto que te doy \
— no inventes hechos, partes, fechas ni argumentos que no estén en el texto. Si algo no \
queda claro, decilo en vez de adivinar.

Estructurá la respuesta en estas secciones, con estos títulos exactos:

Hechos: (resumen breve de los hechos y antecedentes de la causa)
Cuestión jurídica: (el problema o pregunta jurídica que debía resolver la Corte)
Decisión: (qué resolvió la Corte y el resultado concreto)
Argumento central: (el razonamiento principal que sostiene la decisión)
Votos disidentes: (si algún ministro o ministra votó en contra o hizo una prevención, \
resumí su fundamento; si no hubo, escribí "No hubo votos disidentes")
Palabras clave: (entre 5 y 8 palabras o frases cortas para buscar esta causa después — \
instituciones jurídicas, materias, normas citadas, tipo de conflicto, etc. Ponelas en \
una sola línea, separadas por coma, sin numerar ni viñetas, listas para pegar tal cual \
en un campo de tags)

Sé conciso — no más de 300 palabras en total (sin contar las palabras clave). Español \
formal, sin lenguaje grandilocuente."""


class PromptError(Exception):
    """Error de negocio (texto insuficiente) para mostrar al usuario."""


def construir_prompt(texto_fallo, materia="", tipo_recurso="", resultado="", caratula="", rol=""):
    texto_fallo = (texto_fallo or "").strip()
    if len(texto_fallo) < MIN_LARGO_TEXTO:
        raise PromptError(
            "El texto del fallo es muy corto o está vacío (puede que el PDF sea un "
            "escaneo sin capa de texto). Completá o corregí texto_fallo antes de generar el prompt.")

    contexto = "\n".join(
        f"{etiqueta}: {valor}"
        for etiqueta, valor in [
            ("Rol", rol), ("Carátula", caratula), ("Materia", materia),
            ("Tipo de recurso", tipo_recurso), ("Resultado", resultado),
        ] if valor
    )

    partes = [INSTRUCCIONES, "---"]
    if contexto:
        partes.append(f"Datos de la causa (metadata de SITCORTE, puede ser incompleta):\n{contexto}")
    partes.append(f"Texto del fallo:\n\n{texto_fallo}")
    return "\n\n".join(partes)
