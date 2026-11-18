import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models import ParticipacionTicket, Ticket, Usuario
from app.seed import USUARIOS, sembrar_demo

CLAVES = {ident: clave for ident, _n, _r, _a, clave in USUARIOS}
ADMIN, SOLICITANTE1, SOLICITANTE2 = "admin1", "solicitante1", "solicitante2"
RESPONSABLE1, RESPONSABLE2, INACTIVO = "responsable1", "responsable2", "inactivo1"
CLAVE_OK = CLAVES[SOLICITANTE1]


class ConfigCsrf(TestConfig):
    WTF_CSRF_ENABLED = True


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.drop_all()
        db.create_all()
        sembrar_demo()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, identificador, password):
    return client.post("/login", data={"identificador": identificador, "password": password})


def entrar(client, identificador):
    """Inicia sesión con la contraseña de demostración de esa persona."""
    r = login(client, identificador, CLAVES[identificador])
    assert r.status_code == 302, f"no se pudo iniciar sesión como {identificador}"
    return client


def uid(app, identificador):
    with app.app_context():
        return Usuario.query.filter_by(identificador_acceso=identificador).one().id


def foto_bd(app):
    """Instantánea de tickets y participaciones para comprobar que NO cambió nada."""
    with app.app_context():
        tickets = [(t.id, t.titulo) for t in Ticket.query.order_by(Ticket.id)]
        parts = [
            (p.ticket_id, p.usuario_id, p.tipo_participacion)
            for p in ParticipacionTicket.query.order_by(ParticipacionTicket.id)
        ]
        return tickets, parts
