import re
from datetime import date

ID_RE = re.compile(r"^[a-z0-9._@+\-]{3,100}$")
MAX_PASSWORD = 128  # evita hashear cadenas gigantes (DoS)
TITULO_MIN, TITULO_MAX = 3, 200


def validar_credenciales(identificador_raw, password_raw):
    """Valida solo el *formato* de lo enviado; no dice nada sobre si la cuenta existe.

    Devuelve (identificador_normalizado, password, errores).
    """
    errores = {}
    identificador = (identificador_raw or "").strip().lower()
    password = password_raw or ""

    if not identificador:
        errores["identificador"] = "Escribe tu identificador de acceso."
    elif not ID_RE.match(identificador):
        errores["identificador"] = (
            "Usa de 3 a 100 caracteres: letras, números y . _ @ + -"
        )

    if not password:
        errores["password"] = "Escribe tu contraseña."
    elif len(password) > MAX_PASSWORD:
        errores["password"] = f"La contraseña no puede superar {MAX_PASSWORD} caracteres."

    return identificador, password, errores


def validar_titulo(titulo_raw):
    """Devuelve (titulo_limpio, error|None)."""
    titulo = " ".join((titulo_raw or "").split())
    if len(titulo) < TITULO_MIN:
        return titulo, f"El título debe tener al menos {TITULO_MIN} caracteres."
    if len(titulo) > TITULO_MAX:
        return titulo, f"El título no puede superar {TITULO_MAX} caracteres."
    return titulo, None


# --- Sprint 2 · HU-04 Catálogos y equipos ---
CODIGO_EQUIPO_RE = re.compile(r"^[A-Z0-9\-]{3,30}$")
NOMBRE_CATALOGO_MIN, NOMBRE_CATALOGO_MAX = 2, 100
NOMBRE_EQUIPO_MIN, NOMBRE_EQUIPO_MAX = 3, 150
PERIODICIDAD_MIN, PERIODICIDAD_MAX = 1, 60  # meses


def validar_nombre_catalogo(nombre_raw):
    """Devuelve (nombre_limpio, error|None)."""
    nombre = " ".join((nombre_raw or "").split())
    if len(nombre) < NOMBRE_CATALOGO_MIN:
        return nombre, f"El nombre debe tener al menos {NOMBRE_CATALOGO_MIN} caracteres."
    if len(nombre) > NOMBRE_CATALOGO_MAX:
        return nombre, f"El nombre no puede superar {NOMBRE_CATALOGO_MAX} caracteres."
    return nombre, None


def validar_periodicidad(valor_raw):
    """Periodicidad preventiva en meses. Vacío = no aplica. Devuelve (meses|None, error|None)."""
    valor = (valor_raw or "").strip()
    if valor == "":
        return None, None
    # Solo dígitos 0-9 (isdigit sola acepta caracteres raros como "²").
    if not (valor.isascii() and valor.isdigit() and len(valor) <= 3):
        return None, "Escribe un número entero de meses, o deja el campo vacío si no aplica."
    meses = int(valor)
    if meses < PERIODICIDAD_MIN or meses > PERIODICIDAD_MAX:
        return None, f"La periodicidad debe estar entre {PERIODICIDAD_MIN} y {PERIODICIDAD_MAX} meses."
    return meses, None


# --- Sprint 2 · HU-05 Registro de ticket ---
SITUACION_MIN, SITUACION_MAX = 10, 2000
DETECTOR_MIN, DETECTOR_MAX = 3, 150
EVIDENCIA_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
# Extensión permitida -> primeros bytes que debe tener un archivo real de ese tipo.
FIRMAS_EVIDENCIA = {
    "jpg": b"\xff\xd8\xff",
    "jpeg": b"\xff\xd8\xff",
    "png": b"\x89PNG\r\n\x1a\n",
    "pdf": b"%PDF-",
}


def validar_situacion(texto_raw):
    """Devuelve (texto_limpio, error|None). Conserva los saltos de línea."""
    texto = (texto_raw or "").replace("\r\n", "\n").strip()
    if len(texto) < SITUACION_MIN:
        return texto, f"Describe la situación con al menos {SITUACION_MIN} caracteres."
    if len(texto) > SITUACION_MAX:
        return texto, f"La situación no puede superar {SITUACION_MAX} caracteres."
    return texto, None


def validar_detector(nombre_raw):
    """Devuelve (nombre_limpio, error|None)."""
    nombre = " ".join((nombre_raw or "").split())
    if len(nombre) < DETECTOR_MIN:
        return nombre, "Escribe el nombre de quien detectó el problema."
    if len(nombre) > DETECTOR_MAX:
        return nombre, f"El nombre no puede superar {DETECTOR_MAX} caracteres."
    return nombre, None


def validar_fecha_deteccion(fecha_raw, hoy):
    """Fecha en formato AAAA-MM-DD que no sea futura. Devuelve (date|None, error|None)."""
    try:
        fecha = date.fromisoformat(fecha_raw or "")
    except ValueError:
        return None, "Elige la fecha en que se detectó el problema."
    if fecha > hoy:
        return None, "La fecha de detección no puede ser futura."
    return fecha, None


def validar_evidencia(nombre_archivo, contenido):
    """Revisa extensión, tamaño y contenido real. Devuelve (extension|None, error|None)."""
    extension = nombre_archivo.rsplit(".", 1)[-1].lower() if "." in nombre_archivo else ""
    if extension not in FIRMAS_EVIDENCIA:
        return None, "Solo se permiten archivos JPG, PNG o PDF."
    if len(contenido) == 0:
        return None, "El archivo está vacío."
    if len(contenido) > EVIDENCIA_MAX_BYTES:
        return None, "El archivo supera el máximo de 10 MB."
    if not contenido.startswith(FIRMAS_EVIDENCIA[extension]):
        return None, "El contenido del archivo no corresponde a un JPG, PNG o PDF válido."
    return extension, None


def validar_codigo_equipo(codigo_raw):
    """Devuelve (codigo_en_mayúsculas, error|None)."""
    codigo = (codigo_raw or "").strip().upper()
    if not CODIGO_EQUIPO_RE.match(codigo):
        return codigo, "Usa de 3 a 30 caracteres: letras, números y guion (ej. PC-001)."
    return codigo, None


def validar_nombre_equipo(nombre_raw):
    """Devuelve (nombre_limpio, error|None)."""
    nombre = " ".join((nombre_raw or "").split())
    if len(nombre) < NOMBRE_EQUIPO_MIN:
        return nombre, f"El nombre debe tener al menos {NOMBRE_EQUIPO_MIN} caracteres."
    if len(nombre) > NOMBRE_EQUIPO_MAX:
        return nombre, f"El nombre no puede superar {NOMBRE_EQUIPO_MAX} caracteres."
    return nombre, None
