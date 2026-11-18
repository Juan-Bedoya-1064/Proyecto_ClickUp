from flask import Blueprint, g, redirect, render_template, url_for
from sqlalchemy import text

from .extensions import db
from .security import login_required

bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    return redirect(url_for("main.panel" if g.usuario else "auth.login"))


@bp.get("/panel")
@login_required
def panel():
    return render_template("panel.html", sesion=g.sesion, permisos=g.usuario.rol.permisos)


@bp.get("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
        return {"estado": "ok"}
    except Exception:  # noqa: BLE001
        return {"estado": "error"}, 503
