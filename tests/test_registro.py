"""HU-05 · Registro de ticket (Sprint 2).

Criterios:
  1. El equipo debe estar activo.
  2. Validar campos obligatorios.
  3. Folio único y persistente.
  4. Identificar solicitante, detector, equipo, situación, prioridad y fecha.
  5. Adjuntar evidencia permitida dentro del límite.
"""
import io
import os
import re
from datetime import date, timedelta

import pytest

from app.extensions import db
from app.models import (
    AdjuntoTicket,
    CategoriaServicio,
    Equipo,
    ParticipacionTicket,
    SolicitudMantenimiento,
    Ticket,
)
from app.seed import TICKETS, sembrar_demo

from .conftest import ADMIN, RESPONSABLE1, SOLICITANTE1, SOLICITANTE2, entrar, uid

PNG = b"\x89PNG\r\n\x1a\n" + b"contenido de imagen de prueba"
JPG = b"\xff\xd8\xff\xe0" + b"contenido de foto de prueba"
PDF = b"%PDF-1.4\n" + b"contenido de documento de prueba"


@pytest.fixture(autouse=True)
def carpeta(app, tmp_path):
    """Cada prueba guarda la evidencia en una carpeta temporal propia."""
    app.config["CARPETA_ADJUNTOS"] = str(tmp_path / "adjuntos")
    return app.config["CARPETA_ADJUNTOS"]


def archivos(carpeta):
    return sorted(os.listdir(carpeta)) if os.path.isdir(carpeta) else []


def datos_validos(app, **cambios):
    with app.app_context():
        datos = {
            "titulo": "El computador no enciende",
            "equipo_id": Equipo.query.filter_by(codigo="PC-001").one().id,
            "categoria_id": CategoriaServicio.query.filter_by(nombre="Hardware").one().id,
            "prioridad": "alta",
            "situacion": "Al oprimir el botón de encendido no pasa nada y no prende ninguna luz.",
            "detectado_por": "Pedro Profesor",
            "fecha_deteccion": date.today().isoformat(),
        }
    datos.update(cambios)
    return datos


def registrar(client, datos, archivo=None):
    """Envía el formulario. `archivo` es (nombre, contenido) o None."""
    datos = dict(datos)
    if archivo is not None:
        datos["evidencia"] = (io.BytesIO(archivo[1]), archivo[0])
    return client.post("/tickets/registrar", data=datos, content_type="multipart/form-data")


def ultimo(app):
    """Datos de la última solicitud registrada."""
    with app.app_context():
        s = SolicitudMantenimiento.query.order_by(SolicitudMantenimiento.id.desc()).first()
        return {
            "ticket_id": s.ticket_id,
            "folio": s.folio,
            "equipo": s.equipo.codigo,
            "categoria": s.categoria.nombre,
            "prioridad": s.prioridad,
            "situacion": s.situacion,
            "detectado_por": s.detectado_por,
            "fecha_deteccion": s.fecha_deteccion,
            "titulo": s.ticket.titulo,
            "creado_en": s.ticket.creado_en,
        }


def foto(app, carpeta):
    """Instantánea para comprobar que un registro rechazado NO guardó nada."""
    with app.app_context():
        return (
            Ticket.query.count(),
            SolicitudMantenimiento.query.count(),
            AdjuntoTicket.query.count(),
            ParticipacionTicket.query.count(),
            archivos(carpeta),
        )


# ---------- Acceso al formulario ----------
@pytest.mark.parametrize("quien, esperado", [(SOLICITANTE1, 200), (ADMIN, 200), (RESPONSABLE1, 403)])
def test_rt01_solo_los_roles_que_crean_tickets_ven_el_formulario(client, quien, esperado):
    assert entrar(client, quien).get("/tickets/registrar").status_code == esperado


def test_rt02_sin_sesion_redirige_al_login_y_no_guarda(app, client, carpeta):
    antes = foto(app, carpeta)
    for r in (client.get("/tickets/registrar"), registrar(client, datos_validos(app))):
        assert r.status_code == 302 and "/login" in r.headers["Location"]
    assert foto(app, carpeta) == antes


def test_rt03_el_rol_responsable_no_puede_registrar(app, client, carpeta):
    antes = foto(app, carpeta)
    assert registrar(entrar(client, RESPONSABLE1), datos_validos(app)).status_code == 403
    assert foto(app, carpeta) == antes


def test_rt03b_el_formulario_viejo_de_solo_titulo_ya_no_existe(app, client, carpeta):
    antes = foto(app, carpeta)
    entrar(client, ADMIN)
    assert client.get("/tickets/nuevo").status_code == 404
    assert client.post("/tickets/nuevo", data={"titulo": "Ticket sin equipo ni folio"}).status_code == 404
    assert foto(app, carpeta) == antes


# ---------- Criterio 1: equipo activo ----------
def test_rt04_el_formulario_solo_ofrece_equipos_y_categorias_activos(app, client):
    with app.app_context():
        CategoriaServicio.query.filter_by(nombre="Software").one().activo = False
        db.session.commit()
    html = entrar(client, SOLICITANTE1).get("/tickets/registrar").get_data(as_text=True)
    assert "PC-001" in html and "PC-000" not in html  # PC-000 está dado de baja
    assert "Hardware" in html and "Software" not in html


def test_rt05_un_equipo_inactivo_se_rechaza_aunque_se_envie_su_id(app, client, carpeta):
    with app.app_context():
        inactivo = Equipo.query.filter_by(codigo="PC-000").one().id
    antes = foto(app, carpeta)
    r = registrar(entrar(client, SOLICITANTE1), datos_validos(app, equipo_id=inactivo))
    assert r.status_code == 400 and "Elige un equipo activo" in r.get_data(as_text=True)
    assert foto(app, carpeta) == antes


def test_rt06_una_categoria_inactiva_se_rechaza(app, client, carpeta):
    with app.app_context():
        categoria = CategoriaServicio.query.filter_by(nombre="Software").one()
        categoria.activo = False
        db.session.commit()
        categoria_id = categoria.id
    antes = foto(app, carpeta)
    r = registrar(entrar(client, SOLICITANTE1), datos_validos(app, categoria_id=categoria_id))
    assert r.status_code == 400
    assert foto(app, carpeta) == antes


def test_rt07_si_el_equipo_se_desactiva_despues_el_ticket_lo_conserva(app, client):
    entrar(client, SOLICITANTE1)
    registrar(client, datos_validos(app))
    ticket_id = ultimo(app)["ticket_id"]
    with app.app_context():
        Equipo.query.filter_by(codigo="PC-001").one().activo = False
        db.session.commit()
    html = client.get(f"/tickets/{ticket_id}").get_data(as_text=True)
    assert "PC-001" in html


# ---------- Criterio 2: campos obligatorios y validaciones ----------
@pytest.mark.parametrize(
    "campo", ["titulo", "equipo_id", "categoria_id", "prioridad", "situacion", "detectado_por", "fecha_deteccion"]
)
def test_rt08_cada_campo_obligatorio_vacio_o_ausente_se_rechaza(app, client, carpeta, campo):
    entrar(client, SOLICITANTE1)
    antes = foto(app, carpeta)
    assert registrar(client, datos_validos(app, **{campo: ""})).status_code == 400
    sin_campo = datos_validos(app)
    del sin_campo[campo]
    assert registrar(client, sin_campo).status_code == 400
    assert foto(app, carpeta) == antes


@pytest.mark.parametrize(
    "cambios",
    [
        {"titulo": "ab"},
        {"titulo": "x" * 201},
        {"equipo_id": "9999"},
        {"equipo_id": "abc"},
        {"categoria_id": "9999"},
        {"prioridad": "urgente"},
        {"prioridad": "ALTA"},
        {"situacion": "muy corto"},
        {"situacion": "          "},
        {"situacion": "x" * 2001},
        {"detectado_por": "ab"},
        {"detectado_por": "x" * 151},
        {"fecha_deteccion": "31/12/2025"},
        {"fecha_deteccion": "2026-02-30"},
        {"fecha_deteccion": (date.today() + timedelta(days=2)).isoformat()},
    ],
)
def test_rt09_valores_invalidos_se_rechazan_sin_guardar(app, client, carpeta, cambios):
    antes = foto(app, carpeta)
    assert registrar(entrar(client, SOLICITANTE1), datos_validos(app, **cambios)).status_code == 400
    assert foto(app, carpeta) == antes


def test_rt10_al_rechazar_se_conserva_lo_escrito_y_se_marca_el_error(app, client):
    r = registrar(entrar(client, SOLICITANTE1), datos_validos(app, prioridad=""))
    html = r.get_data(as_text=True)
    assert "Elige una prioridad." in html
    assert "El computador no enciende" in html and "Pedro Profesor" in html


def test_rt11_un_error_no_guarda_la_evidencia_que_venia_bien(app, client, carpeta):
    antes = foto(app, carpeta)
    r = registrar(entrar(client, SOLICITANTE1), datos_validos(app, titulo=""), ("foto.png", PNG))
    assert r.status_code == 400
    assert foto(app, carpeta) == antes


# ---------- Criterio 3: folio único y persistente ----------
def test_rt12_registro_valido_genera_un_folio(app, client):
    r = registrar(entrar(client, SOLICITANTE1), datos_validos(app))
    u = ultimo(app)
    assert r.status_code == 302 and r.headers["Location"].endswith(f"/tickets/{u['ticket_id']}")
    assert re.fullmatch(r"TK-\d{4}-\d{5}", u["folio"])
    assert u["folio"] in client.get(r.headers["Location"]).get_data(as_text=True)


def test_rt13_cada_ticket_recibe_un_folio_distinto(app, client):
    entrar(client, SOLICITANTE1)
    for _ in range(5):
        assert registrar(client, datos_validos(app)).status_code == 302
    with app.app_context():
        folios = [s.folio for s in SolicitudMantenimiento.query]
    assert len(folios) == len(set(folios)) == len(TICKETS) + 5  # los de demostración + 5 nuevos


def test_rt14_la_base_no_admite_dos_solicitudes_con_el_mismo_folio(app, client):
    from sqlalchemy.exc import IntegrityError

    registrar(entrar(client, SOLICITANTE1), datos_validos(app))
    with app.app_context():
        primera = SolicitudMantenimiento.query.first()
        otro_ticket = Ticket(titulo="Otro ticket")
        db.session.add(otro_ticket)
        db.session.flush()
        db.session.add(
            SolicitudMantenimiento(
                ticket_id=otro_ticket.id,
                folio=primera.folio,  # repetido a propósito
                equipo_id=primera.equipo_id,
                categoria_id=primera.categoria_id,
                prioridad="baja",
                situacion="Intento de folio repetido",
                detectado_por="Prueba",
                fecha_deteccion=date.today(),
            )
        )
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_rt15_el_folio_no_cambia_al_editar_el_ticket(app, client):
    registrar(entrar(client, SOLICITANTE1), datos_validos(app))
    antes = ultimo(app)
    client.post("/logout")
    r = entrar(client, ADMIN).post(f"/tickets/{antes['ticket_id']}/editar", data={"titulo": "Título corregido"})
    assert r.status_code == 302
    despues = ultimo(app)
    assert despues["folio"] == antes["folio"] and despues["titulo"] == "Título corregido"


def test_rt16_los_tickets_de_demostracion_tienen_folio_y_no_se_duplican(app):
    with app.app_context():
        antes = sorted(s.folio for s in SolicitudMantenimiento.query)
        sembrar_demo()
        assert sorted(s.folio for s in SolicitudMantenimiento.query) == antes
        assert len(antes) == len(set(antes)) == len(TICKETS)


# ---------- Criterio 4: solicitante, detector, equipo, situación, prioridad y fecha ----------
def test_rt17_se_guardan_todos_los_datos_que_identifican_la_solicitud(app, client):
    ayer = (date.today() - timedelta(days=1)).isoformat()
    datos = datos_validos(app, fecha_deteccion=ayer, situacion="  Primera línea.\r\nSegunda línea.  ")
    registrar(entrar(client, SOLICITANTE1), datos)
    u = ultimo(app)
    assert u["titulo"] == "El computador no enciende"
    assert u["equipo"] == "PC-001" and u["categoria"] == "Hardware" and u["prioridad"] == "alta"
    assert u["situacion"] == "Primera línea.\nSegunda línea."
    assert u["detectado_por"] == "Pedro Profesor"
    assert u["fecha_deteccion"].isoformat() == ayer
    assert u["creado_en"] is not None  # fecha de registro puesta por el servidor


def test_rt18_el_solicitante_es_quien_tiene_la_sesion_y_no_se_puede_suplantar(app, client):
    otro = uid(app, SOLICITANTE2)
    datos = datos_validos(app, usuario_id=otro, solicitante_id=otro)  # campos que el servidor ignora
    registrar(entrar(client, SOLICITANTE1), datos)
    with app.app_context():
        participaciones = ParticipacionTicket.query.filter_by(ticket_id=ultimo(app)["ticket_id"]).all()
        assert [(p.usuario_id, p.tipo_participacion) for p in participaciones] == [
            (uid(app, SOLICITANTE1), "solicitante")
        ]


def test_rt19_el_detalle_muestra_los_datos_y_la_lista_el_folio(app, client):
    entrar(client, SOLICITANTE1)
    registrar(client, datos_validos(app))
    u = ultimo(app)
    html = client.get(f"/tickets/{u['ticket_id']}").get_data(as_text=True)
    for texto in (u["folio"], "PC-001", "Hardware", "Alta", "Pedro Profesor", "no prende ninguna luz", "Sara Solicitante"):
        assert texto in html
    assert u["folio"] in client.get("/tickets").get_data(as_text=True)


def test_rt20_el_texto_de_la_situacion_se_muestra_escapado(app, client):
    entrar(client, SOLICITANTE1)
    registrar(client, datos_validos(app, situacion="<script>alert('hola')</script> en la pantalla"))
    html = client.get(f"/tickets/{ultimo(app)['ticket_id']}").get_data(as_text=True)
    assert "<script>alert" not in html and "&lt;script&gt;" in html


# ---------- Criterio 5: evidencia permitida dentro del límite ----------
@pytest.mark.parametrize(
    "nombre, contenido", [("foto.png", PNG), ("foto.jpg", JPG), ("FOTO.JPEG", JPG), ("informe.pdf", PDF)]
)
def test_rt23_evidencia_permitida_se_guarda_y_se_puede_descargar(app, client, carpeta, nombre, contenido):
    entrar(client, SOLICITANTE1)
    assert registrar(client, datos_validos(app), (nombre, contenido)).status_code == 302
    ticket_id = ultimo(app)["ticket_id"]
    with app.app_context():
        adjunto = AdjuntoTicket.query.filter_by(ticket_id=ticket_id).one()
        assert adjunto.nombre_original == nombre and adjunto.tamano_bytes == len(contenido)
        assert adjunto.subido_por_id == uid(app, SOLICITANTE1)
        guardado, adjunto_id = adjunto.nombre_guardado, adjunto.id
    # En disco queda con un nombre aleatorio, no con el que traía.
    assert archivos(carpeta) == [guardado] and re.fullmatch(r"[0-9a-f]{32}\.(png|jpg|jpeg|pdf)", guardado)

    assert nombre in client.get(f"/tickets/{ticket_id}").get_data(as_text=True)
    r = client.get(f"/tickets/{ticket_id}/adjuntos/{adjunto_id}")
    assert r.status_code == 200 and r.data == contenido
    assert r.headers["Content-Disposition"].startswith("attachment")
    r.close()


def test_rt24_sin_evidencia_el_ticket_se_registra_igual(app, client, carpeta):
    entrar(client, SOLICITANTE1)
    assert registrar(client, datos_validos(app)).status_code == 302
    assert registrar(client, datos_validos(app), ("", b"")).status_code == 302  # campo de archivo vacío
    assert archivos(carpeta) == []
    assert "Sin evidencia adjunta" in client.get(f"/tickets/{ultimo(app)['ticket_id']}").get_data(as_text=True)


@pytest.mark.parametrize(
    "nombre, contenido",
    [
        ("virus.exe", b"MZ" + b"programa"),
        ("pagina.html", b"<script>alert(1)</script>"),
        ("imagen.svg", b"<svg onload='alert(1)'></svg>"),
        ("foto.png.exe", PNG),          # doble extensión
        ("sin_extension", PNG),
        ("falso.png", b"<script>alert(1)</script>"),  # extensión permitida, contenido que no es imagen
        ("falso.pdf", PNG),             # el contenido no corresponde a la extensión
        ("vacio.png", b""),
    ],
)
def test_rt25_evidencia_no_permitida_se_rechaza_sin_guardar_nada(app, client, carpeta, nombre, contenido):
    antes = foto(app, carpeta)
    r = registrar(entrar(client, SOLICITANTE1), datos_validos(app), (nombre, contenido))
    assert r.status_code == 400
    assert foto(app, carpeta) == antes


def test_rt26_evidencia_de_mas_de_10_mb_se_rechaza(app, client, carpeta):
    antes = foto(app, carpeta)
    grande = PNG + b"0" * (10 * 1024 * 1024)
    r = registrar(entrar(client, SOLICITANTE1), datos_validos(app), ("grande.png", grande))
    assert r.status_code == 413 and "10 MB" in r.get_data(as_text=True)
    assert foto(app, carpeta) == antes


def test_rt27_el_validador_tambien_corta_en_10_mb():
    from app.validators import EVIDENCIA_MAX_BYTES, validar_evidencia

    justo = PNG + b"0" * (EVIDENCIA_MAX_BYTES - len(PNG))
    assert validar_evidencia("a.png", justo) == ("png", None)
    assert validar_evidencia("a.png", justo + b"0")[1] == "El archivo supera el máximo de 10 MB."


def test_rt28_un_nombre_con_ruta_no_sale_de_la_carpeta(app, client, carpeta):
    entrar(client, SOLICITANTE1)
    r = registrar(client, datos_validos(app), ("../../../fuera.png", PNG))
    assert r.status_code == 302
    with app.app_context():
        adjunto = AdjuntoTicket.query.one()
        assert adjunto.nombre_original == "fuera.png"
        assert archivos(carpeta) == [adjunto.nombre_guardado]
    assert not os.path.exists(os.path.join(carpeta, "..", "fuera.png"))


def test_rt29_la_evidencia_solo_la_descarga_quien_puede_ver_el_ticket(app, client):
    registrar(entrar(client, SOLICITANTE1), datos_validos(app), ("foto.png", PNG))
    ticket_id = ultimo(app)["ticket_id"]
    with app.app_context():
        adjunto_id = AdjuntoTicket.query.one().id
    ruta = f"/tickets/{ticket_id}/adjuntos/{adjunto_id}"

    client.post("/logout")
    r = client.get(ruta)  # sin sesión
    assert r.status_code == 302 and "/login" in r.headers["Location"]

    assert entrar(client, SOLICITANTE2).get(ruta).status_code == 404  # no participa en el ticket
    client.post("/logout")

    r = entrar(client, ADMIN).get(ruta)  # el administrador ve todos los tickets
    assert r.status_code == 200 and r.data == PNG
    r.close()


def test_rt30_un_adjunto_no_se_descarga_desde_otro_ticket(app, client):
    entrar(client, SOLICITANTE1)
    registrar(client, datos_validos(app), ("foto.png", PNG))
    with app.app_context():
        adjunto_id = AdjuntoTicket.query.one().id
    registrar(client, datos_validos(app))  # segundo ticket, sin evidencia
    otro_ticket = ultimo(app)["ticket_id"]
    assert client.get(f"/tickets/{otro_ticket}/adjuntos/{adjunto_id}").status_code == 404
    assert client.get(f"/tickets/{otro_ticket}/adjuntos/9999").status_code == 404


def test_rt31_la_carpeta_de_evidencia_no_esta_dentro_de_la_carpeta_publica(app):
    from app.config import Config

    assert os.path.abspath(app.static_folder) not in os.path.abspath(Config.CARPETA_ADJUNTOS)
