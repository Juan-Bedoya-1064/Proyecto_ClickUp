from flask import Blueprint, current_app, flash, g, redirect, render_template, request, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .models import Usuario
from .security import cerrar_sesion, iniciar_sesion
from .validators import validar_credenciales

bp = Blueprint("auth", __name__)

# Mensaje único para cualquier fallo de credenciales: no revela qué dato falló.
MENSAJE_GENERICO = "Identificador o contraseña incorrectos."

# Hash de relleno: se verifica cuando la cuenta no existe para igualar tiempos de respuesta.
_HASH_RELLENO = generate_password_hash("relleno-para-igualar-tiempos")


def _motivo(motivo, identificador):
    """El motivo real solo queda en el registro del servidor, nunca en la respuesta."""
    current_app.logger.info(
        "login_fallido motivo=%s identificador=%s ip=%s", motivo, identificador, request.remote_addr
    )


def autenticar(identificador: str, password: str):
    """Devuelve el Usuario si puede ingresar; si no, None (sin explicar por qué)."""
    usuario = Usuario.query.filter_by(identificador_acceso=identificador).first()

    if usuario is None:
        check_password_hash(_HASH_RELLENO, password)
        _motivo("cuenta_inexistente", identificador)
        return None
    if not usuario.check_password(password):
        _motivo("contrasena_incorrecta", identificador)
        return None
    if not usuario.activo:
        _motivo("cuenta_inactiva", identificador)
        return None
    return usuario


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.usuario is not None:
        return redirect(url_for("main.panel"))

    if request.method == "GET":
        return render_template("login.html", identificador="", errores={})

    identificador, password, errores = validar_credenciales(
        request.form.get("identificador"), request.form.get("password")
    )
    if errores:
        return render_template("login.html", identificador=identificador, errores=errores), 400

    usuario = autenticar(identificador, password)
    if usuario is None:
        return (
            render_template(
                "login.html",
                identificador=identificador,
                errores={},
                error_general=MENSAJE_GENERICO,
            ),
            401,
        )

    iniciar_sesion(usuario)
    flash(f"Hola, {usuario.nombre_completo}. Iniciaste sesión correctamente.", "ok")
    return redirect(url_for("main.panel"))


@bp.post("/logout")
def logout():
    cerrar_sesion()
    flash("Cerraste sesión. Hasta pronto.", "ok")
    return redirect(url_for("auth.login"))
