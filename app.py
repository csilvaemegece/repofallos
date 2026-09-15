# -*- coding: utf-8 -*-
"""Repositorio de Fallos — Centro de Conocimiento de la C.A. de Rancagua."""
import os
import uuid

from flask import (Flask, render_template, request, redirect, url_for,
                    send_from_directory, abort)
from werkzeug.utils import secure_filename

import fallos_core as fc
import sitcorte_import as si

BASE_DIR = os.path.dirname(__file__)
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB por PDF

fc.init_db()


def _datos_form():
    data = {campo: request.form.get(campo, "").strip() for campo in fc.CAMPOS_FALLO}
    if data["estado"] not in fc.ESTADOS:
        data["estado"] = "borrador"
    return data


def _guardar_pdf_si_viene(data, pdf_actual=None, pdf_actual_nombre=None):
    """Si llegó un PDF nuevo en el form, lo guarda y actualiza data; si no,
    conserva el que ya tenía el fallo (edición sin reemplazar archivo)."""
    archivo = request.files.get("archivo_pdf")
    if archivo and archivo.filename:
        nombre_seguro = secure_filename(archivo.filename)
        nombre_disco = f"{uuid.uuid4().hex}_{nombre_seguro}"
        archivo.save(os.path.join(UPLOAD_DIR, nombre_disco))
        data["archivo_pdf"] = nombre_disco
        data["archivo_pdf_nombre"] = nombre_seguro
    else:
        data["archivo_pdf"] = pdf_actual or ""
        data["archivo_pdf_nombre"] = pdf_actual_nombre or ""
    return data


@app.route("/")
def index():
    return redirect(url_for("listado_fallos"))


# ── Listado + filtros ────────────────────────────────────────────────────────

@app.route("/fallos")
def listado_fallos():
    filtros = {
        "materia": request.args.get("materia", ""),
        "tipo_recurso": request.args.get("tipo_recurso", ""),
        "resultado": request.args.get("resultado", ""),
        "sala": request.args.get("sala", ""),
        "ministro_redactor": request.args.get("ministro_redactor", ""),
        "estado": request.args.get("estado", ""),
        "tag": request.args.get("tag", ""),
        "q": request.args.get("q", ""),
        "desde": request.args.get("desde", ""),
        "hasta": request.args.get("hasta", ""),
    }
    fallos = fc.listar_fallos(filtros)
    return render_template(
        "index.html", active_menu="fallos", fallos=fallos, filtros=filtros,
        materias=fc.cargar_materias(),
        salas=fc.valores_distintos("sala"),
        ministros=fc.valores_distintos("ministro_redactor"),
        resultados=fc.valores_distintos("resultado"),
        tipos_recurso=fc.valores_distintos("tipo_recurso"),
    )


# ── Alta ──────────────────────────────────────────────────────────────────

@app.route("/fallos/nuevo", methods=["GET", "POST"])
def nuevo_fallo():
    if request.method == "POST":
        data = _datos_form()
        data = _guardar_pdf_si_viene(data)
        nuevo_id = fc.crear_fallo(data)
        return redirect(url_for("detalle_fallo", fallo_id=nuevo_id))
    return render_template(
        "form.html", active_menu="fallos", modo="nuevo", fallo=None,
        materias=fc.cargar_materias(),
        tipos_recurso_sugeridos=fc.TIPOS_RECURSO_SUGERIDOS,
        resultados_sugeridos=fc.RESULTADOS_SUGERIDOS, estados=fc.ESTADOS,
    )


# ── Detalle ───────────────────────────────────────────────────────────────

@app.route("/fallos/<int:fallo_id>")
def detalle_fallo(fallo_id):
    fallo = fc.obtener_fallo(fallo_id)
    if not fallo:
        abort(404)
    return render_template("detalle.html", active_menu="fallos", fallo=fallo)


# ── Edición ───────────────────────────────────────────────────────────────

@app.route("/fallos/<int:fallo_id>/editar", methods=["GET", "POST"])
def editar_fallo(fallo_id):
    fallo = fc.obtener_fallo(fallo_id)
    if not fallo:
        abort(404)
    if request.method == "POST":
        data = _datos_form()
        data = _guardar_pdf_si_viene(
            data, pdf_actual=fallo.get("archivo_pdf"),
            pdf_actual_nombre=fallo.get("archivo_pdf_nombre"),
        )
        fc.actualizar_fallo(fallo_id, data)
        return redirect(url_for("detalle_fallo", fallo_id=fallo_id))
    return render_template(
        "form.html", active_menu="fallos", modo="editar", fallo=fallo,
        materias=fc.cargar_materias(),
        tipos_recurso_sugeridos=fc.TIPOS_RECURSO_SUGERIDOS,
        resultados_sugeridos=fc.RESULTADOS_SUGERIDOS, estados=fc.ESTADOS,
    )


# ── Eliminar ──────────────────────────────────────────────────────────────

@app.route("/fallos/<int:fallo_id>/eliminar", methods=["POST"])
def eliminar_fallo(fallo_id):
    fc.eliminar_fallo(fallo_id)
    return redirect(url_for("listado_fallos"))


# ── Descarga del PDF adjunto ──────────────────────────────────────────────

@app.route("/fallos/<int:fallo_id>/pdf")
def pdf_fallo(fallo_id):
    fallo = fc.obtener_fallo(fallo_id)
    if not fallo or not fallo.get("archivo_pdf"):
        abort(404)
    return send_from_directory(
        UPLOAD_DIR, fallo["archivo_pdf"],
        download_name=fallo.get("archivo_pdf_nombre") or "fallo.pdf",
    )


# ── Materias (taxonomía editable) ──────────────────────────────────────────

@app.route("/materias", methods=["GET", "POST"])
def materias():
    if request.method == "POST":
        lista = request.form.get("materias", "")
        fc.guardar_materias(lista.split("\n"))
        return redirect(url_for("materias"))
    return render_template("materias.html", active_menu="materias",
                           materias=fc.cargar_materias())


# ── Importar automáticamente desde SITCORTE ─────────────────────────────────

@app.route("/importar")
def importar_form():
    return render_template(
        "importar.html", active_menu="importar",
        materias=sorted(si.MATERIAS_COD_LIBRO), salas=sorted(si.SALAS_COD),
        resultados=sorted(si.ESTADOS_FALLO_COD), error=None, resumen=None,
        fec_desde="", fec_hasta="",
    )


@app.route("/importar/ejecutar", methods=["POST"])
def importar_ejecutar():
    usuario = request.form.get("usuario", "").strip()
    clave = request.form.get("clave", "")
    fec_desde = request.form.get("fec_desde", "").strip()
    fec_hasta = request.form.get("fec_hasta", "").strip()
    materia_sel = request.form.get("materia", "")
    sala_sel = request.form.get("sala", "")
    resultado_sel = request.form.get("resultado", "")

    ctx = dict(
        active_menu="importar",
        materias=sorted(si.MATERIAS_COD_LIBRO), salas=sorted(si.SALAS_COD),
        resultados=sorted(si.ESTADOS_FALLO_COD),
        fec_desde=fec_desde, fec_hasta=fec_hasta,
    )

    if not usuario or not clave or not fec_desde or not fec_hasta:
        return render_template("importar.html", error="Completá usuario, clave y ambas fechas.",
                               resumen=None, **ctx)

    try:
        filas = si.consultar_fallos(
            usuario, clave, fec_desde, fec_hasta,
            cod_sala=si.SALAS_COD.get(sala_sel, "0"),
            cod_libro=si.MATERIAS_COD_LIBRO.get(materia_sel, ""),
            cod_est_fallo=si.ESTADOS_FALLO_COD.get(resultado_sel, "0"),
        )
    except si.SitcorteError as e:
        return render_template("importar.html", error=str(e), resumen=None, **ctx)

    nuevos, duplicados, ids_nuevos = 0, 0, []
    for raw in filas:
        data = si.mapear_a_fallo(raw)
        fallo_id, creado = fc.importar_fallo(data)
        if creado:
            nuevos += 1
            ids_nuevos.append(fallo_id)
        else:
            duplicados += 1

    resumen = {"total": len(filas), "nuevos": nuevos, "duplicados": duplicados}
    return render_template("importar.html", error=None, resumen=resumen, **ctx)


if __name__ == "__main__":
    app.run(debug=True, port=5050)
