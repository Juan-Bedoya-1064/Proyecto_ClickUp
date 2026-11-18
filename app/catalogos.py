"""HU-04 · Administración de catálogos (solo quien tenga el permiso catalogos.administrar).

Catálogos: tipos de equipo, ubicaciones y categorías de servicio.
Reglas:
  - Alta y cambio: el nombre es obligatorio y no se puede repetir dentro del catálogo.
  - Desactivación: los valores nunca se borran, solo se marcan como inactivos. Un valor
    inactivo ya no se ofrece para registros nuevos, pero los equipos que lo usaban lo
    siguen mostrando (referencia histórica).
  - Periodicidad preventiva: solo aplica a los tipos de equipo y es opcional.
"""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from sqlalchemy import func

from .autorizacion import permiso_required
from .extensions import db
from .models import CategoriaServicio, TipoEquipo, Ubicacion
from .security import login_required
from .validators import validar_nombre_catalogo, validar_periodicidad

bp = Blueprint("catalogos", __name__, url_prefix="/catalogos")

# clave que va en la URL -> (título que se muestra, modelo)
CATALOGOS = {
    "tipos-equipo": ("Tipos de equipo", TipoEquipo),
    "ubicaciones": ("Ubicaciones", Ubicacion),
    "categorias": ("Categorías de servicio", CategoriaServicio),
}


def buscar_catalogo(clave):
    """Devuelve (título, modelo) o responde 404 si el catálogo no existe."""
    if clave not in CATALOGOS:
        abort(404)
    return CATALOGOS[clave]


def nombre_repetido(modelo, nombre, id_actual=None):
    """True si otro valor del mismo catálogo ya tiene ese nombre (sin importar mayúsculas)."""
    consulta = modelo.query.filter(func.lower(modelo.nombre) == nombre.lower())
    if id_actual is not None:
        consulta = consulta.filter(modelo.id != id_actual)
    return consulta.first() is not None


@bp.get("")
@login_required
@permiso_required("catalogos.administrar")
def lista():
    catalogos = []
    for clave, (titulo, modelo) in CATALOGOS.items():
        valores = modelo.query.order_by(modelo.nombre).all()
        catalogos.append((clave, titulo, valores))
    return render_template("catalogo_lista.html", catalogos=catalogos)


def _guardar(clave, valor):
    """Atiende el formulario de alta (valor=None) y el de cambio (valor existente)."""
    titulo, modelo = buscar_catalogo(clave)
    con_periodicidad = modelo is TipoEquipo
    datos = {"nombre": "", "periodicidad": ""}
    if valor is not None:
        datos["nombre"] = valor.nombre
        if con_periodicidad and valor.periodicidad_meses:
            datos["periodicidad"] = valor.periodicidad_meses
    errores = {}

    if request.method == "POST":
        datos["nombre"], error = validar_nombre_catalogo(request.form.get("nombre"))
        if error:
            errores["nombre"] = error
        elif nombre_repetido(modelo, datos["nombre"], valor.id if valor else None):
            errores["nombre"] = "Ya existe un valor con ese nombre en este catálogo."

        periodicidad = None
        if con_periodicidad:
            datos["periodicidad"] = (request.form.get("periodicidad") or "").strip()
            periodicidad, error = validar_periodicidad(datos["periodicidad"])
            if error:
                errores["periodicidad"] = error

        if not errores:
            if valor is None:
                valor = modelo(nombre=datos["nombre"])
                db.session.add(valor)
                mensaje = "Valor creado."
            else:
                valor.nombre = datos["nombre"]
                mensaje = "Valor actualizado."
            if con_periodicidad:
                valor.periodicidad_meses = periodicidad
            db.session.commit()
            flash(mensaje, "ok")
            return redirect(url_for("catalogos.lista"))

    return (
        render_template(
            "catalogo_form.html",
            titulo_catalogo=titulo,
            es_nuevo=valor is None,
            con_periodicidad=con_periodicidad,
            datos=datos,
            errores=errores,
        ),
        400 if errores else 200,
    )


@bp.route("/<clave>/nuevo", methods=["GET", "POST"])
@login_required
@permiso_required("catalogos.administrar")
def nuevo(clave):
    return _guardar(clave, None)


@bp.route("/<clave>/<int:valor_id>/editar", methods=["GET", "POST"])
@login_required
@permiso_required("catalogos.administrar")
def editar(clave, valor_id):
    _titulo, modelo = buscar_catalogo(clave)
    valor = db.session.get(modelo, valor_id)
    if valor is None:
        abort(404)
    return _guardar(clave, valor)


@bp.post("/<clave>/<int:valor_id>/estado")
@login_required
@permiso_required("catalogos.administrar")
def cambiar_estado(clave, valor_id):
    """Activa o desactiva un valor. Nunca se borra."""
    _titulo, modelo = buscar_catalogo(clave)
    valor = db.session.get(modelo, valor_id)
    if valor is None:
        abort(404)
    valor.activo = not valor.activo
    db.session.commit()
    if valor.activo:
        flash(f"«{valor.nombre}» se activó de nuevo.", "ok")
    else:
        flash(f"«{valor.nombre}» se desactivó. Los equipos que ya lo usan lo conservan.", "ok")
    return redirect(url_for("catalogos.lista"))
