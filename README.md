# Repositorio de Fallos

Centro de conocimiento de fallos de la C.A. de Rancagua: carga, clasificación
(materia, tipo de recurso y resultado, sala, ministro redactor, tags libres)
y resumen de causas, con búsqueda y filtros.

Proyecto independiente pensado para eventualmente integrarse a `sitcorte_web`
(S.A.C.A.) una vez validado.

## Estado actual — Fase 1

- Alta/edición/baja manual de fallos, con adjunto de PDF.
- Listado con filtros por materia, tipo de recurso, resultado, sala,
  ministro redactor, tag, texto libre y rango de fechas.
- Taxonomía de materias editable (`/materias`).
- Resumen de la causa: campo de texto manual (sin IA todavía).

### Próximas fases

- Fase 2: autogenerar borradores de fallo a partir del detector de
  "desenlace final" que ya existe en `sitcorte_web` (monitor/tablas).
- Fase 3: resumen asistido por IA a partir del texto/PDF del fallo,
  siempre como borrador editable antes de publicar.

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecución

```bash
python app.py
```

La app queda disponible en `http://localhost:5050`. La base de datos SQLite
(`fallos.db`) y los PDFs adjuntos (`uploads/`) se crean localmente y están
excluidos del repo vía `.gitignore`.
