"""HU-01 · Inicio y cierre de sesión."""
import re
from datetime import timedelta
from io import BytesIO

from app import create_app
from app.auth import MENSAJE_GENERICO
from app.extensions import db
from app.models import Sesion, Usuario, utcnow
from app.seed import sembrar_demo

from .conftest import CLAVE_OK, INACTIVO, SOLICITANTE1, ConfigCsrf, entrar, login


def _normalizar(html, texto):
    # El token CSRF lleva la hora: cambia de un segundo a otro aunque la página sea
    # la misma. Se quita para comparar solo lo que ve la persona.
    html = re.sub(r'name="csrf_token" value="[^"]*"', 'name="csrf_token" value="TOKEN"', html)
    return html.replace(texto, "ID")


# ---------- Criterio 1: usuario activo con credenciales válidas inicia sesión ----------
def test_cp01_login_valido_da_acceso(client):
    r = login(client, SOLICITANTE1, CLAVE_OK)
    assert r.status_code == 302 and r.headers["Location"].endswith("/panel")
    panel = client.get("/panel")
    assert panel.status_code == 200
    assert "Sara" in panel.get_data(as_text=True)


def test_cp02_identificador_se_normaliza(client):
    assert login(client, "  SOLICITANTE1 ", CLAVE_OK).status_code == 302


def test_cp03_cookie_de_sesion_httponly(client):
    r = login(client, SOLICITANTE1, CLAVE_OK)
    assert "HttpOnly" in r.headers["Set-Cookie"] and "SameSite=Lax" in r.headers["Set-Cookie"]


def test_cp04_login_con_sesion_activa_redirige_al_panel(client):
    entrar(client, SOLICITANTE1)
    r = client.get("/login")
    assert r.status_code == 302 and r.headers["Location"].endswith("/panel")


def test_cp05_se_crea_fila_en_sesiones(client, app):
    entrar(client, SOLICITANTE1)
    with app.app_context():
        s = Sesion.query.one()
        assert s.cerrada_en is None and s.expira_en > s.iniciada_en
        assert len(s.token_hash) == 64  # hash, nunca el token


# ---------- Criterio 2: credenciales inválidas no revelan cuál dato falló ----------
def test_cp06_contrasena_incorrecta_y_cuenta_inexistente_son_indistinguibles(client):
    r1 = login(client, SOLICITANTE1, "incorrecta-123")
    r2 = login(client, "noexiste", CLAVE_OK)
    assert r1.status_code == r2.status_code == 401
    for r in (r1, r2):
        assert MENSAJE_GENERICO in r.get_data(as_text=True)
    assert _normalizar(r1.get_data(as_text=True), SOLICITANTE1) == _normalizar(
        r2.get_data(as_text=True), "noexiste"
    )
    assert client.get("/panel").status_code == 302


def test_cp07_el_mensaje_no_menciona_motivos(client):
    html = login(client, "noexiste", "x" * 12).get_data(as_text=True).lower()
    for palabra in ("no existe", "inactiv", "bloquead", "no registrad"):
        assert palabra not in html


# ---------- Criterio 3: cuenta inactiva no puede ingresar ----------
def test_cp08_cuenta_inactiva_con_credenciales_validas_no_ingresa(client):
    r = login(client, INACTIVO, "Inactivo#2026-Demo")
    assert r.status_code == 401 and MENSAJE_GENERICO in r.get_data(as_text=True)
    assert client.get("/panel").status_code == 302


def test_cp09_inactiva_indistinguible_de_credencial_invalida(client):
    r1 = login(client, INACTIVO, "Inactivo#2026-Demo")
    r2 = login(client, "noexiste", "Inactivo#2026-Demo")
    assert _normalizar(r1.get_data(as_text=True), INACTIVO) == _normalizar(
        r2.get_data(as_text=True), "noexiste"
    )


def test_cp10_desactivar_cuenta_invalida_la_sesion_abierta(client, app):
    entrar(client, SOLICITANTE1)
    assert client.get("/panel").status_code == 200
    with app.app_context():
        Usuario.query.filter_by(identificador_acceso=SOLICITANTE1).one().activo = False
        db.session.commit()
    assert client.get("/panel").status_code == 302


# ---------- Criterio 4: cerrar sesión elimina acceso a funciones protegidas ----------
def test_cp11_logout_elimina_acceso(client, app):
    entrar(client, SOLICITANTE1)
    r = client.post("/logout")
    assert r.status_code == 302 and r.headers["Location"].endswith("/login")
    assert client.get("/panel").status_code == 302
    assert client.get("/tickets").status_code == 302
    with app.app_context():
        assert Sesion.query.one().cerrada_en is not None


def test_cp12_cookie_vieja_no_sirve_tras_logout(client, app):
    entrar(client, SOLICITANTE1)
    cookie_vieja = client.get_cookie("session").value
    client.post("/logout")
    otro = app.test_client()
    otro.set_cookie("session", cookie_vieja)
    assert otro.get("/panel").status_code == 302
    assert otro.get("/tickets/1").status_code == 302


def test_cp13_logout_solo_acepta_post(client):
    entrar(client, SOLICITANTE1)
    assert client.get("/logout").status_code == 405
    assert client.get("/panel").status_code == 200


def test_cp14_paginas_protegidas_no_se_cachean(client):
    entrar(client, SOLICITANTE1)
    assert client.get("/panel").headers["Cache-Control"] == "no-store"


def test_cp15_rutas_protegidas_sin_sesion_redirigen_a_login(client):
    for ruta in ("/panel", "/tickets", "/tickets/1", "/tickets/registrar", "/tickets/1/editar"):
        r = client.get(ruta)
        assert r.status_code == 302 and r.headers["Location"].endswith("/login"), ruta


def test_cp16_sesion_expirada_pierde_acceso(client, app):
    entrar(client, SOLICITANTE1)
    with app.app_context():
        Sesion.query.update({"expira_en": utcnow() - timedelta(minutes=1)})
        db.session.commit()
    assert client.get("/panel").status_code == 302


# ---------- Validaciones de entrada ----------
def test_cp17_campos_vacios(client):
    r = login(client, "", "")
    html = r.get_data(as_text=True)
    assert r.status_code == 400
    assert "Escribe tu identificador" in html and "Escribe tu contraseña" in html


def test_cp18_identificador_con_formato_invalido(client):
    r = login(client, "no válido!", CLAVE_OK)
    assert r.status_code == 400 and "3 a 100 caracteres" in r.get_data(as_text=True)


def test_cp19_password_demasiado_larga(client):
    assert login(client, SOLICITANTE1, "a" * 129).status_code == 400


def test_cp20_inyeccion_sql_no_inicia_sesion(client):
    assert login(client, "' OR '1'='1", "' OR '1'='1").status_code == 400
    assert login(client, "xx@demo", "' OR '1'='1").status_code == 401


# ---------- Seguridad adicional ----------
def test_cp21_password_se_guarda_con_hash(app):
    with app.app_context():
        u = Usuario.query.filter_by(identificador_acceso=SOLICITANTE1).one()
        assert u.contrasena_hash != CLAVE_OK and CLAVE_OK not in u.contrasena_hash


def test_cp22_limite_de_10mb(client):
    grande = BytesIO(b"x" * (10 * 1024 * 1024 + 1))
    r = client.post(
        "/login",
        data={"identificador": SOLICITANTE1, "password": CLAVE_OK, "archivo": (grande, "a.bin")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 413


def test_cp23_csrf_bloquea_formularios_sin_token():
    app = create_app(ConfigCsrf)
    with app.app_context():
        db.drop_all()
        db.create_all()
        sembrar_demo()
    r = app.test_client().post("/login", data={"identificador": SOLICITANTE1, "password": CLAVE_OK})
    assert r.status_code == 400


def test_cp24_login_con_csrf_valido():
    app = create_app(ConfigCsrf)
    with app.app_context():
        db.drop_all()
        db.create_all()
        sembrar_demo()
    c = app.test_client()
    token = re.search(r'name="csrf_token" value="([^"]+)"', c.get("/login").get_data(as_text=True)).group(1)
    r = c.post("/login", data={"identificador": SOLICITANTE1, "password": CLAVE_OK, "csrf_token": token})
    assert r.status_code == 302


def test_cp25_health(client):
    assert client.get("/health").get_json() == {"estado": "ok"}
