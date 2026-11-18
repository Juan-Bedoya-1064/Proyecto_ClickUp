"""Genera el diagrama de secuencia del Sprint 1 (SVG + Mermaid) desde una sola definición.

Uso:  python docs/generar_diagrama.py
Edita la lista EVENTOS (al final) para ajustar mensajes o nombres de rutas.
"""
from html import escape
from pathlib import Path

AQUI = Path(__file__).parent

# ---------------------------------------------------------------- participantes
PART = [
    ("Usuario", "según su rol"),
    ("Navegador", "cliente"),
    ("Flask", "auth · tickets · main"),
    ("security.py", "sesión del servidor"),
    ("autorizacion.py", "roles y participación"),
    ("MySQL", "base de datos"),
]
U, N, F, S, A, D = range(6)
X = [120, 345, 640, 925, 1195, 1445]
ANCHO = 1570

# ---------------------------------------------------------------- estilo
INK, MUTED, LINE = "#10222b", "#5a6d76", "#9db0b7"
ROJO, VERDE, PETROLEO = "#a42a1f", "#1f6b4d", "#1d4e5a"
SECCIONES = {"HU-01": "#1d4e5a", "HU-02": "#3b4a8f", "HU-03": "#6a4a1f"}
FUENTE = "Helvetica Neue, Arial, DejaVu Sans, sans-serif"
CHAR = 6.9  # ancho medio por carácter a 12 px (estimación conservadora)


def envolver(texto, max_chars):
    palabras, lineas, actual = texto.split(), [], ""
    for p in palabras:
        if len(actual) + len(p) + (1 if actual else 0) <= max_chars:
            actual = f"{actual} {p}".strip()
        else:
            lineas.append(actual)
            actual = p
    lineas.append(actual)
    return lineas


# ---------------------------------------------------------------- DSL de eventos
EVENTOS = []


def seccion(codigo, titulo):
    EVENTOS.append(("seccion", codigo, titulo))


def flujo(titulo):
    EVENTOS.append(("flujo", titulo))


def msg(a, b, texto, tipo="req"):
    EVENTOS.append(("msg", a, b, texto, tipo))


def propio(a, texto):
    EVENTOS.append(("propio", a, texto))


def nota(a, b, texto):
    EVENTOS.append(("nota", a, b, texto))


def alt(cond):
    EVENTOS.append(("alt", cond))


def sino(cond):
    EVENTOS.append(("sino", cond))


def fin():
    EVENTOS.append(("fin",))


# ---------------------------------------------------------------- render SVG
def svg():
    atras, medio, frente = [], [], []
    y = 140
    num = 0
    pila = []  # (y_inicio, profundidad, condición)
    sec_color = PETROLEO

    def t(x, y_, s, size=12, color=INK, anchor="middle", peso="normal", fondo=False, cursiva=False):
        w = len(s) * CHAR * size / 12 + 8
        if fondo:
            x0 = x - w / 2 if anchor == "middle" else (x - 4 if anchor == "start" else x - w + 4)
            frente.append(f'<rect x="{x0:.1f}" y="{y_ - size:.1f}" width="{w:.1f}" height="{size + 5}" fill="#fff" opacity=".88"/>')
        estilo = ' font-style="italic"' if cursiva else ""
        frente.append(
            f'<text x="{x:.1f}" y="{y_:.1f}" font-size="{size}" fill="{color}" text-anchor="{anchor}" '
            f'font-weight="{peso}"{estilo}>{escape(s)}</text>'
        )

    for ev in EVENTOS:
        k = ev[0]
        if k == "seccion":
            _, cod, titulo = ev
            sec_color = SECCIONES[cod]
            num = 0
            y += 16
            atras.append(f'<rect x="20" y="{y}" width="{ANCHO - 40}" height="40" rx="8" fill="{sec_color}"/>')
            frente.append(
                f'<text x="40" y="{y + 26}" font-size="16" font-weight="700" fill="#fff">{escape(cod)}</text>'
                f'<text x="104" y="{y + 26}" font-size="15" fill="#fff">{escape(titulo)}</text>'
            )
            y += 70
        elif k == "flujo":
            frente.append(f'<text x="{X[1] - 70}" y="{y}" font-size="13" font-weight="700" fill="{sec_color}">{escape(ev[1])}</text>')
            frente.append(f'<line x1="{X[1] - 70}" y1="{y + 7}" x2="{ANCHO - 40}" y2="{y + 7}" stroke="{sec_color}" stroke-width="1" opacity=".35"/>')
            y += 38
        elif k == "msg":
            _, a, b, texto, tipo = ev
            num += 1
            x1, x2 = X[a], X[b]
            color = {"req": INK, "res": MUTED, "err": ROJO, "ok": VERDE}[tipo]
            dash = ' stroke-dasharray="6 4"' if tipo != "req" else ""
            span = abs(x2 - x1)
            lineas = envolver(f"{num}. {texto}", max(14, int((span - 26) / CHAR)))
            alto = len(lineas) * 15
            ytxt = y
            for i, l in enumerate(lineas):
                t((x1 + x2) / 2, ytxt + i * 15, l, color=color, fondo=True)
            ya = y + alto + 4
            d = 1 if x2 > x1 else -1
            marker = f"flecha-{tipo}"
            frente.append(
                f'<line x1="{x1 + 6 * d}" y1="{ya}" x2="{x2 - 7 * d}" y2="{ya}" stroke="{color}" stroke-width="1.6"{dash} marker-end="url(#{marker})"/>'
            )
            y = ya + 24
        elif k == "propio":
            _, a, texto = ev
            num += 1
            x0 = X[a]
            lineas = envolver(f"{num}. {texto}", 34)
            alto = len(lineas) * 15 + 8
            frente.append(
                f'<path d="M{x0 + 6} {y} h34 v{alto} h-30" fill="none" stroke="{INK}" stroke-width="1.6" marker-end="url(#flecha-req)"/>'
            )
            for i, l in enumerate(lineas):
                t(x0 + 48, y + 14 + i * 15, l, anchor="start", fondo=True)
            y += alto + 24
        elif k == "nota":
            _, a, b, texto = ev
            x1, x2 = X[a] - 90, X[b] + 90
            lineas = envolver(texto, int((x2 - x1 - 24) / CHAR))
            alto = len(lineas) * 15 + 16
            frente.append(f'<rect x="{x1}" y="{y}" width="{x2 - x1}" height="{alto}" rx="6" fill="#fff6dd" stroke="#e7a21d" stroke-width="1"/>')
            for i, l in enumerate(lineas):
                t(x1 + 12, y + 19 + i * 15, l, anchor="start", color="#5b4300")
            y += alto + 20
        elif k == "alt":
            pila.append([y - 4, len(pila), ev[1], []])
            y += 8
            y_etq = y
            _tag(frente, pila[-1], X, y_etq, t)
            y += 44
        elif k == "sino":
            g = pila[-1]
            y += 2
            inset = 12 * g[1]
            izq, der = X[1] - 70 + inset, X[5] + 70 - inset
            frente.append(f'<line x1="{izq}" y1="{y}" x2="{der}" y2="{y}" stroke="{LINE}" stroke-width="1.2" stroke-dasharray="7 5"/>')
            g[3].append(y)
            t(izq + 10, y + 18, f"[{ev[1]}]", size=12, color=MUTED, anchor="start", peso="600", fondo=True)
            y += 44
        elif k == "fin":
            g = pila.pop()
            inset = 12 * g[1]
            izq, der = X[1] - 70 + inset, X[5] + 70 - inset
            medio.append(
                f'<rect x="{izq}" y="{g[0]}" width="{der - izq}" height="{y - g[0] - 4}" rx="6" fill="none" stroke="{LINE}" stroke-width="1.3"/>'
            )
            y += 28

    alto_total = y + 120
    cab = _cabeceras(60)
    pie = _cabeceras(y + 20)
    vidas = "".join(
        f'<line x1="{x}" y1="112" x2="{x}" y2="{y + 20}" stroke="{LINE}" stroke-width="1.2" stroke-dasharray="3 5"/>' for x in X
    )
    defs = "<defs>" + "".join(
        f'<marker id="flecha-{n}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
        f'<path d="M0 0 L10 5 L0 10 z" fill="{c}"/></marker>'
        for n, c in [("req", INK), ("res", MUTED), ("err", ROJO), ("ok", VERDE)]
    ) + "</defs>"
    titulo = (
        f'<text x="30" y="34" font-size="22" font-weight="700" fill="{INK}">Sprint 1 · Acceso y usuarios</text>'
        f'<text x="30" y="56" font-size="13" fill="{MUTED}">Diagrama de secuencia de HU-01, HU-02 y HU-03 · nombres de rutas, funciones y tablas tal como están en el código</text>'
    )
    leyenda = (
        f'<g font-size="12" fill="{MUTED}">'
        f'<line x1="{ANCHO - 520}" y1="40" x2="{ANCHO - 490}" y2="40" stroke="{INK}" stroke-width="1.6"/><text x="{ANCHO - 484}" y="44">petición</text>'
        f'<line x1="{ANCHO - 410}" y1="40" x2="{ANCHO - 380}" y2="40" stroke="{MUTED}" stroke-width="1.6" stroke-dasharray="6 4"/><text x="{ANCHO - 374}" y="44">respuesta</text>'
        f'<line x1="{ANCHO - 290}" y1="40" x2="{ANCHO - 260}" y2="40" stroke="{VERDE}" stroke-width="1.6" stroke-dasharray="6 4"/><text x="{ANCHO - 254}" y="44">permitido</text>'
        f'<line x1="{ANCHO - 170}" y1="40" x2="{ANCHO - 140}" y2="40" stroke="{ROJO}" stroke-width="1.6" stroke-dasharray="6 4"/><text x="{ANCHO - 134}" y="44">rechazado</text></g>'
    )
    cuerpo = "\n".join(atras + [vidas] + medio + frente)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{ANCHO}" height="{alto_total}" viewBox="0 0 {ANCHO} {alto_total}" '
        f'font-family="{FUENTE}"><rect width="100%" height="100%" fill="#ffffff"/>{defs}{titulo}{leyenda}{cab}\n{cuerpo}\n{pie}</svg>'
    )


def _tag(frente, grupo, X, y, t):
    inset = 12 * grupo[1]
    izq = X[1] - 70 + inset
    frente.append(f'<path d="M{izq} {y - 2} h46 v16 l-8 8 h-38 z" fill="{LINE}" opacity=".55"/>')
    frente.append(f'<text x="{izq + 8}" y="{y + 15}" font-size="12" font-weight="700" fill="{INK}">alt</text>')
    t(izq + 60, y + 16, f"[{grupo[2]}]", size=12, color=MUTED, anchor="start", peso="600", fondo=True)


def _cabeceras(y):
    out = []
    for i, (nombre, sub) in enumerate(PART):
        w = 170
        x = X[i] - w / 2
        out.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="46" rx="8" fill="{INK}"/>'
            f'<text x="{X[i]}" y="{y + 20}" font-size="14" font-weight="700" fill="#fff" text-anchor="middle">{escape(nombre)}</text>'
            f'<text x="{X[i]}" y="{y + 36}" font-size="10.5" fill="#9fb7bf" text-anchor="middle">{escape(sub if len(sub) < 28 else sub[:27] + "…")}</text>'
        )
    return "".join(out)


# ---------------------------------------------------------------- render Mermaid
def mermaid():
    nombres = ["U", "N", "F", "S", "A", "D"]
    etiquetas = ["Usuario", "Navegador", "Flask (rutas)", "security.py", "autorizacion.py", "MySQL"]
    limpio = lambda s: s.replace(";", ",").replace("#", "").replace("{", "(").replace("}", ")")
    L = ["sequenceDiagram", "    autonumber"]
    L += [f"    participant {n} as {e}" for n, e in zip(nombres, etiquetas)]
    ind = 1
    for ev in EVENTOS:
        k = ev[0]
        pad = "    " * ind
        if k == "seccion":
            L.append(f"{pad}Note over U,D: {ev[1]} · {limpio(ev[2])}")
        elif k == "flujo":
            L.append(f"{pad}Note over N,F: {limpio(ev[1])}")
        elif k == "msg":
            _, a, b, texto, tipo = ev
            flecha = "->>" if tipo == "req" else "-->>"
            L.append(f"{pad}{nombres[a]}{flecha}{nombres[b]}: {limpio(texto)}")
        elif k == "propio":
            L.append(f"{pad}{nombres[ev[1]]}->>{nombres[ev[1]]}: {limpio(ev[2])}")
        elif k == "nota":
            L.append(f"{pad}Note over {nombres[ev[1]]},{nombres[ev[2]]}: {limpio(ev[3])}")
        elif k == "alt":
            L.append(f"{pad}alt {limpio(ev[1])}")
            ind += 1
        elif k == "sino":
            L.append("    " * (ind - 1) + f"else {limpio(ev[1])}")
        elif k == "fin":
            ind -= 1
            L.append("    " * ind + "end")
    return "\n".join(L) + "\n"


# ================================================================ DEFINICIÓN DEL DIAGRAMA
# ---------------------------------------------------------------- HU-01
seccion("HU-01", "Iniciar y cerrar sesión")

flujo("Iniciar sesión")
msg(U, N, "Escribe su identificador de acceso y su contraseña")
msg(N, F, "POST /login (identificador, password, csrf_token)")
propio(F, "validar_credenciales(): solo valida el formato")
alt("formato inválido")
msg(F, N, "400 · mensaje por campo", "err")
sino("formato válido")
msg(F, D, "SELECT usuarios WHERE identificador_acceso = ?")
msg(D, F, "fila del usuario, o ninguna", "res")
propio(F, "autenticar(): compara contrasena_hash (siempre verifica un hash) y revisa activo")
alt("cuenta inexistente, contraseña incorrecta o cuenta inactiva")
msg(F, N, "401 · «Identificador o contraseña incorrectos.» (el mismo mensaje en los tres casos)", "err")
sino("credenciales válidas y cuenta activa")
msg(F, S, "iniciar_sesion(usuario)")
msg(S, D, "INSERT sesiones (token_hash, expira_en)")
msg(F, N, "302 /panel + cookie HttpOnly con el token (en la base solo se guarda su hash)", "ok")
fin()
fin()

flujo("Cerrar sesión")
msg(N, F, "POST /logout (csrf_token)")
msg(F, S, "cerrar_sesion()")
msg(S, D, "UPDATE sesiones SET cerrada_en = ahora")
msg(F, N, "302 /login + cookie borrada", "res")
msg(N, F, "GET /panel con la cookie anterior")
msg(F, S, "cargar_usuario(): busca la sesión por token_hash")
msg(S, D, "SELECT sesiones WHERE token_hash = ?")
msg(D, S, "sesión con cerrada_en", "res")
msg(F, N, "302 /login · sin acceso a funciones protegidas", "err")

# ---------------------------------------------------------------- HU-02
seccion("HU-02", "Control de acceso por rol y participación en el ticket")
nota(N, D, "En cada petición, antes de la ruta: cargar_usuario() exige sesión no cerrada, no vencida y cuenta activa (usuarios.activo). Si falla, 302 /login. Los rechazos de abajo ocurren ANTES de escribir, por eso la base de datos no cambia.")

flujo("Ver un ticket (también por acceso directo a la URL)")
msg(N, F, "GET /tickets/{id}")
msg(F, A, "permiso_required('tickets.ver')")
msg(A, D, "SELECT permisos del rol (roles_permisos)")
alt("el rol no tiene tickets.ver")
msg(F, N, "403 · «Tu rol no permite esta acción»", "err")
sino("el rol tiene tickets.ver")
msg(F, A, "ticket_visible_o_404(id)")
msg(A, D, "SELECT tickets + participaciones_ticket")
alt("no existe, o no participa y no tiene tickets.ver_todos")
msg(F, N, "404 · misma respuesta en ambos casos (no revela si existe)", "err")
sino("participa en el ticket o tiene tickets.ver_todos")
msg(F, N, "200 · detalle del ticket y sus participantes", "ok")
fin()
fin()

flujo("Editar el título de un ticket")
msg(N, F, "POST /tickets/{id}/editar (titulo)")
msg(F, A, "permiso_required('tickets.editar') y ticket_editable_o_error(id)")
msg(A, D, "SELECT permisos, tickets y participaciones_ticket")
alt("el rol no tiene tickets.editar")
msg(F, N, "403", "err")
sino("no existe, o no participa y no tiene tickets.ver_todos")
msg(F, N, "404", "err")
sino("ve el ticket, pero no es responsable y no tiene tickets.editar_todos")
msg(F, N, "403", "err")
sino("es responsable del ticket, o tiene tickets.editar_todos")
propio(F, "validar_titulo(): de 3 a 200 caracteres")
alt("título inválido")
msg(F, N, "400 · mensaje en el campo", "err")
sino("título válido")
msg(F, D, "UPDATE tickets SET titulo")
msg(F, N, "302 /tickets/{id}", "ok")
fin()
fin()

flujo("Crear un ticket (Solicitante o Administrador)")
msg(N, F, "POST /tickets/registrar (formulario)")
msg(F, A, "permiso_required('tickets.crear')")
msg(A, D, "SELECT permisos del rol (roles_permisos)")
alt("el rol no tiene tickets.crear (por ejemplo, Responsable)")
msg(F, N, "403", "err")
sino("el rol tiene tickets.crear")
msg(F, D, "INSERT tickets + INSERT participaciones_ticket (quien crea queda como solicitante)")
msg(F, N, "302 /tickets/{id}", "ok")
fin()

flujo("Asignar una persona a un ticket (Administrador)")
msg(N, F, "POST /tickets/{id}/participantes (usuario_id, tipo_participacion)")
msg(F, A, "permiso_required('tickets.asignar')")
msg(A, D, "SELECT permisos del rol (roles_permisos)")
alt("el rol no tiene tickets.asignar")
msg(F, N, "403", "err")
sino("el rol tiene tickets.asignar")
propio(F, "valida tipo (solicitante o responsable), cuenta activa y rol compatible")
alt("datos inválidos")
msg(F, N, "400 · mensaje", "err")
sino("datos válidos")
msg(F, D, "INSERT participaciones_ticket (ticket_id, usuario_id, tipo_participacion)")
alt("ya existe esa participación (índice único)")
msg(F, N, "409 · «Esa persona ya participa en el ticket con ese tipo»", "err")
sino("participación nueva")
msg(F, N, "302 /tickets/{id}", "ok")
fin()
fin()
fin()

# ---------------------------------------------------------------- HU-03
seccion("HU-03", "Gestión de usuarios (módulo del compañero · las rutas se modelan según el texto de la HU)")
nota(N, D, "Se dibuja desde el texto de la HU-03. Si las rutas o funciones del módulo de tu compañero se llaman distinto, edita estas líneas en docs/generar_diagrama.py y vuelve a generar.")

flujo("Registrar un usuario (Administrador)")
msg(U, N, "Completa el formulario: identificador_acceso, nombre_completo, correo (opcional), rol y contraseña")
msg(N, F, "POST registrar usuario")
msg(F, A, "verifica que el rol puede gestionar usuarios")
msg(A, D, "SELECT permisos del rol (roles_permisos)")
alt("el rol no es Administrador")
msg(F, N, "403", "err")
sino("el rol es Administrador")
propio(F, "valida obligatorios, formato y contraseña")
alt("datos inválidos")
msg(F, N, "400 · mensaje por campo", "err")
sino("datos válidos")
msg(F, D, "SELECT usuarios WHERE identificador_acceso = ?")
msg(D, F, "existe o no", "res")
alt("identificador duplicado")
msg(F, N, "409 · «El identificador ya está en uso»", "err")
sino("identificador libre")
msg(F, D, "INSERT usuarios (contrasena_hash, rol_id, activo = true)")
msg(F, N, "302 listado de usuarios", "ok")
fin()
fin()
fin()

flujo("Actualizar rol y estado de una cuenta (Administrador)")
msg(N, F, "POST actualizar usuario (nombre_completo, correo, rol_id)")
msg(F, D, "UPDATE usuarios SET ..., rol_id, actualizado_en (mismas comprobaciones de permiso y validación)")
msg(F, N, "302 listado de usuarios", "ok")
msg(N, F, "POST cambiar estado (activo = false)")
msg(F, D, "UPDATE usuarios SET activo = false, actualizado_en")
msg(F, N, "302 listado de usuarios", "ok")

flujo("Efecto de la cuenta desactivada en HU-01 y HU-02")
msg(N, F, "POST /login con la cuenta desactivada")
propio(F, "autenticar(): usuarios.activo = false")
msg(F, N, "401 · el mismo mensaje genérico que cualquier credencial inválida", "err")
msg(N, F, "GET /tickets con una sesión que ya estaba abierta")
msg(F, S, "cargar_usuario(): la cuenta ya no está activa")
msg(S, D, "UPDATE sesiones SET cerrada_en = ahora")
msg(F, N, "302 /login · pierde el acceso en la siguiente petición", "err")
msg(N, F, "GET /tickets tras cambiarle el rol (por ejemplo, Responsable a Solicitante)")
msg(F, A, "los permisos se leen de roles_permisos en cada petición")
msg(F, N, "403 en las acciones que el nuevo rol no permite", "err")


if __name__ == "__main__":
    (AQUI / "diagrama_secuencia_sprint1.svg").write_text(svg(), encoding="utf-8")
    (AQUI / "diagrama_secuencia_sprint1.mmd").write_text(mermaid(), encoding="utf-8")
    print("Listo: diagrama_secuencia_sprint1.svg y .mmd")
