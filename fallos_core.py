# -*- coding: utf-8 -*-
"""
Acceso a datos del Repositorio de Fallos: SQLite (tabla `fallos`) + lista
de materias configurable (config_materias.json), siguiendo el mismo patrón
de config editable que usa sitcorte_web con config_ministros.json.
"""
import os
import sqlite3
import datetime
import json

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "fallos.db")
MATERIAS_PATH = os.path.join(BASE_DIR, "config_materias.json")

CAMPOS_FALLO = [
    "rol", "caratula", "sala", "ministro_redactor", "materia",
    "tipo_recurso", "resultado", "tags", "resumen", "texto_fallo",
    "archivo_pdf", "archivo_pdf_nombre", "fecha_fallo", "estado",
]

TIPOS_RECURSO_SUGERIDOS = [
    "Apelación", "Casación en la Forma", "Casación en el Fondo",
    "Amparo", "Protección", "Queja", "Nulidad", "Otro",
]

RESULTADOS_SUGERIDOS = [
    "Confirma", "Revoca", "Aprueba", "Admisibilidad", "Resuelta", "Fallado",
    "C.Mod.Fallo 1ªInst.", "C.Fallo. con 3 Consi", "Acogida", "Rechazada",
    "Abandonado",
]

ESTADOS = ["borrador", "publicado"]


def _now_iso():
    return datetime.datetime.now().isoformat(timespec="seconds")


def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_db():
    con = get_db()
    con.execute("""
        CREATE TABLE IF NOT EXISTS fallos (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            rol                 TEXT,
            caratula            TEXT,
            sala                TEXT,
            ministro_redactor   TEXT,
            materia             TEXT,
            tipo_recurso        TEXT,
            resultado           TEXT,
            tags                TEXT,
            resumen             TEXT,
            texto_fallo         TEXT,
            archivo_pdf         TEXT,
            archivo_pdf_nombre  TEXT,
            fecha_fallo         TEXT,
            estado              TEXT NOT NULL DEFAULT 'borrador',
            clave_sitcorte      TEXT,
            creado_en           TEXT NOT NULL,
            actualizado_en      TEXT NOT NULL
        )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS idx_fallos_materia   ON fallos(materia)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_fallos_resultado ON fallos(resultado)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_fallos_sala      ON fallos(sala)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_fallos_estado    ON fallos(estado)")
    con.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_fallos_clave_sitcorte
        ON fallos(clave_sitcorte) WHERE clave_sitcorte IS NOT NULL AND clave_sitcorte != ''
    """)
    con.commit()
    con.close()


# ── Materias (taxonomía editable) ──────────────────────────────────────────

def cargar_materias():
    try:
        with open(MATERIAS_PATH, encoding="utf-8") as f:
            return json.load(f).get("materias", [])
    except Exception:
        return []


def guardar_materias(lista):
    limpio = [m.strip() for m in lista if m.strip()]
    with open(MATERIAS_PATH, "w", encoding="utf-8") as f:
        json.dump({"materias": limpio}, f, ensure_ascii=False, indent=2)


# ── CRUD de fallos ──────────────────────────────────────────────────────────

def crear_fallo(data):
    con = get_db()
    ahora = _now_iso()
    campos = CAMPOS_FALLO + ["creado_en", "actualizado_en"]
    valores = [data.get(c, "") for c in CAMPOS_FALLO] + [ahora, ahora]
    placeholders = ", ".join("?" for _ in campos)
    cur = con.execute(
        f"INSERT INTO fallos ({', '.join(campos)}) VALUES ({placeholders})",
        valores,
    )
    con.commit()
    nuevo_id = cur.lastrowid
    con.close()
    return nuevo_id


def actualizar_fallo(fallo_id, data):
    con = get_db()
    sets = ", ".join(f"{c} = ?" for c in CAMPOS_FALLO)
    valores = [data.get(c, "") for c in CAMPOS_FALLO] + [_now_iso(), fallo_id]
    con.execute(
        f"UPDATE fallos SET {sets}, actualizado_en = ? WHERE id = ?",
        valores,
    )
    con.commit()
    con.close()


def importar_fallo(data):
    """Inserta un fallo proveniente de una fuente externa (SITCORTE),
    evitando duplicados por 'clave_sitcorte'. Devuelve (fallo_id, creado)."""
    clave = (data.get("clave_sitcorte") or "").strip()
    con = get_db()
    if clave:
        existente = con.execute(
            "SELECT id FROM fallos WHERE clave_sitcorte = ?", (clave,)
        ).fetchone()
        if existente:
            con.close()
            return existente["id"], False

    ahora = _now_iso()
    campos = CAMPOS_FALLO + ["clave_sitcorte", "creado_en", "actualizado_en"]
    valores = [data.get(c, "") for c in CAMPOS_FALLO] + [clave, ahora, ahora]
    placeholders = ", ".join("?" for _ in campos)
    try:
        cur = con.execute(
            f"INSERT INTO fallos ({', '.join(campos)}) VALUES ({placeholders})",
            valores,
        )
        con.commit()
        nuevo_id = cur.lastrowid
        creado = True
    except sqlite3.IntegrityError:
        # Carrera con otra importación concurrente sobre la misma clave.
        existente = con.execute(
            "SELECT id FROM fallos WHERE clave_sitcorte = ?", (clave,)
        ).fetchone()
        nuevo_id = existente["id"] if existente else None
        creado = False
    con.close()
    return nuevo_id, creado


def eliminar_fallo(fallo_id):
    con = get_db()
    con.execute("DELETE FROM fallos WHERE id = ?", (fallo_id,))
    con.commit()
    con.close()


def obtener_fallo(fallo_id):
    con = get_db()
    row = con.execute("SELECT * FROM fallos WHERE id = ?", (fallo_id,)).fetchone()
    con.close()
    return dict(row) if row else None


def listar_fallos(filtros=None):
    """filtros: dict con claves opcionales materia, tipo_recurso, resultado,
    sala, ministro_redactor, estado, tag, q (texto libre), desde, hasta
    (fecha_fallo en formato YYYY-MM-DD)."""
    filtros = filtros or {}
    where, params = [], []

    for campo in ("materia", "tipo_recurso", "resultado", "sala",
                  "ministro_redactor", "estado"):
        val = filtros.get(campo)
        if val:
            where.append(f"{campo} = ?")
            params.append(val)

    if filtros.get("tag"):
        where.append("tags LIKE ?")
        params.append(f"%{filtros['tag']}%")

    if filtros.get("q"):
        q = f"%{filtros['q']}%"
        where.append("(rol LIKE ? OR caratula LIKE ? OR resumen LIKE ? OR texto_fallo LIKE ?)")
        params += [q, q, q, q]

    if filtros.get("desde"):
        where.append("fecha_fallo >= ?")
        params.append(filtros["desde"])

    if filtros.get("hasta"):
        where.append("fecha_fallo <= ?")
        params.append(filtros["hasta"])

    sql = "SELECT * FROM fallos"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY COALESCE(NULLIF(fecha_fallo, ''), creado_en) DESC, id DESC"

    con = get_db()
    filas = [dict(r) for r in con.execute(sql, params).fetchall()]
    con.close()
    return filas


def valores_distintos(campo):
    if campo not in CAMPOS_FALLO:
        return []
    con = get_db()
    filas = con.execute(
        f"SELECT DISTINCT {campo} FROM fallos "
        f"WHERE {campo} IS NOT NULL AND {campo} != '' ORDER BY {campo}"
    ).fetchall()
    con.close()
    return [r[0] for r in filas]
