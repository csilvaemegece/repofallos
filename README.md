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
- **Fase 3 — Prompt para resumen con IA** — botón "Generar Prompt" en la
  ficha de un fallo con texto cargado: arma un prompt (con el texto del
  fallo + instrucciones para estructurar hechos, cuestión jurídica,
  decisión, argumento central y votos disidentes) y lo copia al
  portapapeles. No se llama a ninguna API de IA desde el servidor — el
  prompt se pega a mano en Copilot (la IA autorizada) y el resultado se
  revisa y carga en el formulario de edición.
- **Votos disidentes** — campo propio para el voto de minoría o
  prevención, si lo hubo, con su propia sección destacada en la ficha del
  fallo.
- **Publicación automática y limpieza de PDF** — al guardar, si el fallo
  ya tiene resumen y tags, pasa a estado "Publicado" solo. Y si además
  tiene el texto del fallo cargado y el PDF vino de SITCORTE (no subido a
  mano), el archivo se borra del servidor para ahorrar espacio — siempre
  se puede volver a pedir con "Buscar PDF en SITCORTE".

### Próxima fase

- Fase 2: autogenerar borradores de fallo a partir del detector de
  "desenlace final" que ya existe en `sitcorte_web` (monitor/tablas), para
  el caso en que no se quiera importar por rango de fechas manualmente.

## Instalación

```bash
pip install -r requirements.txt
```

El resumen con IA no necesita ninguna API key ni configuración: el botón
"Generar Prompt" arma el texto y lo copia al portapapeles directo en el
navegador, para pegarlo en Copilot a mano.

## Ejecución

```bash
python app.py
```

La app queda disponible en `http://localhost:5050`. La base de datos SQLite
(`fallos.db`) y los PDFs adjuntos (`uploads/`) se crean localmente y están
excluidos del repo vía `.gitignore`.
