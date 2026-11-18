import click
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL, make_url

from .extensions import db
from .seed import sembrar_demo


def asegurar_base_datos(uri: str) -> None:
    """Crea la base de datos MySQL/MariaDB si todavía no existe.

    Se conecta al servidor sin elegir base (así funciona aunque esté vacío, como un
    XAMPP recién instalado) y ejecuta CREATE DATABASE IF NOT EXISTS en utf8mb4.
    Con otros motores (SQLite en las pruebas) no hace nada.
    """
    url = make_url(uri)
    if not url.drivername.startswith(("mysql", "mariadb")):
        return
    nombre = url.database
    if not nombre or "`" in nombre:
        raise click.ClickException(f"Nombre de base de datos no válido: {nombre!r}")
    # URL igual pero sin base de datos (url.set(database=None) no la quita).
    servidor = URL.create(
        url.drivername, url.username, url.password, url.host, url.port, None, url.query
    )
    motor = create_engine(servidor, pool_pre_ping=True)
    try:
        with motor.begin() as con:
            con.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS `{nombre}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            )
    finally:
        motor.dispose()


def agregar_columnas_faltantes() -> None:
    """Sprint 2 · HU-06: create_all() crea tablas nuevas pero no cambia las que ya existen.

    Si la base se creó antes de la HU-06, aquí se agrega la columna `estado`.
    """
    columnas = [c["name"] for c in inspect(db.engine).get_columns("solicitudes_mantenimiento")]
    if "estado" not in columnas:
        db.session.execute(
            text("ALTER TABLE solicitudes_mantenimiento ADD COLUMN estado VARCHAR(20) NOT NULL DEFAULT 'abierto'")
        )
        db.session.commit()


def preparar_bd(app, sembrar: bool = True) -> None:
    """Base de datos + tablas + (opcional) datos de demostración. Idempotente."""
    asegurar_base_datos(app.config["SQLALCHEMY_DATABASE_URI"])
    with app.app_context():
        db.create_all()
        agregar_columnas_faltantes()
        if sembrar:
            sembrar_demo()


def registrar_comandos(app):
    @app.cli.command("init-db")
    def init_db():
        """Crea la base de datos (si falta) y las tablas que falten."""
        asegurar_base_datos(app.config["SQLALCHEMY_DATABASE_URI"])
        db.create_all()
        agregar_columnas_faltantes()
        click.echo("Base de datos y tablas listas.")

    @app.cli.command("seed-demo")
    def seed_demo():
        """Carga roles, permisos, usuarios y tickets ficticios (idempotente)."""
        sembrar_demo()
        click.echo("Datos de demostración listos.")
