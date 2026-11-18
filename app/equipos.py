"""HU-04 · Equipos: consultar y localizar los activos, y administrarlos.

  - Consultar (permiso equipos.ver): cualquier rol ve los equipos ACTIVOS y puede
    buscarlos por código o nombre y filtrarlos por tipo y ubicación.
  - Administrar (permiso catalogos.administrar): alta, cambio y desactivación.
    Un equipo tampoco se borra, solo se desactiva.
"""
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from .autorizacion import permiso_required, tiene_permiso
from .extensions import db
from .models import Equipo, TipoEquipo, Ubicacion
from .security import login_required
from .validators import validar_codigo_equipo, validar_nombre_equipo

bp = Blueprint("equipos", __name__, url_prefix="/equipos")


@bp.get("")
@login_required
@permiso_required("equipos.ver")
def lista():
    puede_administrar = tiene_permiso(g.usuario, "catalogos.administrar")
    texto = (request.args.get("q") or "").strip()
    tipo_id = request.args.get("tipo_id", type=int)
    ubicacion_id = request.args.get("ubicacion_id", type=int)
    # Solo quien administra puede pedir que también salgan los inactivos.
    ver_inactivos = puede_administrar and request.args.get("inactivos") == "1"

    consulta = Equipo.query
    if not ver_inactivos:
        consulta = consulta.filter(Equipo.activo.is_(True))
    if texto:
        patron = f"%{texto}%"
        consulta = consulta.filter(db.or_(Equipo.codigo.ilike(patron), Equipo.nombre.ilike(patron)))
    if tipo_id:
        consulta = consulta.filter(Equipo.tipo_id == tipo_id)
    if ubicacion_id:
        consulta = consulta.filter(Equipo.ubicacion_id == ubicacion_id)

    return render_template(
        "equipo_lista.html",
        equipos=consulta.order_by(Equipo.codigo).all(),
        tipos=TipoEquipo.query.order_by(TipoEquipo.nombre).all(),
        ubicaciones=Ubicacion.query.order_by(Ubicacion.nombre).all(),
        texto=texto,
        tipo_id=tipo_id,
        ubicacion_id=ubicacion_id,
        ver_inactivos=ver_inactivos,
        puede_administrar=puede_administrar,
    )


def _opciones(modelo, id_actual):
    """Valores activos del catálogo, más el que ya tiene el equipo aunque esté inactivo."""
    return (
        modelo.query.filter(db.or_(modelo.activo.is_(True), modelo.id == id_actual))
        .order_by(modelo.nombre)
        .all()
    )


def _guardar(equipo):
    """Atiende el formulario de alta (equipo=None) y el de cambio (equipo existente)."""
    datos = {"codigo": "", "nombre": "", "tipo_id": None, "ubicacion_id": None}
    if equipo is not None:
        datos = {
            "codigo": equipo.codigo,
            "nombre": equipo.nombre,
            "tipo_id": equipo.tipo_id,
            "ubicacion_id": equipo.ubicacion_id,
        }
    # Un equipo que ya existe puede conservar su tipo/ubicación aunque esté inactivo.
    tipos = _opciones(TipoEquipo, datos["tipo_id"])
    ubicaciones = _opciones(Ubicacion, datos["ubicacion_id"])
    errores = {}

    if request.method == "POST":
        datos["codigo"], error = validar_codigo_equipo(request.form.get("codigo"))
        if error:
            errores["codigo"] = error
        else:
            repetido = Equipo.query.filter_by(codigo=datos["codigo"]).first()
            if repetido is not None and repetido is not equipo:
                errores["codigo"] = "Ya existe un equipo con ese código."

        datos["nombre"], error = validar_nombre_equipo(request.form.get("nombre"))
        if error:
            errores["nombre"] = error

        datos["tipo_id"] = request.form.get("tipo_id", type=int)
        if datos["tipo_id"] not in [t.id for t in tipos]:
            errores["tipo_id"] = "Elige un tipo de equipo activo."

        datos["ubicacion_id"] = request.form.get("ubicacion_id", type=int)
        if datos["ubicacion_id"] not in [u.id for u in ubicaciones]:
            errores["ubicacion_id"] = "Elige una ubicación activa."

        if not errores:
            if equipo is None:
                equipo = Equipo()
                db.session.add(equipo)
                mensaje = "Equipo creado."
            else:
                mensaje = "Equipo actualizado."
            equipo.codigo = datos["codigo"]
            equipo.nombre = datos["nombre"]
            equipo.tipo_id = datos["tipo_id"]
            equipo.ubicacion_id = datos["ubicacion_id"]
            db.session.commit()
            flash(mensaje, "ok")
            return redirect(url_for("equipos.lista"))

    return (
        render_template(
            "equipo_form.html",
            es_nuevo=equipo is None,
            datos=datos,
            errores=errores,
            tipos=tipos,
            ubicaciones=ubicaciones,
        ),
        400 if errores else 200,
    )


@bp.route("/nuevo", methods=["GET", "POST"])
@login_required
@permiso_required("catalogos.administrar")
def nuevo():
    return _guardar(None)


@bp.route("/<int:equipo_id>/editar", methods=["GET", "POST"])
@login_required
@permiso_required("catalogos.administrar")
def editar(equipo_id):
    equipo = db.session.get(Equipo, equipo_id)
    if equipo is None:
        abort(404)
    return _guardar(equipo)


@bp.post("/<int:equipo_id>/estado")
@login_required
@permiso_required("catalogos.administrar")
def cambiar_estado(equipo_id):
    """Activa o desactiva un equipo. Nunca se borra."""
    equipo = db.session.get(Equipo, equipo_id)
    if equipo is None:
        abort(404)
    equipo.activo = not equipo.activo
    db.session.commit()
    flash(f"Equipo {equipo.codigo} {'activado' if equipo.activo else 'desactivado'}.", "ok")
    return redirect(url_for("equipos.lista", inactivos=1))
