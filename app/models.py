"""Modelos alineados 1:1 con db/schema.sql (diagrama relacional del equipo)."""
from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db

TIPOS_PARTICIPACION = ("solicitante", "responsable")


def utcnow():
    """Fecha/hora UTC sin zona y sin microsegundos (portable entre MySQL y SQLite).

    MySQL guarda DATETIME sin fracciones de segundo; se recortan aquí para que
    el valor en memoria y el guardado sean idénticos.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


# Opciones de tabla para MySQL/MariaDB (otros motores las ignoran).
MYSQL = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_unicode_ci",
}


def _pk():
    return db.Column(db.Integer, primary_key=True, autoincrement=True)  # AUTO_INCREMENT


roles_permisos = db.Table(
    "roles_permisos",
    db.Column("rol_id", db.Integer, db.ForeignKey("roles.id"), primary_key=True),
    db.Column("permiso_id", db.Integer, db.ForeignKey("permisos.id"), primary_key=True),
    **MYSQL,
)


class Rol(db.Model):
    __tablename__ = "roles"
    __table_args__ = MYSQL

    id = _pk()
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.String(255))

    permisos = db.relationship("Permiso", secondary=roles_permisos, order_by="Permiso.codigo")


class Permiso(db.Model):
    __tablename__ = "permisos"
    __table_args__ = MYSQL

    id = _pk()
    codigo = db.Column(db.String(100), unique=True, nullable=False)
    descripcion = db.Column(db.String(255))


class Usuario(db.Model):
    __tablename__ = "usuarios"
    __table_args__ = MYSQL

    id = _pk()
    identificador_acceso = db.Column(db.String(100), unique=True, nullable=False)
    contrasena_hash = db.Column(db.String(255), nullable=False)
    nombre_completo = db.Column(db.String(150), nullable=False)
    correo = db.Column(db.String(150))
    rol_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=utcnow)
    actualizado_en = db.Column(db.DateTime)

    rol = db.relationship("Rol")

    def set_password(self, clave: str) -> None:
        self.contrasena_hash = generate_password_hash(clave)

    def check_password(self, clave: str) -> bool:
        return check_password_hash(self.contrasena_hash, clave)

    def codigos_permiso(self) -> set:
        return {p.codigo for p in self.rol.permisos}


class Ticket(db.Model):
    __tablename__ = "tickets"
    __table_args__ = MYSQL

    id = _pk()
    titulo = db.Column(db.String(200), nullable=False)
    creado_en = db.Column(db.DateTime, nullable=False, default=utcnow)

    participaciones = db.relationship(
        "ParticipacionTicket", back_populates="ticket", order_by="ParticipacionTicket.id"
    )


class ParticipacionTicket(db.Model):
    __tablename__ = "participaciones_ticket"
    __table_args__ = (
        db.UniqueConstraint("ticket_id", "usuario_id", "tipo_participacion", name="uq_participacion"),
        MYSQL,
    )

    id = _pk()
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    tipo_participacion = db.Column(db.String(30), nullable=False)

    ticket = db.relationship("Ticket", back_populates="participaciones")
    usuario = db.relationship("Usuario")


class Sesion(db.Model):
    """Sesión del lado del servidor: `cerrada_en` con valor = ya no da acceso."""

    __tablename__ = "sesiones"
    __table_args__ = MYSQL

    id = _pk()
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    token_hash = db.Column(db.String(255), unique=True, nullable=False)  # SHA-256 del token
    iniciada_en = db.Column(db.DateTime, nullable=False, default=utcnow)
    expira_en = db.Column(db.DateTime, nullable=False)
    cerrada_en = db.Column(db.DateTime)

    usuario = db.relationship("Usuario")


# ---------------------------------------------------------------------------
# Sprint 2 · HU-04 Catálogos y equipos
# Ningún valor se borra: se desactiva (activo = False). Así los equipos que ya
# lo usan conservan la referencia histórica.
# ---------------------------------------------------------------------------
class TipoEquipo(db.Model):
    __tablename__ = "tipos_equipo"
    __table_args__ = MYSQL

    id = _pk()
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    # Cada cuántos meses se hace mantenimiento preventivo. NULL = no aplica.
    periodicidad_meses = db.Column(db.Integer)
    activo = db.Column(db.Boolean, nullable=False, default=True)


class Ubicacion(db.Model):
    __tablename__ = "ubicaciones"
    __table_args__ = MYSQL

    id = _pk()
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    activo = db.Column(db.Boolean, nullable=False, default=True)


class CategoriaServicio(db.Model):
    __tablename__ = "categorias_servicio"
    __table_args__ = MYSQL

    id = _pk()
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    activo = db.Column(db.Boolean, nullable=False, default=True)


class Equipo(db.Model):
    __tablename__ = "equipos"
    __table_args__ = MYSQL

    id = _pk()
    codigo = db.Column(db.String(30), unique=True, nullable=False)  # código de inventario
    nombre = db.Column(db.String(150), nullable=False)
    tipo_id = db.Column(db.Integer, db.ForeignKey("tipos_equipo.id"), nullable=False)
    ubicacion_id = db.Column(db.Integer, db.ForeignKey("ubicaciones.id"), nullable=False)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=utcnow)

    tipo = db.relationship("TipoEquipo")
    ubicacion = db.relationship("Ubicacion")


# ---------------------------------------------------------------------------
# Sprint 2 · HU-05 Registro de ticket
# La tabla `tickets` del sprint 1 no se modifica. Los datos de la solicitud de
# mantenimiento van en una tabla aparte, unida 1 a 1 con el ticket.
# ---------------------------------------------------------------------------
PRIORIDADES = {"baja": "Baja", "media": "Media", "alta": "Alta", "critica": "Crítica"}
# HU-06: estado del ticket. Todo ticket nace «abierto».
ESTADOS = {"abierto": "Abierto", "en_proceso": "En proceso", "resuelto": "Resuelto", "cerrado": "Cerrado"}


class SolicitudMantenimiento(db.Model):
    __tablename__ = "solicitudes_mantenimiento"
    __table_args__ = MYSQL

    id = _pk()
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), unique=True, nullable=False)
    folio = db.Column(db.String(20), unique=True, nullable=False)  # ej. TK-2026-00004
    equipo_id = db.Column(db.Integer, db.ForeignKey("equipos.id"), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey("categorias_servicio.id"), nullable=False)
    prioridad = db.Column(db.String(10), nullable=False)
    situacion = db.Column(db.Text, nullable=False)  # qué está pasando con el equipo
    detectado_por = db.Column(db.String(150), nullable=False)  # quién notó el problema
    fecha_deteccion = db.Column(db.Date, nullable=False)
    estado = db.Column(db.String(20), nullable=False, default="abierto", server_default="abierto")

    # uselist=False: desde el ticket se lee como ticket.solicitud (una sola o None).
    ticket = db.relationship("Ticket", backref=db.backref("solicitud", uselist=False))
    equipo = db.relationship("Equipo")
    categoria = db.relationship("CategoriaServicio")


class AdjuntoTicket(db.Model):
    """Evidencia del ticket. El archivo se guarda en disco con un nombre aleatorio."""

    __tablename__ = "adjuntos_ticket"
    __table_args__ = MYSQL

    id = _pk()
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False)
    nombre_original = db.Column(db.String(255), nullable=False)  # solo para mostrarlo
    nombre_guardado = db.Column(db.String(64), unique=True, nullable=False)  # nombre real en disco
    tamano_bytes = db.Column(db.Integer, nullable=False)
    subido_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    creado_en = db.Column(db.DateTime, nullable=False, default=utcnow)

    ticket = db.relationship("Ticket", backref="adjuntos")
    subido_por = db.relationship("Usuario")
