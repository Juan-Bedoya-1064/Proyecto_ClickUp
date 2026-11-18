"""HU-05 · Registro de una solicitud de mantenimiento (ticket) sobre un equipo.

Reglas:
  - Solo se registra sobre un equipo ACTIVO y una categoría activa.
  - Todos los campos son obligatorios, menos la evidencia.
  - El folio (ej. TK-2026-00004) se arma con el año y el id del ticket: como el id no
    se repite, el folio tampoco. Se guarda en la base y no vuelve a cambiar.
  - El solicitante es quien tiene la sesión abierta (no se puede elegir a otra persona).
  - La fecha de registro la pone el servidor.

Seguridad de la evidencia:
  - Solo JPG, PNG o PDF, y de máximo 10 MB.
  - Se revisa el contenido real del archivo, no solo la extensión.
  - Se guarda fuera de la carpeta pública, con un nombre aleatorio.
  - Solo la descarga quien puede ver el ticket, y siempre como archivo adjunto.
"""
import os
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)

from .autorizacion import permiso_required, ticket_visible_o_404
from .extensions import db
from .models import (
    PRIORIDADES,
    AdjuntoTicket,
    CategoriaServicio,
    Equipo,
    ParticipacionTicket,
    SolicitudMantenimiento,
    Ticket,
)
from .security import login_required
from .validators import (
    validar_detector,
    validar_evidencia,
    validar_fecha_deteccion,
    validar_situacion,
    validar_titulo,
)

bp = Blueprint("registro", __name__, url_prefix="/tickets")


def hoy_local():
    """Fecha de hoy en la zona horaria configurada (por defecto Colombia)."""
    return datetime.now(ZoneInfo(current_app.config["ZONA_HORARIA"])).date()


def guardar_archivo(datos, extension):
    """Guarda la evidencia en disco con un nombre aleatorio y devuelve ese nombre."""
    carpeta = current_app.config["CARPETA_ADJUNTOS"]
    os.makedirs(carpeta, exist_ok=True)
    nombre = uuid.uuid4().hex + "." + extension
    with open(os.path.join(carpeta, nombre), "wb") as archivo:
        archivo.write(datos)
    return nombre


@bp.route("/registrar", methods=["GET", "POST"])
@login_required
@permiso_required("tickets.crear")
def registrar():
    equipos = Equipo.query.filter_by(activo=True).order_by(Equipo.codigo).all()
    categorias = CategoriaServicio.query.filter_by(activo=True).order_by(CategoriaServicio.nombre).all()
    hoy = hoy_local()
    datos = {
        "titulo": "",
        "equipo_id": None,
        "categoria_id": None,
        "prioridad": "",
        "situacion": "",
        "detectado_por": g.usuario.nombre_completo,
        "fecha_deteccion": hoy.isoformat(),
    }
    errores = {}

    if request.method == "POST":
        datos["titulo"], error = validar_titulo(request.form.get("titulo"))
        if error:
            errores["titulo"] = error

        datos["equipo_id"] = request.form.get("equipo_id", type=int)
        if datos["equipo_id"] not in [e.id for e in equipos]:
            errores["equipo_id"] = "Elige un equipo activo."

        datos["categoria_id"] = request.form.get("categoria_id", type=int)
        if datos["categoria_id"] not in [c.id for c in categorias]:
            errores["categoria_id"] = "Elige una categoría."

        datos["prioridad"] = request.form.get("prioridad", "")
        if datos["prioridad"] not in PRIORIDADES:
            errores["prioridad"] = "Elige una prioridad."

        datos["situacion"], error = validar_situacion(request.form.get("situacion"))
        if error:
            errores["situacion"] = error

        datos["detectado_por"], error = validar_detector(request.form.get("detectado_por"))
        if error:
            errores["detectado_por"] = error

        datos["fecha_deteccion"] = (request.form.get("fecha_deteccion") or "").strip()
        fecha, error = validar_fecha_deteccion(datos["fecha_deteccion"], hoy)
        if error:
            errores["fecha_deteccion"] = error

        # La evidencia es opcional: solo se valida si la persona eligió un archivo.
        archivo = request.files.get("evidencia")
        contenido, extension = None, None
        if archivo is not None and archivo.filename:
            contenido = archivo.read()
            extension, error = validar_evidencia(archivo.filename, contenido)
            if error:
                errores["evidencia"] = error

        if not errores:
            ticket = Ticket(titulo=datos["titulo"])
            ticket.participaciones.append(
                ParticipacionTicket(usuario_id=g.usuario.id, tipo_participacion="solicitante")
            )
            db.session.add(ticket)
            db.session.flush()  # la base asigna el id del ticket; con él se arma el folio

            solicitud = SolicitudMantenimiento(
                ticket_id=ticket.id,
                folio=f"TK-{ticket.creado_en.year}-{ticket.id:05d}",
                equipo_id=datos["equipo_id"],
                categoria_id=datos["categoria_id"],
                prioridad=datos["prioridad"],
                situacion=datos["situacion"],
                detectado_por=datos["detectado_por"],
                fecha_deteccion=fecha,
            )
            db.session.add(solicitud)

            if contenido is not None:
                db.session.add(
                    AdjuntoTicket(
                        ticket_id=ticket.id,
                        nombre_original=os.path.basename(archivo.filename.replace("\\", "/"))[:255],
                        nombre_guardado=guardar_archivo(contenido, extension),
                        tamano_bytes=len(contenido),
                        subido_por_id=g.usuario.id,
                    )
                )
            db.session.commit()
            flash(f"Ticket registrado con el folio {solicitud.folio}. Guárdalo para consultarlo.", "ok")
            return redirect(url_for("tickets.detalle", ticket_id=ticket.id))

    return (
        render_template(
            "ticket_registro.html",
            datos=datos,
            errores=errores,
            equipos=equipos,
            categorias=categorias,
            prioridades=PRIORIDADES,
            hoy=hoy.isoformat(),
        ),
        400 if errores else 200,
    )


@bp.get("/<int:ticket_id>/adjuntos/<int:adjunto_id>")
@login_required
@permiso_required("tickets.ver")
def descargar_adjunto(ticket_id, adjunto_id):
    ticket = ticket_visible_o_404(ticket_id)
    adjunto = db.session.get(AdjuntoTicket, adjunto_id)
    if adjunto is None or adjunto.ticket_id != ticket.id:
        abort(404)
    return send_from_directory(
        current_app.config["CARPETA_ADJUNTOS"],
        adjunto.nombre_guardado,
        as_attachment=True,  # se descarga; el navegador no lo abre como página
        download_name=adjunto.nombre_original,
    )
