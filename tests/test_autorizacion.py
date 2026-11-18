"""HU-02 · Control de acceso por rol y participación en el ticket.

Datos de demostración (ids por orden de creación):
  T1 · solicitante1 (solicitante) + responsable1 (responsable)
  T2 · solicitante2 (solicitante) + responsable2 (responsable)
  T3 · solicitante1 (solicitante) + responsable2 (responsable)
"""
import pytest

from app.extensions import db
from app.models import ParticipacionTicket, Rol, Ticket, Usuario
from app.seed import ROLES

from .conftest import (
    ADMIN, INACTIVO, RESPONSABLE1, RESPONSABLE2, SOLICITANTE1, SOLICITANTE2,
    entrar, foto_bd, uid,
)
from .test_registro import datos_validos  # datos completos del formulario de la HU-05

T1, T2, T3 = "Falla en la impresora del laboratorio", "Solicitud de acceso a la red wifi", "Restablecer contraseña de correo"


# ======================================================================
# Matriz de acceso directo por URL (GET): permitido (200) / rechazado
# ======================================================================
MATRIZ_GET = [
    # (quién, url, esperado)
    (SOLICITANTE1, "/tickets", 200),
    (SOLICITANTE1, "/tickets/1", 200),
    (SOLICITANTE1, "/tickets/2", 404),   # ticket ajeno: no se revela
    (SOLICITANTE1, "/tickets/3", 200),
    (SOLICITANTE1, "/tickets/registrar", 200),
    (SOLICITANTE1, "/tickets/1/editar", 403),  # su rol no edita
    (SOLICITANTE1, "/tickets/2/editar", 403),
    (RESPONSABLE1, "/tickets", 200),
    (RESPONSABLE1, "/tickets/1", 200),
    (RESPONSABLE1, "/tickets/2", 404),
    (RESPONSABLE1, "/tickets/3", 404),
    (RESPONSABLE1, "/tickets/registrar", 403),     # su rol no crea
    (RESPONSABLE1, "/tickets/1/editar", 200),
    (RESPONSABLE1, "/tickets/2/editar", 404),  # no participa
    (RESPONSABLE2, "/tickets/1", 404),
    (RESPONSABLE2, "/tickets/2", 200),
    (RESPONSABLE2, "/tickets/3", 200),
    (RESPONSABLE2, "/tickets/2/editar", 200),
    (RESPONSABLE2, "/tickets/3/editar", 200),
    (RESPONSABLE2, "/tickets/1/editar", 404),
    (ADMIN, "/tickets", 200),
    (ADMIN, "/tickets/1", 200),
    (ADMIN, "/tickets/2", 200),
    (ADMIN, "/tickets/3", 200),
    (ADMIN, "/tickets/registrar", 200),
    (ADMIN, "/tickets/2/editar", 200),
    (ADMIN, "/tickets/999", 404),
]


@pytest.mark.parametrize("quien,url,esperado", MATRIZ_GET)
def test_ac01_matriz_de_acceso_directo(client, quien, url, esperado):
    entrar(client, quien)
    assert client.get(url).status_code == esperado


# ======================================================================
# Operaciones permitidas
# ======================================================================
def test_ac02_lista_filtrada_por_participacion(client):
    entrar(client, SOLICITANTE1)
    html = client.get("/tickets").get_data(as_text=True)
    assert T1 in html and T3 in html and T2 not in html


def test_ac03_responsable_solo_ve_los_suyos(client):
    entrar(client, RESPONSABLE1)
    html = client.get("/tickets").get_data(as_text=True)
    assert T1 in html and T2 not in html and T3 not in html


def test_ac04_admin_ve_todos(client):
    entrar(client, ADMIN)
    html = client.get("/tickets").get_data(as_text=True)
    assert T1 in html and T2 in html and T3 in html


def test_ac05_solicitante_crea_ticket_y_queda_como_solicitante(client, app):
    entrar(client, SOLICITANTE1)
    r = client.post("/tickets/registrar", data=datos_validos(app, titulo="  Problema   con el proyector "))
    assert r.status_code == 302
    with app.app_context():
        t = Ticket.query.filter_by(titulo="Problema con el proyector").one()
        p = ParticipacionTicket.query.filter_by(ticket_id=t.id).one()
        assert (p.usuario_id, p.tipo_participacion) == (uid(app, SOLICITANTE1), "solicitante")
        nuevo_id = t.id
    assert client.get(f"/tickets/{nuevo_id}").status_code == 200
    # otra persona no lo ve
    otro = app.test_client()
    entrar(otro, SOLICITANTE2)
    assert otro.get(f"/tickets/{nuevo_id}").status_code == 404


def test_ac06_responsable_edita_su_ticket(client, app):
    entrar(client, RESPONSABLE1)
    r = client.post("/tickets/1/editar", data={"titulo": "Impresora reparada"})
    assert r.status_code == 302
    with app.app_context():
        assert db.session.get(Ticket, 1).titulo == "Impresora reparada"


def test_ac07_admin_edita_cualquiera_y_asigna_responsable(client, app):
    entrar(client, ADMIN)
    assert client.post("/tickets/2/editar", data={"titulo": "Wifi resuelto"}).status_code == 302
    r = client.post("/tickets/2/participantes", data={"usuario_id": uid(app, RESPONSABLE1), "tipo_participacion": "responsable"})
    assert r.status_code == 302
    nuevo = app.test_client()
    entrar(nuevo, RESPONSABLE1)
    assert nuevo.get("/tickets/2").status_code == 200          # ahora participa
    assert nuevo.get("/tickets/2/editar").status_code == 200   # y puede editarlo


def test_ac08_titulo_se_muestra_escapado(client, app):
    entrar(client, SOLICITANTE1)
    datos = datos_validos(app, titulo="<script>alert(1)</script>")
    r = client.post("/tickets/registrar", data=datos, follow_redirects=True)
    html = r.get_data(as_text=True)
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html


# ======================================================================
# Operaciones rechazadas: no alteran datos
# ======================================================================
RECHAZOS_POST = [
    # (quién, url, datos, esperado)
    (SOLICITANTE1, "/tickets/1/editar", {"titulo": "Hackeado"}, 403),          # rol sin permiso, ticket propio
    (SOLICITANTE1, "/tickets/2/editar", {"titulo": "Hackeado"}, 403),          # rol sin permiso, ticket ajeno
    (RESPONSABLE1, "/tickets/2/editar", {"titulo": "Hackeado"}, 404),          # no participa
    (RESPONSABLE1, "/tickets/3/editar", {"titulo": "Hackeado"}, 404),
    (RESPONSABLE1, "/tickets/registrar", {"titulo": "Ticket no permitido"}, 403),  # rol no crea
    (SOLICITANTE1, "/tickets/1/participantes", {"usuario_id": "@RESP2", "tipo_participacion": "responsable"}, 403),
    (RESPONSABLE1, "/tickets/1/participantes", {"usuario_id": "@RESP2", "tipo_participacion": "responsable"}, 403),
    (None, "/tickets/1/editar", {"titulo": "Hackeado"}, 302),                  # sin sesión -> login
    (None, "/tickets/registrar", {"titulo": "Sin sesión"}, 302),
    (None, "/tickets/1/participantes", {"usuario_id": "1", "tipo_participacion": "responsable"}, 302),
    # Administrador con datos inválidos
    (ADMIN, "/tickets/1/participantes", {"usuario_id": "@RESP2", "tipo_participacion": "dueño"}, 400),
    (ADMIN, "/tickets/1/participantes", {"usuario_id": "@INACTIVO", "tipo_participacion": "solicitante"}, 400),
    (ADMIN, "/tickets/1/participantes", {"usuario_id": "99999", "tipo_participacion": "solicitante"}, 400),
    (ADMIN, "/tickets/1/participantes", {"usuario_id": "@SOL2", "tipo_participacion": "responsable"}, 400),  # rol incompatible
    (ADMIN, "/tickets/1/participantes", {"usuario_id": "@SOL1", "tipo_participacion": "solicitante"}, 409),  # duplicado
    (ADMIN, "/tickets/1/editar", {"titulo": ""}, 400),
    (ADMIN, "/tickets/1/editar", {"titulo": "x" * 201}, 400),
    (ADMIN, "/tickets/registrar", {"titulo": "ab"}, 400),
    (ADMIN, "/tickets/999/participantes", {"usuario_id": "@RESP2", "tipo_participacion": "responsable"}, 404),
]
ALIAS = {"@RESP2": RESPONSABLE2, "@SOL1": SOLICITANTE1, "@SOL2": SOLICITANTE2, "@INACTIVO": INACTIVO}


@pytest.mark.parametrize("quien,url,datos,esperado", RECHAZOS_POST)
def test_ac09_operaciones_indebidas_se_rechazan_sin_alterar_datos(client, app, quien, url, datos, esperado):
    datos = dict(datos)
    if datos.get("usuario_id", "").startswith("@"):
        datos["usuario_id"] = uid(app, ALIAS[datos["usuario_id"]])
    if quien:
        entrar(client, quien)
    antes = foto_bd(app)
    assert client.post(url, data=datos).status_code == esperado
    assert foto_bd(app) == antes


def test_ac10_ticket_ajeno_e_inexistente_responden_igual(client):
    entrar(client, SOLICITANTE1)
    ajeno, inexistente = client.get("/tickets/2"), client.get("/tickets/999")
    assert ajeno.status_code == inexistente.status_code == 404
    assert ajeno.get_data() == inexistente.get_data()
    assert T2 not in ajeno.get_data(as_text=True)


def test_ac11_los_datos_ajenos_no_aparecen_en_ninguna_pantalla_permitida(client):
    entrar(client, SOLICITANTE1)
    for url in ("/tickets", "/tickets/1", "/tickets/3", "/panel"):
        html = client.get(url).get_data(as_text=True)
        assert T2 not in html and "Samuel" not in html.replace("Sara", "")  # nombre del solicitante ajeno


# ======================================================================
# Las reglas se evalúan en cada petición (no se "recuerdan")
# ======================================================================
def test_ac12_cambio_de_rol_aplica_de_inmediato(client, app):
    entrar(client, RESPONSABLE1)
    assert client.get("/tickets/1/editar").status_code == 200
    with app.app_context():
        u = Usuario.query.filter_by(identificador_acceso=RESPONSABLE1).one()
        u.rol_id = Rol.query.filter_by(nombre="Solicitante").one().id
        db.session.commit()
    assert client.get("/tickets/1/editar").status_code == 403
    assert client.post("/tickets/1/editar", data={"titulo": "Tarde"}).status_code == 403


def test_ac13_retirar_participacion_aplica_de_inmediato(client, app):
    entrar(client, RESPONSABLE1)
    assert client.get("/tickets/1").status_code == 200
    with app.app_context():
        ParticipacionTicket.query.filter_by(ticket_id=1, usuario_id=uid(app, RESPONSABLE1)).delete()
        db.session.commit()
    assert client.get("/tickets/1").status_code == 404


def test_ac14_cuenta_desactivada_pierde_acceso_a_tickets(client, app):
    entrar(client, SOLICITANTE1)
    with app.app_context():
        Usuario.query.filter_by(identificador_acceso=SOLICITANTE1).one().activo = False
        db.session.commit()
    assert client.get("/tickets/1").status_code == 302


def test_ac15_cerrar_sesion_corta_el_acceso_directo(client):
    entrar(client, RESPONSABLE1)
    assert client.get("/tickets/1").status_code == 200
    client.post("/logout")
    assert client.get("/tickets/1").status_code == 302


# ======================================================================
# Integridad de la configuración de roles y permisos
# ======================================================================
def test_ac16_roles_y_permisos_sembrados_coinciden_con_la_matriz(app):
    with app.app_context():
        for nombre, (_desc, codigos) in ROLES.items():
            rol = Rol.query.filter_by(nombre=nombre).one()
            assert {p.codigo for p in rol.permisos} == set(codigos)


def test_ac17_responsable_no_tiene_permisos_de_creacion_ni_asignacion(app):
    with app.app_context():
        permisos = Usuario.query.filter_by(identificador_acceso=RESPONSABLE1).one().codigos_permiso()
        assert "tickets.crear" not in permisos and "tickets.asignar" not in permisos
        assert "tickets.editar_todos" not in permisos and "tickets.ver_todos" not in permisos
