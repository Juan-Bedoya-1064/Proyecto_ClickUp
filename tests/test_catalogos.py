"""HU-04 · Catálogos y equipos (Sprint 2).

Criterios:
  1. Consultar equipos activos.
  2. Administrar catálogos.
  3. Conservar referencias históricas al desactivar valores.
  4. Configurar periodicidad preventiva cuando aplique.
"""
import pytest

from app.extensions import db
from app.models import CategoriaServicio, Equipo, TipoEquipo, Ubicacion
from app.seed import EQUIPOS, sembrar_demo

from .conftest import ADMIN, RESPONSABLE1, SOLICITANTE1, entrar


def id_tipo(app, nombre):
    with app.app_context():
        return TipoEquipo.query.filter_by(nombre=nombre).one().id


def id_ubicacion(app, nombre):
    with app.app_context():
        return Ubicacion.query.filter_by(nombre=nombre).one().id


def id_equipo(app, codigo):
    with app.app_context():
        return Equipo.query.filter_by(codigo=codigo).one().id


def foto_catalogos(app):
    """Instantánea de catálogos y equipos para comprobar que NO cambió nada."""
    with app.app_context():
        foto = []
        for modelo in (TipoEquipo, Ubicacion, CategoriaServicio):
            foto.append([(v.id, v.nombre, v.activo) for v in modelo.query.order_by(modelo.id)])
        foto.append(
            [(e.id, e.codigo, e.nombre, e.tipo_id, e.ubicacion_id, e.activo) for e in Equipo.query.order_by(Equipo.id)]
        )
        return foto


# ---------- Criterio 1: consultar equipos activos ----------
@pytest.mark.parametrize("quien", [ADMIN, SOLICITANTE1, RESPONSABLE1])
def test_ca01_todos_los_roles_consultan_los_equipos_activos(client, quien):
    html = entrar(client, quien).get("/equipos").get_data(as_text=True)
    for codigo, _nombre, _tipo, _ubicacion, activo in EQUIPOS:
        assert (codigo in html) == activo


def test_ca02_sin_sesion_redirige_al_login(client):
    r = client.get("/equipos")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_ca03_buscar_por_codigo_y_por_nombre(client):
    entrar(client, SOLICITANTE1)
    html = client.get("/equipos?q=sw-001").get_data(as_text=True)
    assert "SW-001" in html and "PC-001" not in html
    html = client.get("/equipos?q=thinkpad").get_data(as_text=True)
    assert "PT-001" in html and "PT-002" not in html


def test_ca04_filtrar_por_tipo_y_por_ubicacion(app, client):
    entrar(client, SOLICITANTE1)
    html = client.get(f"/equipos?tipo_id={id_tipo(app, 'Impresora')}").get_data(as_text=True)
    assert "IM-001" in html and "IM-002" in html and "PC-001" not in html
    html = client.get(f"/equipos?ubicacion_id={id_ubicacion(app, 'Biblioteca')}").get_data(as_text=True)
    assert "PT-002" in html and "MN-001" in html and "IM-001" not in html


def test_ca05_busqueda_sin_resultados_muestra_mensaje(client):
    html = entrar(client, SOLICITANTE1).get("/equipos?q=zzzzzz").get_data(as_text=True)
    assert "No se encontraron equipos" in html


def test_ca06_solo_el_administrador_puede_ver_los_inactivos(client):
    html = entrar(client, SOLICITANTE1).get("/equipos?inactivos=1").get_data(as_text=True)
    assert "PC-000" not in html
    client.post("/logout")
    html = entrar(client, ADMIN).get("/equipos?inactivos=1").get_data(as_text=True)
    assert "PC-000" in html


def test_ca07_el_conjunto_inicial_no_se_duplica_al_sembrar_dos_veces(app):
    with app.app_context():
        sembrar_demo()
        assert Equipo.query.count() == len(EQUIPOS)
        assert Equipo.query.filter_by(activo=True).count() == sum(1 for e in EQUIPOS if e[4])


# ---------- Criterio 2: administrar catálogos ----------
def test_ca08_el_administrador_ve_los_tres_catalogos(client):
    html = entrar(client, ADMIN).get("/catalogos").get_data(as_text=True)
    for texto in ("Tipos de equipo", "Ubicaciones", "Categorías de servicio", "Portátil", "Biblioteca", "Hardware"):
        assert texto in html


@pytest.mark.parametrize("clave, modelo", [("tipos-equipo", TipoEquipo), ("ubicaciones", Ubicacion), ("categorias", CategoriaServicio)])
def test_ca09_alta_de_un_valor_en_cada_catalogo(app, client, clave, modelo):
    r = entrar(client, ADMIN).post(f"/catalogos/{clave}/nuevo", data={"nombre": "  Valor   de prueba "})
    assert r.status_code == 302
    with app.app_context():
        valor = modelo.query.filter_by(nombre="Valor de prueba").one()  # se guardó sin espacios de más
        assert valor.activo is True


def test_ca10_cambio_de_nombre(app, client):
    ubicacion_id = id_ubicacion(app, "Biblioteca")
    r = entrar(client, ADMIN).post(f"/catalogos/ubicaciones/{ubicacion_id}/editar", data={"nombre": "Biblioteca central"})
    assert r.status_code == 302
    with app.app_context():
        assert db.session.get(Ubicacion, ubicacion_id).nombre == "Biblioteca central"


@pytest.mark.parametrize("nombre", ["", " ", "a", "x" * 101, "biblioteca", "BIBLIOTECA"])
def test_ca11_nombre_invalido_o_repetido_se_rechaza_sin_guardar(app, client, nombre):
    antes = foto_catalogos(app)
    r = entrar(client, ADMIN).post("/catalogos/ubicaciones/nuevo", data={"nombre": nombre})
    assert r.status_code == 400
    assert foto_catalogos(app) == antes


def test_ca12_al_editar_se_puede_conservar_el_mismo_nombre(app, client):
    ubicacion_id = id_ubicacion(app, "Biblioteca")
    r = entrar(client, ADMIN).post(f"/catalogos/ubicaciones/{ubicacion_id}/editar", data={"nombre": "Biblioteca"})
    assert r.status_code == 302


def test_ca13_editar_no_permite_usar_el_nombre_de_otro_valor(app, client):
    antes = foto_catalogos(app)
    ubicacion_id = id_ubicacion(app, "Biblioteca")
    r = entrar(client, ADMIN).post(
        f"/catalogos/ubicaciones/{ubicacion_id}/editar", data={"nombre": "Sala de profesores"}
    )
    assert r.status_code == 400
    assert foto_catalogos(app) == antes


def test_ca14_catalogo_o_valor_inexistente_responde_404(client):
    entrar(client, ADMIN)
    assert client.get("/catalogos/no-existe/nuevo").status_code == 404
    assert client.post("/catalogos/no-existe/nuevo", data={"nombre": "Algo"}).status_code == 404
    assert client.get("/catalogos/ubicaciones/9999/editar").status_code == 404
    assert client.post("/catalogos/ubicaciones/9999/estado").status_code == 404


RUTAS_SOLO_ADMIN = [
    ("get", "/catalogos"),
    ("get", "/catalogos/ubicaciones/nuevo"),
    ("post", "/catalogos/ubicaciones/nuevo"),
    ("get", "/catalogos/ubicaciones/1/editar"),
    ("post", "/catalogos/ubicaciones/1/editar"),
    ("post", "/catalogos/ubicaciones/1/estado"),
    ("get", "/equipos/nuevo"),
    ("post", "/equipos/nuevo"),
    ("get", "/equipos/1/editar"),
    ("post", "/equipos/1/editar"),
    ("post", "/equipos/1/estado"),
]


@pytest.mark.parametrize("quien", [SOLICITANTE1, RESPONSABLE1])
@pytest.mark.parametrize("metodo, ruta", RUTAS_SOLO_ADMIN)
def test_ca15_quien_no_administra_recibe_403_y_no_cambia_nada(app, client, quien, metodo, ruta):
    antes = foto_catalogos(app)
    entrar(client, quien)
    r = getattr(client, metodo)(ruta, data={"nombre": "Intento", "codigo": "XX-999"} if metodo == "post" else None)
    assert r.status_code == 403
    assert foto_catalogos(app) == antes


@pytest.mark.parametrize("metodo, ruta", RUTAS_SOLO_ADMIN)
def test_ca16_sin_sesion_no_se_puede_administrar(app, client, metodo, ruta):
    antes = foto_catalogos(app)
    r = getattr(client, metodo)(ruta)
    assert r.status_code == 302 and "/login" in r.headers["Location"]
    assert foto_catalogos(app) == antes


def test_ca17_el_menu_solo_muestra_catalogos_al_administrador(client):
    html = entrar(client, SOLICITANTE1).get("/panel").get_data(as_text=True)
    assert 'href="/equipos"' in html and 'href="/catalogos"' not in html
    client.post("/logout")
    html = entrar(client, ADMIN).get("/panel").get_data(as_text=True)
    assert 'href="/equipos"' in html and 'href="/catalogos"' in html


# ---------- Criterio 3: conservar referencias históricas al desactivar ----------
def test_ca18_desactivar_no_borra_el_valor_y_se_puede_reactivar(app, client):
    tipo_id = id_tipo(app, "Impresora")
    entrar(client, ADMIN)
    assert client.post(f"/catalogos/tipos-equipo/{tipo_id}/estado").status_code == 302
    with app.app_context():
        assert db.session.get(TipoEquipo, tipo_id).activo is False  # sigue existiendo
    assert client.post(f"/catalogos/tipos-equipo/{tipo_id}/estado").status_code == 302
    with app.app_context():
        assert db.session.get(TipoEquipo, tipo_id).activo is True


def test_ca19_los_equipos_conservan_el_valor_desactivado(app, client):
    tipo_id = id_tipo(app, "Impresora")
    entrar(client, ADMIN).post(f"/catalogos/tipos-equipo/{tipo_id}/estado")
    with app.app_context():
        equipo = Equipo.query.filter_by(codigo="IM-001").one()
        assert equipo.tipo_id == tipo_id and equipo.tipo.nombre == "Impresora" and equipo.activo is True
    # El equipo sigue apareciendo en la consulta con su tipo de siempre.
    html = client.get("/equipos?q=IM-001").get_data(as_text=True)
    assert "IM-001" in html and "Impresora" in html


def test_ca20_un_valor_inactivo_no_se_ofrece_ni_se_acepta_en_equipos_nuevos(app, client):
    entrar(client, ADMIN)
    html = client.get("/equipos/nuevo").get_data(as_text=True)
    assert "Bodega antigua" not in html and "Máquina de escribir" not in html

    antes = foto_catalogos(app)
    r = client.post(
        "/equipos/nuevo",
        data={
            "codigo": "PC-900",
            "nombre": "Computador nuevo",
            "tipo_id": id_tipo(app, "Portátil"),
            "ubicacion_id": id_ubicacion(app, "Bodega antigua"),  # inactiva
        },
    )
    assert r.status_code == 400
    assert foto_catalogos(app) == antes


def test_ca21_un_equipo_existente_puede_conservar_su_valor_inactivo_al_editarlo(app, client):
    equipo_id = id_equipo(app, "PC-004")  # está en «Bodega antigua», que es inactiva
    bodega = id_ubicacion(app, "Bodega antigua")
    entrar(client, ADMIN)
    assert "Bodega antigua" in client.get(f"/equipos/{equipo_id}/editar").get_data(as_text=True)
    r = client.post(
        f"/equipos/{equipo_id}/editar",
        data={
            "codigo": "PC-004",
            "nombre": "Computador Lenovo renombrado",
            "tipo_id": id_tipo(app, "Computador de escritorio"),
            "ubicacion_id": bodega,
        },
    )
    assert r.status_code == 302
    with app.app_context():
        equipo = db.session.get(Equipo, equipo_id)
        assert equipo.nombre == "Computador Lenovo renombrado" and equipo.ubicacion_id == bodega


def test_ca22_no_existe_ninguna_ruta_para_borrar(client):
    entrar(client, ADMIN)
    assert client.delete("/catalogos/ubicaciones/1/estado").status_code == 405
    assert client.delete("/equipos/1/estado").status_code == 405
    assert client.post("/catalogos/ubicaciones/1/eliminar").status_code == 404
    assert client.post("/equipos/1/eliminar").status_code == 404


# ---------- Criterio 4: periodicidad preventiva cuando aplique ----------
def test_ca23_tipo_con_periodicidad(app, client):
    r = entrar(client, ADMIN).post("/catalogos/tipos-equipo/nuevo", data={"nombre": "Servidor", "periodicidad": "4"})
    assert r.status_code == 302
    with app.app_context():
        assert TipoEquipo.query.filter_by(nombre="Servidor").one().periodicidad_meses == 4


def test_ca24_tipo_sin_periodicidad_queda_como_no_aplica(app, client):
    r = entrar(client, ADMIN).post("/catalogos/tipos-equipo/nuevo", data={"nombre": "Teclado", "periodicidad": ""})
    assert r.status_code == 302
    with app.app_context():
        assert TipoEquipo.query.filter_by(nombre="Teclado").one().periodicidad_meses is None


def test_ca25_cambiar_y_quitar_la_periodicidad(app, client):
    tipo_id = id_tipo(app, "Impresora")
    entrar(client, ADMIN)
    client.post(f"/catalogos/tipos-equipo/{tipo_id}/editar", data={"nombre": "Impresora", "periodicidad": "2"})
    with app.app_context():
        assert db.session.get(TipoEquipo, tipo_id).periodicidad_meses == 2
    client.post(f"/catalogos/tipos-equipo/{tipo_id}/editar", data={"nombre": "Impresora", "periodicidad": ""})
    with app.app_context():
        assert db.session.get(TipoEquipo, tipo_id).periodicidad_meses is None


@pytest.mark.parametrize("valor", ["0", "-3", "61", "1.5", "abc", "9999", "²"])
def test_ca26_periodicidad_invalida_se_rechaza_sin_guardar(app, client, valor):
    antes = foto_catalogos(app)
    r = entrar(client, ADMIN).post("/catalogos/tipos-equipo/nuevo", data={"nombre": "Servidor", "periodicidad": valor})
    assert r.status_code == 400
    assert foto_catalogos(app) == antes


def test_ca27_la_consulta_de_equipos_muestra_la_periodicidad_del_tipo(client):
    entrar(client, SOLICITANTE1)
    assert "Cada 3 meses" in client.get("/equipos?q=IM-001").get_data(as_text=True)  # impresora
    assert "No aplica" in client.get("/equipos?q=MN-001").get_data(as_text=True)  # monitor


def test_ca28_los_otros_catalogos_ignoran_la_periodicidad(app, client):
    r = entrar(client, ADMIN).post("/catalogos/ubicaciones/nuevo", data={"nombre": "Auditorio", "periodicidad": "abc"})
    assert r.status_code == 302
    with app.app_context():
        assert Ubicacion.query.filter_by(nombre="Auditorio").count() == 1


# ---------- Equipos: reglas de alta, cambio y desactivación ----------
def test_ca29_alta_de_equipo(app, client):
    r = entrar(client, ADMIN).post(
        "/equipos/nuevo",
        data={
            "codigo": " pt-010 ",
            "nombre": "Portátil Asus VivoBook",
            "tipo_id": id_tipo(app, "Portátil"),
            "ubicacion_id": id_ubicacion(app, "Biblioteca"),
        },
    )
    assert r.status_code == 302
    with app.app_context():
        equipo = Equipo.query.filter_by(codigo="PT-010").one()  # el código se guarda en mayúsculas
        assert equipo.activo is True and equipo.tipo.nombre == "Portátil"
    assert "PT-010" in client.get("/equipos").get_data(as_text=True)


@pytest.mark.parametrize(
    "cambios",
    [
        {"codigo": ""},
        {"codigo": "ab"},
        {"codigo": "PC 900"},
        {"codigo": "pc-001"},  # repetido
        {"nombre": ""},
        {"nombre": "x" * 151},
        {"tipo_id": ""},
        {"tipo_id": "9999"},
        {"ubicacion_id": ""},
        {"ubicacion_id": "abc"},
    ],
)
def test_ca30_equipo_invalido_se_rechaza_sin_guardar(app, client, cambios):
    datos = {
        "codigo": "PC-900",
        "nombre": "Computador nuevo",
        "tipo_id": id_tipo(app, "Portátil"),
        "ubicacion_id": id_ubicacion(app, "Biblioteca"),
    }
    datos.update(cambios)
    antes = foto_catalogos(app)
    r = entrar(client, ADMIN).post("/equipos/nuevo", data=datos)
    assert r.status_code == 400
    assert foto_catalogos(app) == antes


def test_ca31_desactivar_un_equipo_lo_quita_de_la_consulta_sin_borrarlo(app, client):
    equipo_id = id_equipo(app, "PC-001")
    entrar(client, ADMIN)
    assert client.post(f"/equipos/{equipo_id}/estado").status_code == 302
    with app.app_context():
        assert db.session.get(Equipo, equipo_id).activo is False
    fila = "<td>PC-001</td>"  # la fila de la tabla (el aviso de arriba también nombra el código)
    assert fila not in client.get("/equipos").get_data(as_text=True)
    assert fila in client.get("/equipos?inactivos=1").get_data(as_text=True)
    client.post(f"/equipos/{equipo_id}/estado")
    assert fila in client.get("/equipos").get_data(as_text=True)


def test_ca32_equipo_inexistente_responde_404(client):
    entrar(client, ADMIN)
    assert client.get("/equipos/9999/editar").status_code == 404
    assert client.post("/equipos/9999/estado").status_code == 404


def test_ca33_con_csrf_activo_un_post_sin_token_se_rechaza():
    from app import create_app

    from .conftest import CLAVES, ConfigCsrf

    app_csrf = create_app(ConfigCsrf)
    with app_csrf.app_context():
        db.drop_all()
        db.create_all()
        sembrar_demo()
    cliente = app_csrf.test_client()
    # Con CSRF activo el login también pide token: se toma del formulario.
    html = cliente.get("/login").get_data(as_text=True)
    token = html.split('name="csrf_token" value="')[1].split('"')[0]
    r = cliente.post("/login", data={"identificador": ADMIN, "password": CLAVES[ADMIN], "csrf_token": token})
    assert r.status_code == 302
    r = cliente.post("/catalogos/ubicaciones/nuevo", data={"nombre": "Sin token"})
    assert r.status_code == 400
    with app_csrf.app_context():
        assert Ubicacion.query.filter_by(nombre="Sin token").count() == 0
