import logging
from datetime import timedelta, timezone
from zoneinfo import ZoneInfo

from flask import Flask, g, render_template
from flask_wtf.csrf import CSRFError

from .config import Config
from .extensions import csrf, db


def _registrar_errores(app):
    def manejador(codigo, titulo, detalle):
        def _h(_error):
            return render_template(
                "error.html", codigo=codigo, titulo=titulo, detalle=detalle
            ), codigo

        return _h

    app.register_error_handler(403, manejador(403, "Acceso denegado", "Tu rol no permite esta acción."))
    app.register_error_handler(404, manejador(404, "Página no encontrada", "No existe o no tienes acceso a este recurso."))
    app.register_error_handler(405, manejador(405, "Acción no permitida", "Esta dirección no acepta ese tipo de solicitud."))
    app.register_error_handler(413, manejador(413, "Archivo demasiado grande", "El tamaño máximo permitido es 10 MB."))
    app.register_error_handler(CSRFError, manejador(400, "Solicitud no válida", "El formulario expiró o no es válido. Vuelve a cargar la página e inténtalo de nuevo."))


def create_app(config_object=None):
    app = Flask(__name__)
    app.config.from_object(config_object or Config)
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=app.config["SESSION_MINUTES"])

    app.logger.setLevel(logging.INFO)
    db.init_app(app)
    csrf.init_app(app)

    from .security import cabeceras_seguras, cargar_usuario

    app.before_request(cargar_usuario)
    app.after_request(cabeceras_seguras)

    from .auth import bp as auth_bp
    from .main import bp as main_bp
    from .tickets import bp as tickets_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(tickets_bp)

    # Sprint 2 · HU-04
    from .catalogos import bp as catalogos_bp
    from .equipos import bp as equipos_bp

    app.register_blueprint(catalogos_bp)
    app.register_blueprint(equipos_bp)

    # Sprint 2 · HU-05
    from .registro import bp as registro_bp

    app.register_blueprint(registro_bp)

    @app.context_processor
    def contexto():
        from .autorizacion import tiene_permiso
        from .models import ESTADOS, PRIORIDADES

        usuario = g.get("usuario")
        return {
            "usuario_actual": usuario,
            "puede": lambda codigo: tiene_permiso(usuario, codigo),
            "prioridades": PRIORIDADES,  # Sprint 2 · HU-05
            "estados": ESTADOS,  # Sprint 2 · HU-06
        }

    zona = ZoneInfo(app.config["ZONA_HORARIA"])

    @app.template_filter("hora_local")
    def hora_local(valor, formato="%d/%m/%Y %I:%M %p"):
        """Convierte un DATETIME guardado en UTC a la hora local (por defecto Colombia)."""
        if valor is None:
            return ""
        local = valor.replace(tzinfo=timezone.utc).astimezone(zona)
        return local.strftime(formato).replace("AM", "a. m.").replace("PM", "p. m.")

    _registrar_errores(app)

    from .cli import registrar_comandos

    registrar_comandos(app)
    return app
