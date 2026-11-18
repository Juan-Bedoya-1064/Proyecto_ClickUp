"""HU-02 · Control de acceso por rol (permisos) y participación en el ticket.

Una sola capa decide todo, y se usa en cada ruta (también en acceso directo por URL):

  1. PERMISO del rol  -> ¿el rol permite esta *clase* de acción?      (si no: 403)
  2. ALCANCE          -> ¿puede hacerlo sobre *este* ticket?           (si no: 404)
                         Un administrador ve todo; los demás solo los tickets donde participan.
  3. Edición          -> además exige ser *responsable* del ticket (o administrador).  (si no: 403)

Se responde 404 (y no 403) cuando el ticket no es visible para la persona, así no se
revela si existe. Todas las comprobaciones ocurren ANTES de escribir en la base de datos.
"""
from functools import wraps

from flask import abort, g

from .extensions import db
from .models import ParticipacionTicket, Ticket

# Permiso que debe tener el rol de una persona para ser asignada con cada tipo de participación.
PERMISO_POR_TIPO = {"solicitante": "tickets.crear", "responsable": "tickets.editar"}


def tiene_permiso(usuario, codigo: str) -> bool:
    return usuario is not None and codigo in usuario.codigos_permiso()


def participa(usuario, ticket, tipo=None) -> bool:
    consulta = ParticipacionTicket.query.filter_by(ticket_id=ticket.id, usuario_id=usuario.id)
    if tipo:
        consulta = consulta.filter_by(tipo_participacion=tipo)
    return db.session.query(consulta.exists()).scalar()


def puede_ver(usuario, ticket) -> bool:
    return tiene_permiso(usuario, "tickets.ver") and (
        tiene_permiso(usuario, "tickets.ver_todos") or participa(usuario, ticket)
    )


def puede_editar(usuario, ticket) -> bool:
    return tiene_permiso(usuario, "tickets.editar") and (
        tiene_permiso(usuario, "tickets.editar_todos")
        or participa(usuario, ticket, "responsable")
    )


def permiso_required(codigo: str):
    """Rechaza (403) si el rol de la persona no tiene el permiso."""

    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            if not tiene_permiso(g.usuario, codigo):
                abort(403)
            return vista(*args, **kwargs)

        return envoltura

    return decorador


def ticket_visible_o_404(ticket_id: int) -> Ticket:
    ticket = db.session.get(Ticket, ticket_id)
    if ticket is None or not puede_ver(g.usuario, ticket):
        abort(404)  # misma respuesta si no existe o si no es visible para esta persona
    return ticket


def ticket_editable_o_error(ticket_id: int) -> Ticket:
    ticket = ticket_visible_o_404(ticket_id)
    if not puede_editar(g.usuario, ticket):
        abort(403)
    return ticket
