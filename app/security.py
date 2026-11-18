import hashlib
import secrets
from datetime import timedelta
from functools import wraps

from flask import current_app, flash, g, redirect, request, session, url_for

from .extensions import db
from .models import Sesion, Usuario, utcnow


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def iniciar_sesion(usuario: Usuario) -> None:
    """Crea una sesión nueva en servidor y entrega su token en la cookie firmada."""
    session.clear()  # evita fijación de sesión
    token = secrets.token_urlsafe(32)
    minutos = current_app.config["SESSION_MINUTES"]
    db.session.add(
        Sesion(
            usuario_id=usuario.id,
            token_hash=_hash(token),
            expira_en=utcnow() + timedelta(minutes=minutos),
        )
    )
    db.session.commit()
    session["sid"] = token
    session.permanent = True


def cerrar_sesion() -> None:
    """Marca la sesión como cerrada en servidor y borra la cookie."""
    if g.get("sesion") is not None:
        g.sesion.cerrada_en = utcnow()
        db.session.commit()
    session.clear()
    g.usuario = None
    g.sesion = None


def cargar_usuario():
    """before_request: resuelve el usuario a partir de la sesión del servidor."""
    g.usuario = None
    g.sesion = None
    if request.endpoint == "static":
        return
    token = session.get("sid")
    if not token:
        return

    ahora = utcnow()
    sesion = Sesion.query.filter_by(token_hash=_hash(token)).first()
    if sesion is None or sesion.cerrada_en or sesion.expira_en <= ahora:
        session.clear()
        return

    usuario = db.session.get(Usuario, sesion.usuario_id)
    if usuario is None or not usuario.activo:
        # Si la cuenta se desactiva, la sesión abierta deja de servir.
        sesion.cerrada_en = ahora
        db.session.commit()
        session.clear()
        return

    # Expiración por inactividad: se renueva si pasó más de un minuto.
    duracion = timedelta(minutes=current_app.config["SESSION_MINUTES"])
    if sesion.expira_en - ahora < duracion - timedelta(minutes=1):
        sesion.expira_en = ahora + duracion
        db.session.commit()

    g.usuario = usuario
    g.sesion = sesion


def cabeceras_seguras(respuesta):
    if request.endpoint != "static":
        # Evita que el botón "atrás" muestre páginas protegidas tras cerrar sesión.
        respuesta.headers["Cache-Control"] = "no-store"
    respuesta.headers["X-Content-Type-Options"] = "nosniff"
    respuesta.headers["X-Frame-Options"] = "DENY"
    respuesta.headers["Referrer-Policy"] = "same-origin"
    respuesta.headers["Content-Security-Policy"] = (
        "default-src 'self'; form-action 'self'; frame-ancestors 'none'"
    )
    return respuesta


def login_required(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if g.usuario is None:
            flash("Inicia sesión para continuar.", "info")
            return redirect(url_for("auth.login"))
        return vista(*args, **kwargs)

    return envoltura
