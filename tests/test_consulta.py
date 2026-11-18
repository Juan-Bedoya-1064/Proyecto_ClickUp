"""HU-06 · Consulta de tickets (Sprint 2).

Criterios:
  1. Autorización por ticket.
  2. Búsqueda por folio.
  3. Filtros por equipo, solicitante, responsable, área, prioridad y estado.
  4. Detalle coherente.

Tickets de demostración (id · solicitante · responsable · equipo · área · prioridad · estado):
  1 · solicitante1 · responsable1 · IM-001 · Laboratorio de sistemas · alta    · en_proceso
  2 · solicitante2 · responsable2 · SW-001 · Laboratorio de redes    · media   · abierto
  3 · solicitante1 · responsable2 · PC-003 · Oficina administrativa  · baja    · resuelto
  4 · solicitante2 · responsable1 · VP-001 · Sala de profesores      · media   · en_proceso
  5 · solicitante1 · responsable1 · PC-002 · Laboratorio de sistemas · baja    · abierto
  6 · solicitante2 · responsable2 · PT-001 · Sala de profesores      · critica · abierto
  7 · solicitante1 · (ninguno)    · IM-002 · Oficina administrativa  · media   · abierto
  8 · solicitante2 · responsable2 · MN-001 · Biblioteca              · alta    · cerrado
"""
import re

import pytest
from sqlalchemy import inspect, text

from app.cli import agregar_columnas_faltantes
from app.extensions import db
from app.models import ESTADOS, PRIORIDADES, Equipo, Rol, SolicitudMantenimiento, Ticket, Ubicacion, Usuario

from .conftest import ADMIN, RESPONSABLE1, RESPONSABLE2, SOLICITANTE1, SOLICITANTE2, entrar, login, uid
from .test_registro import datos_validos

TODOS = {1, 2, 3, 4, 5, 6, 7, 8}
VISIBLES = {
    ADMIN: TODOS,
    SOLICITANTE1: {1, 3, 5, 7},
    SOLICITANTE2: {2, 4, 6, 8},
    RESPONSABLE1: {1, 4, 5},
    RESPONSABLE2: {2, 3, 6, 8},
}

# nombre del caso -> (filtros, tickets que cumplen si se pudieran ver todos)
# Los valores que empiezan por @ se cambian por el id real antes de consultar.
CASOS = {
    "equipo": ({"equipo_id": "@equipo:IM-001"}, {1}),
    "area": ({"area_id": "@area:Laboratorio de sistemas"}, {1, 5}),
    "area_compartida": ({"area_id": "@area:Sala de profesores"}, {4, 6}),
    "solicitante": ({"solicitante_id": "@usuario:solicitante1"}, {1, 3, 5, 7}),
    "responsable": ({"responsable_id": "@usuario:responsable2"}, {2, 3, 6, 8}),
    "prioridad": ({"prioridad": "media"}, {2, 4, 7}),
    "estado": ({"estado": "abierto"}, {2, 5, 6, 7}),
    "folio_exacto": ({"folio": "@folio:3"}, {3}),
    "folio_parcial": ({"folio": "tk-"}, TODOS),
    "solicitante_y_estado": ({"solicitante_id": "@usuario:solicitante2", "estado": "abierto"}, {2, 6}),
    "prioridad_y_estado": ({"prioridad": "alta", "estado": "cerrado"}, {8}),
    "tres_filtros": ({"responsable_id": "@usuario:responsable1", "area_id": "@area:Laboratorio de sistemas", "prioridad": "baja"}, {5}),
    "sin_coincidencias": ({"prioridad": "critica", "estado": "cerrado"}, set()),
}


def resolver(app, filtros):
    """Cambia los valores @tipo:dato por el id (o folio) real de la base."""
    listo = {}
    with app.app_context():
        for clave, valor in filtros.items():
            if valor.startswith("@equipo:"):
                valor = Equipo.query.filter_by(codigo=valor[8:]).one().id
            elif valor.startswith("@area:"):
                valor = Ubicacion.query.filter_by(nombre=valor[6:]).one().id
            elif valor.startswith("@usuario:"):
                valor = Usuario.query.filter_by(identificador_acceso=valor[9:]).one().id
            elif valor.startswith("@folio:"):
                valor = SolicitudMantenimiento.query.filter_by(ticket_id=int(valor[7:])).one().folio
            listo[clave] = valor
    return listo


def ids_listados(html):
    """Ids de los tickets que aparecen en la tabla del listado."""
    return {int(n) for n in re.findall(r'href="/tickets/(\d+)"', html)}


def consultar(client, filtros=None):
    r = client.get("/tickets", query_string=filtros or {})
    assert r.status_code == 200
    return r.get_data(as_text=True)


# ---------- Criterio 1: autorización por ticket ----------
@pytest.mark.parametrize("quien", list(VISIBLES))
def test_ct01_sin_filtros_cada_persona_ve_solo_sus_tickets(client, quien):
    assert ids_listados(consultar(entrar(client, quien))) == VISIBLES[quien]


@pytest.mark.parametrize("quien", list(VISIBLES))
@pytest.mark.parametrize("caso", list(CASOS))
def test_ct02_ningun_filtro_muestra_tickets_ajenos(app, client, quien, caso):
    filtros, cumplen = CASOS[caso]
    vistos = ids_listados(consultar(entrar(client, quien), resolver(app, filtros)))
    # Exactamente los que cumplen el filtro Y además son visibles para la persona.
    assert vistos == cumplen & VISIBLES[quien]


def test_ct03_sin_sesion_el_listado_redirige_al_login(client):
    r = client.get("/tickets", query_string={"estado": "abierto"})
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_ct04_las_listas_de_filtros_no_revelan_datos_de_tickets_ajenos(client):
    html = consultar(entrar(client, SOLICITANTE1))
    # solicitante1 no participa en tickets de Samuel, ni del switch, ni de esas áreas.
    for ajeno in ("Samuel Solicitante", "SW-001", "PT-001", "Laboratorio de redes", "Biblioteca"):
        assert ajeno not in html
    for propio in ("Rosa Responsable", "Raúl Responsable", "IM-001", "Oficina administrativa"):
        assert propio in html
    client.post("/logout")
    html = consultar(entrar(client, ADMIN))
    for texto in ("Samuel Solicitante", "SW-001", "PT-001", "Laboratorio de redes", "Biblioteca"):
        assert texto in html


def test_ct05_un_ticket_nuevo_solo_aparece_en_la_consulta_de_quien_participa(app, client):
    entrar(client, SOLICITANTE1)
    r = client.post("/tickets/registrar", data=datos_validos(app, titulo="Teclado sin algunas teclas"))
    assert r.status_code == 302
    nuevo = int(r.headers["Location"].rsplit("/", 1)[1])
    assert ids_listados(consultar(client, {"estado": "abierto"})) == {5, 7, nuevo}  # nace abierto
    client.post("/logout")
    assert nuevo not in ids_listados(consultar(entrar(client, SOLICITANTE2)))
    client.post("/logout")
    assert nuevo in ids_listados(consultar(entrar(client, ADMIN)))


def test_ct06_al_asignar_un_responsable_el_ticket_entra_en_su_consulta(app, client):
    entrar(client, ADMIN).post(
        "/tickets/7/participantes", data={"usuario_id": uid(app, RESPONSABLE1), "tipo_participacion": "responsable"}
    )
    client.post("/logout")
    assert ids_listados(consultar(entrar(client, RESPONSABLE1))) == {1, 4, 5, 7}


# ---------- Criterio 2: búsqueda por folio ----------
def test_ct07_buscar_por_folio_completo_en_minusculas_o_con_espacios(app, client):
    folio = resolver(app, {"folio": "@folio:3"})["folio"]
    entrar(client, SOLICITANTE1)
    for escrito in (folio, folio.lower(), f"  {folio}  "):
        assert ids_listados(consultar(client, {"folio": escrito})) == {3}


def test_ct08_buscar_por_una_parte_del_folio(app, client):
    final = resolver(app, {"folio": "@folio:5"})["folio"][-5:]  # ej. 00005
    assert ids_listados(consultar(entrar(client, ADMIN), {"folio": final})) == {5}


def test_ct09_folio_ajeno_y_folio_inexistente_responden_igual(app, client):
    ajeno = resolver(app, {"folio": "@folio:2"})["folio"]
    entrar(client, SOLICITANTE1)
    consultar(client)  # primera visita: aquí sale (y se gasta) el aviso de bienvenida
    paginas = []
    for folio in (ajeno, "TK-2026-99999"):
        html = consultar(client, {"folio": folio})
        assert ids_listados(html) == set()
        assert "Ningún ticket coincide con los filtros" in html
        assert "Solicitud de acceso a la red wifi" not in html  # título del ticket 2
        # El token CSRF cambia con la hora: se quita para comparar solo lo visible.
        html = re.sub(r'name="csrf_token" value="[^"]*"', "", html)
        paginas.append(html.replace(folio, "FOLIO"))
    assert paginas[0] == paginas[1]  # no se puede saber si el folio existe


def test_ct10_el_folio_con_caracteres_raros_no_rompe_la_consulta(client):
    entrar(client, ADMIN)
    for folio in ("' OR 1=1 --", "<script>alert(1)</script>", "x" * 500):
        html = consultar(client, {"folio": folio})
        assert ids_listados(html) == set() and "<script>alert(1)</script>" not in html


# ---------- Criterio 3: filtros ----------
@pytest.mark.parametrize("caso", list(CASOS))
def test_ct11_cada_filtro_devuelve_lo_esperado_para_el_administrador(app, client, caso):
    filtros, cumplen = CASOS[caso]
    assert ids_listados(consultar(entrar(client, ADMIN), resolver(app, filtros))) == cumplen


@pytest.mark.parametrize("prioridad", list(PRIORIDADES))
def test_ct12_filtro_por_cada_prioridad(app, client, prioridad):
    with app.app_context():
        esperado = {s.ticket_id for s in SolicitudMantenimiento.query.filter_by(prioridad=prioridad)}
    assert ids_listados(consultar(entrar(client, ADMIN), {"prioridad": prioridad})) == esperado


@pytest.mark.parametrize("estado", list(ESTADOS))
def test_ct13_filtro_por_cada_estado(app, client, estado):
    with app.app_context():
        esperado = {s.ticket_id for s in SolicitudMantenimiento.query.filter_by(estado=estado)}
    assert esperado  # los datos de demostración tienen al menos un ticket en cada estado
    assert ids_listados(consultar(entrar(client, ADMIN), {"estado": estado})) == esperado


@pytest.mark.parametrize(
    "filtros",
    [
        {"prioridad": "urgente"},
        {"estado": "borrado"},
        {"equipo_id": "abc"},
        {"solicitante_id": ""},
        {"area_id": "1 OR 1=1"},
        {"otro_parametro": "x"},
    ],
)
def test_ct14_un_valor_que_no_sirve_se_toma_como_sin_filtro(client, filtros):
    assert ids_listados(consultar(entrar(client, SOLICITANTE1), filtros)) == VISIBLES[SOLICITANTE1]


@pytest.mark.parametrize("filtros", [{"equipo_id": 9999}, {"solicitante_id": 9999}, {"responsable_id": 9999}, {"area_id": 9999}])
def test_ct15_un_id_que_no_existe_no_muestra_nada(client, filtros):
    html = consultar(entrar(client, ADMIN), filtros)
    assert ids_listados(html) == set() and "Ningún ticket coincide con los filtros" in html


def test_ct16_filtrar_por_una_persona_ajena_no_muestra_sus_tickets(app, client):
    # solicitante1 escribe a mano el id de solicitante2 en la dirección.
    html = consultar(entrar(client, SOLICITANTE1), {"solicitante_id": uid(app, SOLICITANTE2)})
    assert ids_listados(html) == set()


def test_ct17_el_formulario_recuerda_los_filtros_y_muestra_el_conteo(app, client):
    filtros = resolver(app, {"area_id": "@area:Laboratorio de sistemas"})
    filtros.update({"prioridad": "baja", "folio": "tk"})
    html = consultar(entrar(client, ADMIN), filtros)
    assert f'<option value="{filtros["area_id"]}" selected>' in html
    assert '<option value="baja" selected>' in html and 'value="TK"' in html
    assert "1 de 8 tickets que puedes ver" in html


# ---------- Sin resultados ----------
def test_ct18_sin_coincidencias_se_explica_y_se_ofrece_limpiar(client):
    html = consultar(entrar(client, SOLICITANTE1), {"estado": "cerrado"})
    assert "Ningún ticket coincide con los filtros" in html and 'href="/tickets"' in html
    assert "Aún no participas" not in html


def test_ct19_quien_no_participa_en_nada_ve_otro_mensaje_y_no_ve_filtros(app, client):
    with app.app_context():
        nueva = Usuario(
            identificador_acceso="nueva1",
            nombre_completo="Nora Nueva",
            rol_id=Rol.query.filter_by(nombre="Solicitante").one().id,
        )
        nueva.set_password("Nueva#2026-Demo")
        db.session.add(nueva)
        db.session.commit()
    assert login(client, "nueva1", "Nueva#2026-Demo").status_code == 302
    for filtros in ({}, {"estado": "abierto"}):
        html = consultar(client, filtros)
        assert ids_listados(html) == set()
        assert 'name="folio"' not in html  # sin tickets no hay formulario de filtros
    assert "Aún no participas en ningún ticket" in consultar(client)


# ---------- Criterio 4: detalle coherente y protegido ----------
@pytest.mark.parametrize("ticket_id", sorted(TODOS))
def test_ct20_el_detalle_muestra_los_mismos_datos_que_el_listado(app, client, ticket_id):
    with app.app_context():
        s = SolicitudMantenimiento.query.filter_by(ticket_id=ticket_id).one()
        datos = [
            s.folio, s.ticket.titulo, s.equipo.codigo, s.equipo.ubicacion.nombre,
            PRIORIDADES[s.prioridad], ESTADOS[s.estado],
        ]
        personas = [p.usuario.nombre_completo for p in s.ticket.participaciones]
    entrar(client, ADMIN)
    lista = consultar(client, {"folio": datos[0]})
    assert ids_listados(lista) == {ticket_id}
    detalle = client.get(f"/tickets/{ticket_id}").get_data(as_text=True)
    for texto in datos:
        assert texto in lista and texto in detalle
    for nombre in personas:
        assert nombre in detalle


@pytest.mark.parametrize("quien", [SOLICITANTE1, SOLICITANTE2, RESPONSABLE1, RESPONSABLE2])
def test_ct21_el_detalle_esta_protegido_igual_que_el_listado(client, quien):
    entrar(client, quien)
    for ticket_id in sorted(TODOS):
        esperado = 200 if ticket_id in VISIBLES[quien] else 404
        assert client.get(f"/tickets/{ticket_id}").status_code == esperado


def test_ct22_todo_lo_que_sale_en_el_listado_se_puede_abrir(client):
    entrar(client, RESPONSABLE2)
    for ticket_id in ids_listados(consultar(client)):
        assert client.get(f"/tickets/{ticket_id}").status_code == 200


# ---------- Estado del ticket y bases creadas antes de la HU-06 ----------
def test_ct23_todo_ticket_tiene_un_estado_valido(app):
    with app.app_context():
        assert Ticket.query.count() == len(TODOS)
        for s in SolicitudMantenimiento.query:
            assert s.estado in ESTADOS


def test_ct24_una_base_anterior_recibe_la_columna_estado_sin_perder_datos(app):
    with app.app_context():
        antes = SolicitudMantenimiento.query.count()
        folios = sorted(s.folio for s in SolicitudMantenimiento.query)
        db.session.remove()
        # Se deja la tabla como estaba al terminar la HU-05 (sin la columna).
        db.session.execute(text("ALTER TABLE solicitudes_mantenimiento DROP COLUMN estado"))
        db.session.commit()
        assert "estado" not in [c["name"] for c in inspect(db.engine).get_columns("solicitudes_mantenimiento")]

        agregar_columnas_faltantes()
        agregar_columnas_faltantes()  # llamarla otra vez no hace daño

        assert "estado" in [c["name"] for c in inspect(db.engine).get_columns("solicitudes_mantenimiento")]
        assert SolicitudMantenimiento.query.count() == antes
        assert sorted(s.folio for s in SolicitudMantenimiento.query) == folios
        assert {s.estado for s in SolicitudMantenimiento.query} == {"abierto"}
