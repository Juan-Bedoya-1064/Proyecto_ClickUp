import os
from urllib.parse import quote_plus


def _url_mysql() -> str:
    """URL de conexión a MySQL/MariaDB.

    Si existe DATABASE_URL se usa tal cual. Si no, se arma con las variables MYSQL_*;
    los valores por defecto son los de XAMPP (usuario root sin contraseña en localhost:3306).
    """
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    usuario = os.environ.get("MYSQL_USER", "root")
    clave = quote_plus(os.environ.get("MYSQL_PASSWORD", ""))
    host = os.environ.get("MYSQL_HOST", "127.0.0.1")
    puerto = os.environ.get("MYSQL_PORT", "3306")
    base = os.environ.get("MYSQL_DATABASE", "acceso_usuarios")
    return f"mysql+pymysql://{usuario}:{clave}@{host}:{puerto}/{base}?charset=utf8mb4"


class Config:
    APP_NAME = "Acceso Seguro"
    # La BD guarda UTC; en pantalla se muestra la hora de esta zona.
    ZONA_HORARIA = os.environ.get("ZONA_HORARIA", "America/Bogota")
    SECRET_KEY = os.environ.get("SECRET_KEY", "clave-solo-para-desarrollo")
    SQLALCHEMY_DATABASE_URI = _url_mysql()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # MySQL cierra conexiones inactivas (wait_timeout): se comprueban antes de usarlas
    # y se reciclan cada 5 minutos para evitar el error «MySQL server has gone away».
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}

    # Sesión
    SESSION_MINUTES = int(os.environ.get("SESSION_MINUTES", "30"))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"

    # Límite global de carga (adjuntos máx. 10 MB)
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024

    # Sprint 2 · HU-05: carpeta donde se guarda la evidencia de los tickets.
    # Está fuera de app/static, así que nadie la puede abrir con una dirección directa.
    CARPETA_ADJUNTOS = os.environ.get(
        "CARPETA_ADJUNTOS",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "adjuntos"),
    )

    WTF_CSRF_TIME_LIMIT = None  # el token vive lo que dure la sesión


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "clave-de-pruebas"
    # Por defecto SQLite en memoria (rápido, sin servidor).
    # Con TEST_DATABASE_URL se prueba contra MySQL real, por ejemplo:
    #   TEST_DATABASE_URL="mysql+pymysql://root:@127.0.0.1:3306/acceso_usuarios_test?charset=utf8mb4"
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:")
    SQLALCHEMY_ENGINE_OPTIONS = (
        {"pool_pre_ping": True, "pool_recycle": 280} if os.environ.get("TEST_DATABASE_URL") else {}
    )
    WTF_CSRF_ENABLED = False
