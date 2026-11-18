"""Arranque local en un solo paso: python run.py

1. Lee la configuración de .env (si existe).
2. Se conecta a MySQL/MariaDB (por defecto el de XAMPP: root sin contraseña, puerto 3306).
3. Crea la base `acceso_usuarios`, las tablas y los datos de demostración si faltan.
4. Levanta la aplicación en http://127.0.0.1:5000 y abre el navegador.
"""
import os
import sys
import threading
import webbrowser

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv es opcional
    pass

from sqlalchemy.exc import OperationalError

from app import create_app
from app.cli import preparar_bd

HOST = os.environ.get("APP_HOST", "127.0.0.1")
PORT = int(os.environ.get("APP_PORT", "5000"))
URL = f"http://{HOST}:{PORT}"


def main() -> int:
    # Evita errores de codificación en consolas de Windows antiguas.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    app = create_app()
    destino = app.config["SQLALCHEMY_DATABASE_URI"].split("@")[-1]
    print(f"→ Conectando a MySQL en {destino}")

    try:
        preparar_bd(app, sembrar=os.environ.get("SEED_DEMO", "1") == "1")
    except OperationalError as error:
        print("\n✗ No se pudo conectar a MySQL.")
        print("  · Abre el panel de XAMPP y pulsa «Start» en MySQL.")
        print("  · Si tu usuario root tiene contraseña, ponla en MYSQL_PASSWORD dentro de .env")
        print(f"  · Detalle técnico: {error.orig}")
        return 1

    print("✓ Base de datos, tablas y datos de demostración listos.")
    print(f"✓ Abre {URL}  (Ctrl+C para detener)\n")
    print("  Usuario de prueba: admin1 / Admin#2026-Demo  (más usuarios en el README)\n")

    if os.environ.get("ABRIR_NAVEGADOR", "1") == "1":
        threading.Timer(1.2, lambda: webbrowser.open(URL)).start()

    if os.environ.get("FLASK_DEBUG") == "1":
        app.run(host=HOST, port=PORT, debug=True, use_reloader=False)
    else:
        from waitress import serve  # servidor estable, funciona igual en Windows

        serve(app, host=HOST, port=PORT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
