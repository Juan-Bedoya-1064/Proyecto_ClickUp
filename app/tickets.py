from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from .autorizacion import (
    PERMISO_POR_TIPO,
    permiso_required,
    puede_editar,
    ticket_editable_o_error,
    ticket_visible_o_404,
    tiene_permiso,
)
from .consulta import consultar_tickets
from .extensions import db
from .models import TIPOS_PARTICIPACION, ParticipacionTicket, Ticket, Usuario
from .security import login_required
from .validators import validar_titulo

bp = Blueprint("tickets", __name__, url_prefix="/tickets")


@bp.get("")
@login_required
@permiso_required("tickets.ver")
def lista():
    # Sprint 2 · HU-06: autorización + filtros (ver app/consulta.py)
    datos = consultar_tickets(g.usuario, request.args)
    mis_tipos = {}
    for p in ParticipacionTicket.query.filter_by(usuario_id=g.usuario.id):
        mis_tipos.setdefault(p.ticket_id, []).append(p.tipo_participacion)
    return render_template("ticket_lista.html", mis_tipos=mis_tipos, **datos)


# El alta de tickets se hace en app/registro.py (HU-05): /tickets/registrar


def _render_detalle(ticket, estado=200, error=None):
    puede_asignar = tiene_permiso(g.usuario, "tickets.asignar")
    candidatos = (
        Usuario.query.filter_by(activo=True).order_by(Usuario.nombre_completo).all()
        if puede_asignar
        else []
    )
    return (
        render_template(
            "ticket_detalle.html",
            ticket=ticket,
            puede_editar=puede_editar(g.usuario, ticket),
            puede_asignar=puede_asignar,
            candidatos=candidatos,
            tipos=TIPOS_PARTICIPACION,
            error=error,
        ),
        estado,
    )


@bp.get("/<int:ticket_id>")
@login_required
@permiso_required("tickets.ver")
def detalle(ticket_id):
    return _render_detalle(ticket_visible_o_404(ticket_id))


@bp.route("/<int:ticket_id>/editar", methods=["GET", "POST"])
@login_required
@permiso_required("tickets.editar")
def editar(ticket_id):
    ticket = ticket_editable_o_error(ticket_id)
    if request.method == "GET":
        return render_template(
            "ticket_form.html", titulo_pagina=f"Editar ticket #{ticket.id}", titulo=ticket.titulo, error=None
        )

    titulo, error = validar_titulo(request.form.get("titulo"))
    if error:
        return (
            render_template(
                "ticket_form.html", titulo_pagina=f"Editar ticket #{ticket.id}", titulo=titulo, error=error
            ),
            400,
        )
    ticket.titulo = titulo
    db.session.commit()
    flash("Ticket actualizado.", "ok")
    return redirect(url_for("tickets.detalle", ticket_id=ticket.id))


@bp.post("/<int:ticket_id>/participantes")
@login_required
@permiso_required("tickets.asignar")
def asignar(ticket_id):
    ticket = ticket_visible_o_404(ticket_id)
    tipo = request.form.get("tipo_participacion", "")
    usuario = db.session.get(Usuario, request.form.get("usuario_id", type=int) or 0)

    if tipo not in TIPOS_PARTICIPACION:
        return _render_detalle(ticket, 400, "Elige un tipo de participación válido.")
    if usuario is None or not usuario.activo:
        return _render_detalle(ticket, 400, "Elige una persona con cuenta activa.")
    if not tiene_permiso(usuario, PERMISO_POR_TIPO[tipo]):
        return _render_detalle(ticket, 400, "El rol de esa persona no permite esa participación.")

    ticket.participaciones.append(
        ParticipacionTicket(usuario_id=usuario.id, tipo_participacion=tipo)
    )
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return _render_detalle(ticket, 409, "Esa persona ya participa en el ticket con ese tipo.")
    flash(f"{usuario.nombre_completo} se agregó como {tipo}.", "ok")
    return redirect(url_for("tickets.detalle", ticket_id=ticket.id))
