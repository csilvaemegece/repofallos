# -*- coding: utf-8 -*-
"""
Importador automático desde SITCORTE-REG: informe "Recursos Fallados"
(InformesViewAccion.do?TipMenuINF=2, irAccion="Consulta Fallos").

A diferencia de "Recursos en Acuerdo" (que sitcorte_web ya usa para causas
PENDIENTES), este informe lista causas YA FALLADAS con metadata completa:
rol, carátula, sala, ministro redactor, tipo de recurso, resultado
("Estado Fallo"), fecha del fallo, tribunal de origen, etc. No incluye el
texto de la sentencia — eso sigue siendo carga manual (pegar texto o PDF).

Descubierto a partir de un HAR real capturado navegando SITCORTE. Flujo:
1. Login (idéntico al de sitcorte_core.py del proyecto sitcorte_web).
2. GET del formulario del informe (establece contexto de sesión JSP).
3. POST a InformesDAction.do con COD_Sala/FEC_Desde/FEC_Hasta/COD_Libro/
   COD_EstFallo/irAccion="Consulta Fallos" (sin token CSRF: este formulario
   no lo pide, a diferencia de "Consulta Acd.").
4. El HTML de respuesta trae la tabla de detalle embebida dos veces: como
   <TD> visibles y como llamadas JS `new Informe(23 campos)` (usadas por
   SITCORTE para su propio Excel/orden). Parseamos las filas <TD> directo,
   que es más simple y no depende de JS.
"""
import re

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HOST = "https://sitcorte-reg.pjud.cl"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36")

URL_LOGIN_PAGE   = HOST + "/SITCORTEWEB/jsp/Login/Login.jsp"
URL_LOGIN_ACTION = HOST + "/SITCORTEWEB/InicioAplicacion.do"
URL_MENU_FALLO   = HOST + "/SITCORTEWEB/InformesViewAccion.do?TipMenuINF=2"
URL_FORM_POST    = HOST + "/SITCORTEWEB/InformesDAction.do"
URL_MENU_TRAMITAR = HOST + "/SITCORTEWEB/TramitacionViewAccion.do?TipMenuTrm=1"
URL_CONSULTA_ROL   = HOST + "/SITCORTEWEB/ConsultaRolTramitarAccion.do"

TOKEN_RE = re.compile(
    r'name="org\.apache\.struts\.taglib\.html\.TOKEN"\s+value="([^"]+)"')

# Catálogos reales tal como los expone el combo del informe (útiles para
# ofrecer filtros opcionales al importar; "" / "0" = todas/todos).
MATERIAS_COD_LIBRO = {
    "Civil": "28",
    "Familia": "29",
    "Laboral - Cobranza": "30",
    "Penal": "31",
    "Contencioso Administrativo": "32",
    "Tributario Y Aduanero": "33",
    "Protección": "34",
    "Amparo": "35",
    "Policia Local": "36",
    "Exhorto": "37",
    "Ley De Navegación": "38",
    "Ambiental": "39",
    "Traspaso Corte Marcial": "40",
    "Ministro Primera Instancia Y Fuero": "41",
    "Com. Lib. Cond.": "42",
    "Pleno Y Otros Adm": "9",
}

SALAS_COD = {
    "Primera": "1", "Segunda": "2", "Tercera": "3", "Cuarta": "4",
    "De Turno": "8", "de Verano": "15", "Secretaria": "50", "Pleno": "59",
    "Ministro": "60", "Relator": "63", "Presidencia Pleno": "75",
    "Com. Lib. Cond.": "76", "Presidencia": "91", "Fiscalía": "95",
    "Cuenta": "99",
}

ESTADOS_FALLO_COD = {
    "Confirma": "1", "Revoca": "2", "Aprueba": "3", "Admisibilidad": "4",
    "Resuelta": "5", "Fallado": "6", "C.Mod.Fallo 1ªInst.": "7",
    "C.Fallo. con 3 Consi": "8", "Acogida": "9", "Rechazada": "10",
    "Abandonado": "11",
}

# Orden real de las 23 columnas del informe (mismo orden que los <TD>).
CAMPOS_DETALLE = [
    "Recurso", "Secretaria", "Tipo Fallo", "Fecha Acuerdo",
    "Ministro Redactor", "Fecha Ing.", "Tipo Recurso", "Fecha Proyecto",
    "Fecha Fallo", "Estado Fallo", "Folio", "Sala", "Nomenclatura",
    "Ministro 1", "Ministro 2", "Ministro 3", "Fecha.Ubi", "Ubicacion",
    "Fecha.Proc", "Est.Procesal", "Caratulado", "RIT 1ra Inst.",
    "Trib. 1ra Inst.",
]


class SitcorteError(Exception):
    """Error de negocio (login fallido, sin datos, etc.) para mostrar al usuario."""


def crear_sesion():
    s = requests.Session()
    s.trust_env = False
    s.verify = False
    s.headers.update({
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,*/*",
    })
    return s


def login(s, usuario, clave):
    try:
        r_page = s.get(URL_LOGIN_PAGE, timeout=30)
    except requests.RequestException as e:
        raise SitcorteError(f"No se pudo abrir la página de login: {e}")

    m = TOKEN_RE.search(r_page.text)
    token = m.group(1) if m else ""

    data = {
        "org.apache.struts.taglib.html.TOKEN": token,
        "username": usuario,
        "password": clave,
        "Aceptar": "Aceptar",
        "Cancelar": "",
        "AbrirIntra": "",
    }
    try:
        r = s.post(URL_LOGIN_ACTION, data=data, timeout=30)
    except requests.RequestException as e:
        raise SitcorteError(f"Falló el POST de login: {e}")

    bajo = r.text.lower()
    if ("manejo de errores" in bajo or "nullpointerexception" in bajo
            or "problema de sistema" in bajo):
        raise SitcorteError("Error de sistema del servidor SITCORTE en el login.")
    if ('name="username"' in bajo or "login.jsp" in r.url.lower()
            or "usuario o contrase" in bajo):
        raise SitcorteError("Usuario o contraseña incorrectos.")

    return True


def _extraer_detalle(html_texto):
    """Extrae la tabla de detalle (id='contentCellsDetalle') como lista de
    dicts con las 23 columnas reales del informe."""
    inicio = html_texto.find("id='contentCellsDetalle'")
    if inicio == -1:
        return []
    fin = html_texto.find("</tbody>    </table>", inicio)
    bloque = html_texto[inicio: fin if fin != -1 else None]

    filas = []
    for fila_html in re.findall(r'<tr class="texto">(.*?)</tr>', bloque, re.S):
        celdas = re.findall(r'<TD[^>]*>(.*?)</TD>', fila_html, re.S)
        celdas = [re.sub(r'\s+', ' ', c).strip() for c in celdas]
        if len(celdas) != len(CAMPOS_DETALLE):
            continue
        filas.append(dict(zip(CAMPOS_DETALLE, celdas)))
    return filas


def crear_sesion_logueada(usuario, clave):
    """Login que devuelve la sesión ya autenticada, para reusarla en varias
    consultas seguidas (ej. importar N causas + traer el PDF de cada una)
    sin loguearse de nuevo por cada una."""
    s = crear_sesion()
    login(s, usuario, clave)
    return s


def consultar_fallos_con_sesion(s, fec_desde, fec_hasta,
                                 cod_sala="0", cod_libro="", cod_est_fallo="0"):
    """Igual que consultar_fallos() pero reusando una sesión ya logueada."""
    try:
        s.get(URL_MENU_FALLO, timeout=30)
    except requests.RequestException as e:
        raise SitcorteError(f"Error al cargar el formulario de Fallos: {e}")

    data = {
        "COD_Sala": cod_sala or "0",
        "FEC_Desde": fec_desde,
        "FEC_Hasta": fec_hasta,
        "irAccion": "Consulta Fallos",
        "COD_Libro": cod_libro or "",
        "COD_EstFallo": cod_est_fallo or "0",
    }
    try:
        r_post = s.post(URL_FORM_POST, data=data, timeout=90)
    except requests.RequestException as e:
        raise SitcorteError(f"Error en POST Consulta Fallos: {e}")

    if "usuario o contrase" in r_post.text.lower():
        raise SitcorteError("La sesión de SITCORTE expiró durante la consulta.")

    return _extraer_detalle(r_post.text)


def consultar_fallos(usuario, clave, fec_desde, fec_hasta,
                      cod_sala="0", cod_libro="", cod_est_fallo="0"):
    """Login + consulta del informe "Recursos Fallados". Devuelve una lista
    de dicts (uno por causa fallada) con las columnas crudas del informe."""
    s = crear_sesion_logueada(usuario, clave)
    return consultar_fallos_con_sesion(s, fec_desde, fec_hasta, cod_sala, cod_libro, cod_est_fallo)


# ── Mapeo SITCORTE -> esquema de fallos_core ────────────────────────────────

def _vacio(v):
    v = (v or "").strip()
    return "" if v in ("", "--", "- -") else v


def _fecha_iso(v):
    v = _vacio(v)
    if not v:
        return ""
    partes = v.split("/")
    if len(partes) != 3:
        return ""
    d, m, y = partes
    if len(y) != 4 or not y.isdigit():
        return ""
    return f"{y}-{m.zfill(2)}-{d.zfill(2)}"


def _split_recurso(recurso):
    """'Penal-818-2026' -> ('Penal', '818-2026'); 'Laboral - Cobranza-45-2026'
    -> ('Laboral - Cobranza', '45-2026') (split desde la derecha, los
    últimos dos tramos son siempre número y año)."""
    recurso = _vacio(recurso)
    partes = recurso.rsplit("-", 2)
    if len(partes) == 3:
        materia, numero, anio = partes
        return materia.strip(), f"{numero.strip()}-{anio.strip()}"
    return "", recurso


# ── Búsqueda del PDF de la sentencia a partir del ROL ───────────────────────
#
# Descubierto a partir de un segundo HAR: la ficha de tramitación de una
# causa (ConsultaRolTramitarAccion.do, consultada por Libro+Rol+Año) trae
# el expediente completo (escritos, resoluciones, actuaciones y fallos).
# La fila cuyo "Tipo" de trámite es literalmente "Sentencia" es el fallo;
# su ícono de PDF apunta a DownloadFile.do?...&CRR_IdTramite=X&CRR_IdDocumento=Y,
# que se puede pedir directo con la misma sesión logueada (window.open sin
# más, sin token adicional).

def _extraer_url_pdf_sentencia(html_texto):
    """Busca, entre las filas de trámite del expediente, la que corresponde
    al fallo (Tipo == "Sentencia") y devuelve la URL relativa de su PDF, o
    None si no se encontró (causa sin fallo aún, o con otra nomenclatura)."""
    filas = re.split(r'(?=<TR class="texto" id="\d+")', html_texto)
    for fila in filas:
        if "ShowPDFEscrito" not in fila:
            continue
        tds = [re.sub(r"\s+", " ", t).strip()
               for t in re.findall(r"<TD[^>]*>(.*?)</TD>", fila, re.S)]
        if "Sentencia" not in tds:
            continue
        m = re.search(r"ShowPDFEscrito\('([^']+)'\)", fila)
        if m:
            return m.group(1)
    return None


def obtener_pdf_fallo_con_sesion(s, cod_libro, rol_recurso, era_recurso):
    """Igual que obtener_pdf_fallo() pero reusando una sesión ya logueada
    (para no volver a loguearse por cada causa al enriquecer una importación
    masiva)."""
    try:
        s.get(URL_MENU_TRAMITAR, timeout=30)
    except requests.RequestException:
        pass  # priming de sesión; si falla igual intentamos el POST

    data = {
        "TIP_Tramitacion": "1",
        "COD_Libro": str(cod_libro),
        "ROL_Recurso": str(rol_recurso),
        "ERA_Recurso": str(era_recurso),
        "ERA_RecursoCombo": str(era_recurso),
        "libro": "",
        "era": "",
        "ERA_RecursoAntiguo": "",
    }
    try:
        r_post = s.post(URL_CONSULTA_ROL, data=data, timeout=60)
    except requests.RequestException as e:
        raise SitcorteError(f"Error al consultar la tramitación de la causa: {e}")

    if "usuario o contrase" in r_post.text.lower():
        raise SitcorteError("La sesión de SITCORTE expiró durante la consulta.")

    url_pdf = _extraer_url_pdf_sentencia(r_post.text)
    if not url_pdf:
        raise SitcorteError(
            "No se encontró un trámite de tipo 'Sentencia' en el expediente "
            "de esta causa (puede que aún no esté fallada, o que la causa/"
            "materia/rol/año no coincida con la registrada).")

    if not url_pdf.startswith("http"):
        url_pdf = HOST + url_pdf

    try:
        r_pdf = s.get(url_pdf, timeout=60)
    except requests.RequestException as e:
        raise SitcorteError(f"Error al descargar el PDF de la sentencia: {e}")

    content_type = r_pdf.headers.get("Content-Type", "")
    if r_pdf.status_code != 200 or "pdf" not in content_type.lower():
        raise SitcorteError(
            f"La descarga no devolvió un PDF (HTTP {r_pdf.status_code}, "
            f"Content-Type: {content_type}).")

    nombre = f"sentencia_{cod_libro}-{rol_recurso}-{era_recurso}.pdf"
    return r_pdf.content, nombre


def obtener_pdf_fallo(usuario, clave, cod_libro, rol_recurso, era_recurso):
    """Login + obtener_pdf_fallo_con_sesion(), para uso puntual (un solo
    fallo, ej. el botón "Buscar PDF en SITCORTE" de la ficha)."""
    s = crear_sesion_logueada(usuario, clave)
    return obtener_pdf_fallo_con_sesion(s, cod_libro, rol_recurso, era_recurso)


def mapear_a_fallo(raw):
    """Convierte una fila cruda del informe SITCORTE al dict de campos que
    espera fallos_core (crear_fallo/importar_fallo)."""
    materia, rol = _split_recurso(raw.get("Recurso", ""))
    est_procesal = _vacio(raw.get("Est.Procesal", ""))
    trib_origen = _vacio(raw.get("Trib. 1ra Inst.", ""))
    rit_origen = _vacio(raw.get("RIT 1ra Inst.", ""))

    notas = ["[Auto-importado de SITCORTE — pendiente de completar el resumen de la causa.]"]
    if est_procesal:
        notas.append(f"Estado procesal: {est_procesal}.")
    if trib_origen:
        notas.append(f"Tribunal de origen: {trib_origen}" +
                      (f" (RIT {rit_origen})" if rit_origen else "") + ".")

    return {
        "rol": rol,
        "caratula": _vacio(raw.get("Caratulado", "")),
        "sala": _vacio(raw.get("Sala", "")),
        "ministro_redactor": _vacio(raw.get("Ministro Redactor", "")),
        "materia": materia,
        "tipo_recurso": _vacio(raw.get("Tipo Recurso", "")),
        "resultado": _vacio(raw.get("Estado Fallo", "")),
        "tags": "",
        "resumen": " ".join(notas),
        "texto_fallo": "",
        "archivo_pdf": "",
        "archivo_pdf_nombre": "",
        "fecha_fallo": _fecha_iso(raw.get("Fecha Fallo", "")),
        "estado": "borrador",
        "clave_sitcorte": _vacio(raw.get("Folio", "")) or _vacio(raw.get("Recurso", "")),
    }
