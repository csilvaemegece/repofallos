# Repositorio de Fallos

Centro de conocimiento de fallos de la C.A. de Rancagua: carga, clasificación
(materia, tipo de recurso y resultado, sala, ministro redactor, tags libres)
y resumen de causas, con búsqueda y filtros.

Proyecto independiente pensado para eventualmente integrarse a `sitcorte_web`
(S.A.C.A.) una vez validado.

## Estado actual

- **Fase 1** — Alta/edición/baja manual de fallos, con adjunto de PDF.
  Listado con filtros por materia, tipo de recurso, resultado, sala,
  ministro redactor, tag, texto libre y rango de fechas. Taxonomía de
  materias editable (`/materias`).
- **Importación desde SITCORTE** (`/importar`) — trae causas ya falladas
  (informe "Recursos Fallados") como borrador, con la opción de traer
  también el PDF y el texto de cada sentencia.
- **Buscar PDF por rol** (botón en la ficha de un fallo) — dado un fallo
  con materia+rol, busca su sentencia en la tramitación de SITCORTE y
  adjunta el PDF, precargando el texto extraído.
- **Fase 3 — Resumen asistido por IA** — botón "Generar resumen con IA"
  en la ficha de un fallo con texto cargado: genera un resumen (hechos,
  cuestión jurídica, decisión, argumento central) a partir de
  `texto_fallo`, usando un modelo gratuito vía [OpenRouter](https://openrouter.ai).
  Siempre se entrega como borrador en el formulario de edición — nunca se
  guarda sin que alguien lo revise.

### Próxima fase

- Fase 2: autogenerar borradores de fallo a partir del detector de
  "desenlace final" que ya existe en `sitcorte_web` (monitor/tablas), para
  el caso en que no se quiera importar por rango de fechas manualmente.

## Instalación

```bash
pip install -r requirements.txt
```

Para el resumen con IA (Fase 3) hace falta una API key gratuita de
[OpenRouter](https://openrouter.ai/keys):

```bash
export OPENROUTER_API_KEY=sk-or-...
```

Por default usa `meta-llama/llama-3.3-70b-instruct:free`. Los modelos
gratuitos de OpenRouter cambian con el tiempo (y tienen límites de uso
diarios/por minuto) — revisá cuál está disponible en
https://openrouter.ai/models?max_price=0 y, si hace falta, apuntá a otro:

```bash
export OPENROUTER_MODEL=otro-modelo:free
```

Sin `OPENROUTER_API_KEY`, todo el resto de la app funciona igual — el
botón de generar resumen simplemente muestra un error pidiendo
configurarla.

## Ejecución

```bash
python app.py
```

La app queda disponible en `http://localhost:5050`. La base de datos SQLite
(`fallos.db`) y los PDFs adjuntos (`uploads/`) se crean localmente y están
excluidos del repo vía `.gitignore`.
