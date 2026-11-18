"""Datos FICTICIOS: roles, permisos, usuarios y tickets de demostración (idempotente)."""
from .extensions import db
from .models import (
    CategoriaServicio,
    Equipo,
    ParticipacionTicket,
    Permiso,
    Rol,
    SolicitudMantenimiento,
    Ticket,
    TipoEquipo,
    Ubicacion,
    Usuario,
)

PERMISOS = {
    "tickets.ver": "Ver tickets en los que participas",
    "tickets.ver_todos": "Ver todos los tickets",
    "tickets.crear": "Crear tickets",
    "tickets.editar": "Editar tickets en los que eres responsable",
    "tickets.editar_todos": "Editar cualquier ticket",
    "tickets.asignar": "Asignar solicitantes y responsables a un ticket",
    # Sprint 2 · HU-04
    "equipos.ver": "Consultar los equipos activos",
    "catalogos.administrar": "Administrar catálogos y equipos",
}

ROLES = {
    "Solicitante": ("Reporta necesidades y consulta sus propios tickets", ["tickets.ver", "tickets.crear", "equipos.ver"]),
    "Responsable": ("Atiende los tickets que tiene asignados", ["tickets.ver", "tickets.editar", "equipos.ver"]),
    "Administrador": ("Supervisa y asigna en todos los tickets", list(PERMISOS)),
}

# (identificador, nombre, rol, activo, contraseña)
USUARIOS = [
    ("admin1", "Ana Administradora", "Administrador", True, "Admin#2026-Demo"),
    ("solicitante1", "Sara Solicitante", "Solicitante", True, "Solicitante#2026-Demo"),
    ("solicitante2", "Samuel Solicitante", "Solicitante", True, "Solicitante#2026-Demo"),
    ("responsable1", "Rosa Responsable", "Responsable", True, "Responsable#2026-Demo"),
    ("responsable2", "Raúl Responsable", "Responsable", True, "Responsable#2026-Demo"),
    ("inactivo1", "Irene Inactiva", "Solicitante", False, "Inactivo#2026-Demo"),
]

# (título, [(identificador, tipo)])
TICKETS = [
    ("Falla en la impresora del laboratorio", [("solicitante1", "solicitante"), ("responsable1", "responsable")]),
    ("Solicitud de acceso a la red wifi", [("solicitante2", "solicitante"), ("responsable2", "responsable")]),
    ("Restablecer contraseña de correo", [("solicitante1", "solicitante"), ("responsable2", "responsable")]),
    # Sprint 2 · HU-06: más tickets para probar los filtros (se agregan al final; los ids 1 a 3 no cambian)
    ("El videoproyector no da imagen", [("solicitante2", "solicitante"), ("responsable1", "responsable")]),
    ("Instalar software de simulación", [("solicitante1", "solicitante"), ("responsable1", "responsable")]),
    ("El portátil no carga la batería", [("solicitante2", "solicitante"), ("responsable2", "responsable")]),
    ("Mantenimiento preventivo de la impresora", [("solicitante1", "solicitante")]),  # aún sin responsable
    ("Monitor con líneas en la pantalla", [("solicitante2", "solicitante"), ("responsable2", "responsable")]),
]

# --- Sprint 2 · HU-04: catálogos y conjunto inicial de equipos (todo ficticio) ---
# (nombre, periodicidad preventiva en meses o None si no aplica, activo)
TIPOS_EQUIPO = [
    ("Computador de escritorio", 6, True),
    ("Portátil", 6, True),
    ("Impresora", 3, True),
    ("Videoproyector", 12, True),
    ("Switch de red", 12, True),
    ("Monitor", None, True),
    ("Máquina de escribir", None, False),
]

# (nombre, activo)
UBICACIONES = [
    ("Laboratorio de sistemas", True),
    ("Laboratorio de redes", True),
    ("Sala de profesores", True),
    ("Biblioteca", True),
    ("Oficina administrativa", True),
    ("Bodega antigua", False),
]

CATEGORIAS_SERVICIO = [
    ("Hardware", True),
    ("Software", True),
    ("Red e internet", True),
    ("Cuentas y accesos", True),
    ("Mantenimiento preventivo", True),
]

# (código, nombre, tipo, ubicación, activo)
EQUIPOS = [
    ("PC-001", "Computador Dell OptiPlex 7010", "Computador de escritorio", "Laboratorio de sistemas", True),
    ("PC-002", "Computador Dell OptiPlex 7010", "Computador de escritorio", "Laboratorio de sistemas", True),
    ("PC-003", "Computador HP ProDesk 400", "Computador de escritorio", "Oficina administrativa", True),
    ("PC-004", "Computador Lenovo ThinkCentre", "Computador de escritorio", "Bodega antigua", True),
    ("PT-001", "Portátil Lenovo ThinkPad E14", "Portátil", "Sala de profesores", True),
    ("PT-002", "Portátil HP 250 G8", "Portátil", "Biblioteca", True),
    ("IM-001", "Impresora HP LaserJet Pro M404", "Impresora", "Laboratorio de sistemas", True),
    ("IM-002", "Impresora Epson EcoTank L3250", "Impresora", "Oficina administrativa", True),
    ("VP-001", "Videoproyector Epson PowerLite", "Videoproyector", "Sala de profesores", True),
    ("SW-001", "Switch Cisco Catalyst 2960", "Switch de red", "Laboratorio de redes", True),
    ("MN-001", "Monitor LG 24 pulgadas", "Monitor", "Biblioteca", True),
    ("PC-000", "Computador Compaq Presario (dado de baja)", "Computador de escritorio", "Bodega antigua", False),
]


def sembrar_catalogos():
    """Crea los valores que falten. Si ya existen no los toca (respeta los cambios hechos)."""
    tipos = {}
    for nombre, periodicidad, activo in TIPOS_EQUIPO:
        t = TipoEquipo.query.filter_by(nombre=nombre).first()
        if t is None:
            t = TipoEquipo(nombre=nombre, periodicidad_meses=periodicidad, activo=activo)
            db.session.add(t)
        tipos[nombre] = t

    ubicaciones = {}
    for nombre, activo in UBICACIONES:
        u = Ubicacion.query.filter_by(nombre=nombre).first()
        if u is None:
            u = Ubicacion(nombre=nombre, activo=activo)
            db.session.add(u)
        ubicaciones[nombre] = u

    for nombre, activo in CATEGORIAS_SERVICIO:
        if CategoriaServicio.query.filter_by(nombre=nombre).first() is None:
            db.session.add(CategoriaServicio(nombre=nombre, activo=activo))
    db.session.flush()

    for codigo, nombre, tipo, ubicacion, activo in EQUIPOS:
        if Equipo.query.filter_by(codigo=codigo).first() is None:
            db.session.add(
                Equipo(
                    codigo=codigo,
                    nombre=nombre,
                    tipo_id=tipos[tipo].id,
                    ubicacion_id=ubicaciones[ubicacion].id,
                    activo=activo,
                )
            )

# --- Sprint 2 · HU-05: datos de mantenimiento de los tickets de demostración ---
# título del ticket -> (código de equipo, categoría, prioridad, situación, estado)
SOLICITUDES = {
    "Falla en la impresora del laboratorio": (
        "IM-001", "Hardware", "alta",
        "La impresora enciende pero atasca el papel en cada hoja y muestra el aviso de tóner bajo.",
        "en_proceso",
    ),
    "Solicitud de acceso a la red wifi": (
        "SW-001", "Red e internet", "media",
        "Los equipos del laboratorio de redes no reciben dirección al conectarse al switch.",
        "abierto",
    ),
    "Restablecer contraseña de correo": (
        "PC-003", "Cuentas y accesos", "baja",
        "En este computador no se puede iniciar sesión en el correo; pide restablecer la contraseña.",
        "resuelto",
    ),
    "El videoproyector no da imagen": (
        "VP-001", "Hardware", "media",
        "El videoproyector enciende pero la pantalla se queda en azul con cualquier computador.",
        "en_proceso",
    ),
    "Instalar software de simulación": (
        "PC-002", "Software", "baja",
        "Se necesita instalar el simulador de redes para la práctica de la próxima semana.",
        "abierto",
    ),
    "El portátil no carga la batería": (
        "PT-001", "Hardware", "critica",
        "El portátil solo funciona conectado; al quitar el cargador se apaga de inmediato.",
        "abierto",
    ),
    "Mantenimiento preventivo de la impresora": (
        "IM-002", "Mantenimiento preventivo", "media",
        "La impresora cumple tres meses desde su último mantenimiento preventivo.",
        "abierto",
    ),
    "Monitor con líneas en la pantalla": (
        "MN-001", "Hardware", "alta",
        "El monitor mostraba líneas verticales; se cambió el cable de video y quedó funcionando.",
        "cerrado",
    ),
}


def sembrar_solicitudes():
    """Completa los tickets de demostración que todavía no tengan solicitud ni folio."""
    for titulo, (codigo, categoria, prioridad, situacion, estado) in SOLICITUDES.items():
        ticket = Ticket.query.filter_by(titulo=titulo).first()
        if ticket is None or ticket.solicitud is not None:
            continue
        solicitante = None
        for p in ticket.participaciones:
            if p.tipo_participacion == "solicitante":
                solicitante = p.usuario
        db.session.add(
            SolicitudMantenimiento(
                ticket_id=ticket.id,
                folio=f"TK-{ticket.creado_en.year}-{ticket.id:05d}",
                equipo_id=Equipo.query.filter_by(codigo=codigo).one().id,
                categoria_id=CategoriaServicio.query.filter_by(nombre=categoria).one().id,
                prioridad=prioridad,
                situacion=situacion,
                detectado_por=solicitante.nombre_completo if solicitante else "Sin dato",
                fecha_deteccion=ticket.creado_en.date(),
                estado=estado,
            )
        )


def sembrar_demo():
    permisos = {}
    for codigo, desc in PERMISOS.items():
        p = Permiso.query.filter_by(codigo=codigo).first() or Permiso(codigo=codigo)
        p.descripcion = desc
        db.session.add(p)
        permisos[codigo] = p

    roles = {}
    for nombre, (desc, codigos) in ROLES.items():
        r = Rol.query.filter_by(nombre=nombre).first() or Rol(nombre=nombre)
        r.descripcion = desc
        r.permisos = [permisos[c] for c in codigos]
        db.session.add(r)
        roles[nombre] = r
    db.session.flush()

    usuarios = {}
    for ident, nombre, rol, activo, clave in USUARIOS:
        u = Usuario.query.filter_by(identificador_acceso=ident).first()
        if u is None:
            u = Usuario(identificador_acceso=ident, nombre_completo=nombre, rol_id=roles[rol].id, activo=activo)
            u.set_password(clave)
            db.session.add(u)
        usuarios[ident] = u
    db.session.flush()

    for titulo, participantes in TICKETS:
        if Ticket.query.filter_by(titulo=titulo).first():
            continue
        t = Ticket(titulo=titulo)
        for ident, tipo in participantes:
            t.participaciones.append(
                ParticipacionTicket(usuario_id=usuarios[ident].id, tipo_participacion=tipo)
            )
        db.session.add(t)

    sembrar_catalogos()
    db.session.flush()
    sembrar_solicitudes()
    db.session.commit()
