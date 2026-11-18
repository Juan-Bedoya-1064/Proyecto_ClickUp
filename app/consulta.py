"""HU-06 · Consulta de tickets: listado filtrable, solo con lo que la persona puede ver.

El orden importa:
  1. AUTORIZACIÓN: primero se arma la consulta de los tickets visibles para la persona
     (un administrador ve todos; los demás solo aquellos en los que participan).
  2. FILTROS: se aplican encima de esa consulta. Por eso ningún filtro, ni escrito a
     mano en la dirección, puede mostrar un ticket ajeno.
  3. OPCIONES: las listas desplegables se arman solo con datos de los tickets visibles,
     así tampoco revelan equipos o personas de tickets ajenos.

Filtros: folio (búsqueda), equipo, solicitante, responsable, área, prioridad y estado.
El «área» es la ubicación del equipo del ticket.
"""
from .autorizacion import tiene_permiso
from .models import ESTADOS, PRIORIDADES, Equipo, SolicitudMantenimiento, Ticket


def tickets_visibles(usuario):
    """Consulta con los tickets que la persona tiene derecho a ver."""
    consulta = Ticket.query
    if not tiene_permiso(usuario, "tickets.ver_todos"):
        consulta = consulta.filter(Ticket.participaciones.any(usuario_id=usuario.id))
    return consulta


def leer_filtros(args):
    """Lee los filtros de la dirección. Un valor que no sirve se toma como «sin filtro»."""
    prioridad = args.get("prioridad", "")
    estado = args.get("estado", "")
    return {
        "folio": (args.get("folio") or "").strip().upper()[:20],
        "equipo_id": args.get("equipo_id", type=int),
        "solicitante_id": args.get("solicitante_id", type=int),
        "responsable_id": args.get("responsable_id", type=int),
        "area_id": args.get("area_id", type=int),
        "prioridad": prioridad if prioridad in PRIORIDADES else "",
        "estado": estado if estado in ESTADOS else "",
    }


def aplicar_filtros(consulta, filtros):
    """Agrega a la consulta una condición por cada filtro que venga con valor."""
    # outerjoin: un ticket sin solicitud no rompe la lista (simplemente no cumple esos filtros).
    consulta = consulta.outerjoin(
        SolicitudMantenimiento, SolicitudMantenimiento.ticket_id == Ticket.id
    ).outerjoin(Equipo, Equipo.id == SolicitudMantenimiento.equipo_id)

    if filtros["folio"]:
        consulta = consulta.filter(SolicitudMantenimiento.folio.ilike(f"%{filtros['folio']}%"))
    if filtros["equipo_id"]:
        consulta = consulta.filter(SolicitudMantenimiento.equipo_id == filtros["equipo_id"])
    if filtros["area_id"]:
        consulta = consulta.filter(Equipo.ubicacion_id == filtros["area_id"])
    if filtros["prioridad"]:
        consulta = consulta.filter(SolicitudMantenimiento.prioridad == filtros["prioridad"])
    if filtros["estado"]:
        consulta = consulta.filter(SolicitudMantenimiento.estado == filtros["estado"])
    if filtros["solicitante_id"]:
        consulta = consulta.filter(
            Ticket.participaciones.any(usuario_id=filtros["solicitante_id"], tipo_participacion="solicitante")
        )
    if filtros["responsable_id"]:
        consulta = consulta.filter(
            Ticket.participaciones.any(usuario_id=filtros["responsable_id"], tipo_participacion="responsable")
        )
    return consulta


def opciones_de_filtro(tickets):
    """Valores para las listas desplegables, sacados solo de los tickets visibles."""
    equipos, areas, solicitantes, responsables = {}, {}, {}, {}
    for ticket in tickets:
        if ticket.solicitud is not None:
            equipo = ticket.solicitud.equipo
            equipos[equipo.id] = f"{equipo.codigo} · {equipo.nombre}"
            areas[equipo.ubicacion.id] = equipo.ubicacion.nombre
        for p in ticket.participaciones:
            if p.tipo_participacion == "solicitante":
                solicitantes[p.usuario.id] = p.usuario.nombre_completo
            elif p.tipo_participacion == "responsable":
                responsables[p.usuario.id] = p.usuario.nombre_completo

    def ordenar(diccionario):
        # lista de (id, texto) ordenada por el texto
        return sorted(diccionario.items(), key=lambda par: par[1])

    return {
        "equipos": ordenar(equipos),
        "areas": ordenar(areas),
        "solicitantes": ordenar(solicitantes),
        "responsables": ordenar(responsables),
    }


def consultar_tickets(usuario, args):
    """Devuelve lo que necesita la plantilla del listado."""
    visibles = tickets_visibles(usuario)
    filtros = leer_filtros(args)
    tickets = aplicar_filtros(visibles, filtros).order_by(Ticket.id.desc()).all()
    todos = visibles.all()
    return {
        "tickets": tickets,
        "filtros": filtros,
        "hay_filtros": any(filtros.values()),
        "opciones": opciones_de_filtro(todos),
        "total_visibles": len(todos),
    }
