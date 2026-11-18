
4

# Sprint 1 · Acceso y usuarios

| HU | Historia | Estado |
|---|---|---|
| **HU-01** | Como usuario con una cuenta activa, quiero iniciar y cerrar sesión para acceder de forma segura a las funciones que me correspondan. | Implementada y probada |
| **HU-02** | Como usuario autenticado, quiero acceder solamente a la información y acciones permitidas por mi rol y participación en cada ticket, para proteger datos y evitar cambios no autorizados. | Implementada y probada |
| **HU-03** | Como administrador, quiero registrar y mantener usuarios con su rol y estado para controlar quién puede utilizar el sistema. | Implementada por otro integrante; aquí solo se modela en el diagrama de secuencia |

**Stack:** Python 3.10+ · Flask · **MySQL 8 / MariaDB (XAMPP)** · Docker Compose (opcional) · pytest  
**Datos:** 100 % ficticios. **Adjuntos:** máximo 10 MB (`MAX_CONTENT_LENGTH`, responde 413).  
**Base de datos:** el esquema del equipo está en [`db/schema.sql`](db/schema.sql) en sintaxis MySQL (diagrama en [`docs/diagrama_relacional.png`](docs/diagrama_relacional.png)); los modelos de `app/models.py` coinciden 1:1.

---

## 1. Ejecutar y ver en el navegador

### Opción A · XAMPP (recomendada, sin Docker)

1. Abre el **panel de XAMPP** y pulsa **Start** en **MySQL** (Apache no hace falta).
2. **Windows:** doble clic en **`iniciar.bat`**.  
   **macOS / Linux:** `./iniciar.sh`
3. Se abre solo **http://127.0.0.1:5000**. Entra con `admin1` / `Admin#2026-Demo`.

La primera vez crea el entorno virtual `.venv`, instala dependencias y, en MySQL, **crea la base `acceso_usuarios`, sus 7 tablas y los datos de demostración**. Las siguientes veces solo arranca.

Hazlo a mano si prefieres:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  ·  source .venv/bin/activate en macOS/Linux
pip install -r requirements.txt
copy .env.example .env           # cp en macOS/Linux; ajusta MYSQL_PASSWORD si tu root tiene clave
python run.py
```

Para ver los datos: **http://localhost/phpmyadmin** → base `acceso_usuarios` (necesita Apache encendido en XAMPP). También puedes importar `db/schema.sql` desde la pestaña **Importar** de phpMyAdmin; la app respeta las tablas existentes.

| Variable (`.env`) | Por defecto | Para qué |
|---|---|---|
| `MYSQL_HOST` / `MYSQL_PORT` | `127.0.0.1` / `3306` | Servidor MySQL de XAMPP |
| `MYSQL_USER` / `MYSQL_PASSWORD` | `root` / *(vacía)* | Credenciales (XAMPP trae root sin clave) |
| `MYSQL_DATABASE` | `acceso_usuarios` | Nombre de la base |
| `DATABASE_URL` | — | Si la pones, reemplaza todo lo anterior |
| `ZONA_HORARIA` | `America/Bogota` | Hora que se muestra en pantalla (la BD guarda UTC) |

### Opción B · Docker Compose

```bash
cp .env.example .env
docker compose up --build        # http://localhost:5000  ·  MySQL expuesto en 127.0.0.1:3307
```

MySQL 8.4 crea las tablas con `db/schema.sql` en su primer arranque; después la app carga los datos de demostración.

### Pruebas

```bash
python -m pytest -v              # 86 pruebas, SQLite en memoria (no necesita MySQL)

# Contra MySQL real (crea antes la base vacía acceso_usuarios_test):
set TEST_DATABASE_URL=mysql+pymysql://root:@127.0.0.1:3306/acceso_usuarios_test?charset=utf8mb4
python -m pytest -v
```

### Usuarios y tickets de demostración

| Identificador | Contraseña | Rol | Estado |
|---|---|---|---|
| `admin1` | `Admin#2026-Demo` | Administrador | activo |
| `solicitante1` | `Solicitante#2026-Demo` | Solicitante | activo |
| `solicitante2` | `Solicitante#2026-Demo` | Solicitante | activo |
| `responsable1` | `Responsable#2026-Demo` | Responsable | activo |
| `responsable2` | `Responsable#2026-Demo` | Responsable | activo |
| `inactivo1` | `Inactivo#2026-Demo` | Solicitante | **inactivo** |

| Ticket | Solicitante | Responsable |
|---|---|---|
| #1 Falla en la impresora del laboratorio | solicitante1 | responsable1 |
| #2 Solicitud de acceso a la red wifi | solicitante2 | responsable2 |
| #3 Restablecer contraseña de correo | solicitante1 | responsable2 |

---

## 2. HU-01 · Inicio y cierre de sesión

| Criterio | Implementación | Pruebas |
|---|---|---|
| Usuario activo con credenciales válidas inicia sesión | `auth.autenticar()` + `security.iniciar_sesion()`; crea una fila en `sesiones` | CP-01 a CP-05 |
| Credenciales inválidas no revelan cuál dato falló | Un único mensaje, mismo 401 y misma página; hash de relleno si la cuenta no existe | CP-06, CP-07 |
| Cuenta inactiva no puede ingresar | Mismo mensaje genérico; el motivo real solo queda en el registro del servidor | CP-08 a CP-10 |
| Cerrar sesión elimina acceso a funciones protegidas | `cerrada_en` en `sesiones` + cookie borrada; una cookie copiada ya no sirve | CP-11 a CP-16 |

**Sesión:** cookie firmada (`HttpOnly`, `SameSite=Lax`, `Secure` con HTTPS) que solo lleva un token aleatorio; en la base se guarda su hash SHA-256. Vence a los 30 min de inactividad; se renueva en cada inicio (sin fijación de sesión); si la cuenta se desactiva, la sesión deja de servir; `Cache-Control: no-store` evita ver páginas protegidas con «atrás».

## 3. HU-02 · Control de acceso por rol y participación

Una sola capa (`app/autorizacion.py`) decide en **cada** petición, incluido el acceso directo por URL:

1. **Permiso del rol** (`roles_permisos`): ¿el rol permite esta clase de acción? Si no → **403**.
2. **Alcance por participación** (`participaciones_ticket`): ¿puede hacerlo sobre *este* ticket? Si no → **404** (misma respuesta que un ticket inexistente, para no revelar su existencia). El administrador ve todo.
3. **Edición:** además de ver el ticket, exige ser *responsable* de él (o administrador). Si no → **403**.

Todas las comprobaciones ocurren **antes** de escribir, por eso una operación rechazada nunca altera datos (lo verifica una instantánea de la BD antes y después en cada prueba). Ver la matriz completa en [`docs/MATRIZ_PERMISOS.md`](docs/MATRIZ_PERMISOS.md).

| Criterio | Pruebas |
|---|---|
| Usuarios autorizados realizan acciones permitidas | AC-02 a AC-08 |
| Los no autorizados no consultan ni modifican información restringida | AC-01, AC-10, AC-11 |
| Operaciones indebidas se rechazan sin alterar datos | AC-09 (19 casos) |
| Las reglas aplican también al acceso directo | AC-01 (27 URL), AC-10, AC-12 a AC-15 |

## 4. Verificación realizada

- 86 pruebas automáticas en verde con **SQLite** y también contra **MariaDB 10.11** real (el motor que trae XAMPP).
- `db/schema.sql` importado tal cual en MariaDB, y también arranque desde cero con `python run.py` (crea base, tablas y datos).
- Flujo revisado en el navegador: login válido e inválido, panel, lista y detalle de tickets.
- Pendiente de tu parte: probar `docker compose up --build` (MySQL 8.4) en tu equipo; aquí no hay Docker.

## 5. Estructura

```
run.py              arranque local: crea BD/tablas/datos y abre el navegador
iniciar.bat / .sh   lanzadores de doble clic (Windows / macOS-Linux)
app/  __init__ · auth · autorizacion · security · tickets · main · models · seed · validators · cli
      templates/ · static/
db/schema.sql       esquema del equipo en MySQL (phpMyAdmin, consola o Docker)
tests/              test_auth.py (HU-01) · test_autorizacion.py (HU-02)
docs/               matriz de permisos · casos de prueba · trazabilidad · diagramas (relacional y de secuencia)
```

## 6. Diagrama de secuencia

Ver [`docs/DIAGRAMA_SECUENCIA.md`](docs/DIAGRAMA_SECUENCIA.md): cubre HU-01, HU-02 y HU-03 con los nombres de rutas, funciones y tablas del código.

## 7. Notas
- Producción: cambiar `SECRET_KEY`, no usar `root` sin clave (crear un usuario MySQL propio para la app), usar HTTPS con `COOKIE_SECURE=1`, `SEED_DEMO=0`.
- El esquema del equipo no incluye intentos fallidos ni bitácora de eventos, así que no hay bloqueo temporal por fuerza bruta; los intentos fallidos solo quedan en el registro del servidor. Si lo quieren, es una ampliación del esquema para otro sprint.

---

## 8. Sprint 2 · HU-04 Catálogos y equipos

Mantener catálogos básicos y localizar equipos para usar información consistente.

**Lo que definió el equipo**

| Tema | Decisión |
|---|---|
| Catálogos | Tipos de equipo, Ubicaciones y Categorías de servicio |
| Atributos | `nombre` y `activo` en todos; los tipos de equipo además tienen `periodicidad_meses` |
| Equipo | `codigo` de inventario (único), `nombre`, tipo, ubicación y `activo` |
| Alta / cambio | Nombre de 2 a 100 caracteres, sin repetir dentro del catálogo (no distingue mayúsculas). Código de equipo: 3 a 30 letras, números o guion; se guarda en mayúsculas |
| Desactivación | Nada se borra: se marca `activo = false`. Un valor inactivo no se ofrece ni se acepta en equipos nuevos, pero los equipos que ya lo usan lo conservan y lo siguen mostrando |
| Periodicidad preventiva | Opcional y solo en tipos de equipo: de 1 a 60 meses; vacío = «No aplica» |
| Permisos | `equipos.ver` (los tres roles) y `catalogos.administrar` (solo Administrador) |

**Pantallas**

- `/equipos` — consulta de equipos activos con búsqueda por código o nombre y filtros por tipo y ubicación. El administrador además puede incluir los inactivos, crear, editar y desactivar.
- `/catalogos` — administración de los tres catálogos (solo Administrador).

| Criterio | Implementación | Pruebas |
|---|---|---|
| Consultar equipos activos | `app/equipos.py` → `lista()` | CA-01 a CA-07 |
| Administrar catálogos | `app/catalogos.py` | CA-08 a CA-17 |
| Conservar referencias históricas al desactivar | columna `activo`; no existe ninguna ruta de borrado | CA-18 a CA-22 |
| Configurar periodicidad preventiva cuando aplique | `tipos_equipo.periodicidad_meses` | CA-23 a CA-28 |
| Reglas de alta, cambio y desactivación de equipos | `app/equipos.py` | CA-29 a CA-33 |

**Demostración:** al arrancar se cargan 7 tipos de equipo, 6 ubicaciones, 5 categorías y 12 equipos ficticios. Incluyen un tipo y una ubicación inactivos, un equipo activo que sigue en la ubicación inactiva (`PC-004`) y un equipo dado de baja (`PC-000`).

Las tablas nuevas están al final de `db/schema.sql`; si ya tenías la base del sprint 1, `python run.py` las crea solas sin tocar tus datos.

```bash
python -m pytest -v tests/test_catalogos.py     # 88 pruebas de la HU-04
python -m pytest -v                             # 174 en total (sprint 1 + HU-04)
```

---

## 9. Sprint 2 · HU-05 Registro de ticket

Registrar una solicitud de mantenimiento relacionada con un equipo para identificar y rastrear la necesidad.

**Lo que definió el equipo**

| Tema | Decisión |
|---|---|
| Campos | Asunto, equipo, categoría, prioridad, situación, detectado por, fecha de detección y evidencia (opcional) |
| Categorías | Las del catálogo «Categorías de servicio» de la HU-04 (solo las activas) |
| Prioridades | Baja, Media, Alta y Crítica |
| Solicitante | Siempre la persona con la sesión abierta; no se puede elegir a otra |
| Detector | Texto libre (puede ser alguien sin cuenta); viene con el nombre del solicitante y se puede cambiar |
| Fechas | Fecha de detección: obligatoria y no futura. Fecha de registro: la pone el servidor |
| Folio | `TK-AÑO-NÚMERO` (ej. `TK-2026-00004`). Se arma con el id del ticket, se guarda con restricción `UNIQUE` y no cambia al editar |
| Validaciones | Asunto 3-200 caracteres, situación 10-2000, detector 3-150; equipo y categoría deben existir y estar activos |
| Permisos | Registrar: `tickets.crear` (Solicitante y Administrador). Consultar: las mismas reglas de la HU-02 |

**Seguridad de la evidencia**

- Solo JPG, PNG o PDF, un archivo por ticket, máximo 10 MB (el servidor corta en 10 MB con error 413).
- Se revisan los primeros bytes del archivo: cambiarle la extensión a otro tipo de archivo no sirve.
- Se guarda en la carpeta `adjuntos/` (fuera de `app/static`) con un nombre aleatorio; el nombre original solo se muestra.
- Solo la descarga quien puede ver el ticket, y siempre como descarga (`Content-Disposition: attachment`).
- Si el formulario tiene cualquier error no se guarda ni el ticket ni el archivo.

**Pantallas**

- `/tickets/registrar` — formulario de registro.
- `/tickets/<id>` — el detalle ahora muestra folio, equipo, prioridad, detector, fechas, situación y evidencia.
- `/tickets` — columna Folio (la búsqueda por folio quedó como filtro del listado en la HU-06).

| Criterio | Implementación | Pruebas |
|---|---|---|
| Equipo activo | `app/registro.py` → `registrar()` | RT-04 a RT-07 |
| Validar campos obligatorios | `app/validators.py` | RT-08 a RT-11 |
| Folio único y persistente | `solicitudes_mantenimiento.folio` | RT-12 a RT-16 |
| Identificar solicitante, detector, equipo, situación, prioridad y fecha | tabla `solicitudes_mantenimiento` + `participaciones_ticket` | RT-17 a RT-22 |
| Adjuntar evidencia permitida dentro del límite | `validar_evidencia()` + tabla `adjuntos_ticket` | RT-23 a RT-31 |

**Nota:** la tabla `tickets` del sprint 1 no se modificó; los datos nuevos van en `solicitudes_mantenimiento` (1 a 1 con el ticket) y `adjuntos_ticket`. El formulario del sprint 1 (`/tickets/nuevo`, solo título) se retiró: todo ticket se registra en `/tickets/registrar`, con equipo y folio. Las pruebas del sprint 1 que lo usaban ahora apuntan al formulario nuevo.

```bash
python -m pytest -v tests/test_registro.py      # 62 pruebas de la HU-05
python -m pytest -v                             # 364 en total (ver HU-06)
```

---

## 10. Sprint 2 · HU-06 Consulta de tickets

Consultar y filtrar solo los tickets que el participante puede ver.

**Lo que definió el equipo**

| Tema | Decisión |
|---|---|
| Autorización | Igual que en la HU-02: el Administrador ve todos los tickets; los demás solo aquellos en los que participan. Primero se limita a los tickets visibles y **después** se aplican los filtros, así ningún filtro (ni escrito a mano en la dirección) muestra tickets ajenos |
| Búsqueda por folio | Campo de texto; acepta el folio completo o una parte, sin importar mayúsculas |
| Filtros | Equipo, área, solicitante, responsable, prioridad y estado. Se pueden combinar; todos van en la dirección (`/tickets?estado=abierto&prioridad=alta`) |
| Área | Es la ubicación del equipo del ticket (catálogo «Ubicaciones» de la HU-04) |
| Estado | Abierto, En proceso, Resuelto y Cerrado. Todo ticket nace «Abierto». En este sprint solo se consulta; cambiarlo queda para la historia de atención del ticket |
| Listas desplegables | Solo ofrecen equipos, áreas y personas que aparecen en los tickets que la persona puede ver (no revelan datos de tickets ajenos) |
| Valores no válidos | Un filtro con un valor que no sirve se toma como «sin filtro»; un id que no existe no muestra nada |
| Sin resultados | Con filtros: «Ningún ticket coincide con los filtros» y enlace para limpiarlos. Sin tickets: «Aún no participas en ningún ticket» y no se muestran los filtros. Un folio ajeno responde igual que uno inexistente |
| Campos del listado | Folio, título, equipo y área, prioridad, estado, tu participación y fecha; del más reciente al más antiguo |
| Detalle | Muestra los mismos datos del listado más situación, detector, fechas, evidencia y participantes. Sigue protegido: 404 si la persona no puede ver el ticket |

**Cambio en la base:** columna `estado` en `solicitudes_mantenimiento`. Si la base ya existía, `python run.py` (o `flask init-db`) la agrega sola sin perder datos (`agregar_columnas_faltantes()` en `app/cli.py`).

| Criterio | Implementación | Pruebas |
|---|---|---|
| Autorización por ticket | `app/consulta.py` → `tickets_visibles()` | CT-01 a CT-06 |
| Búsqueda por folio | `aplicar_filtros()` | CT-07 a CT-10 |
| Filtros por equipo, solicitante, responsable, área, prioridad y estado | `leer_filtros()` + `aplicar_filtros()` | CT-11 a CT-17 |
| Sin resultados | `ticket_lista.html` | CT-18, CT-19 |
| Detalle coherente y protegido | `ticket_detalle.html` + `autorizacion.py` | CT-20 a CT-22 |

La prueba CT-02 cruza las 5 personas de demostración con 13 combinaciones de filtros (65 casos) y comprueba que cada una ve exactamente los tickets que cumplen el filtro **y** que le corresponden.

**Demostración:** ahora hay 8 tickets ficticios con equipos, áreas, prioridades y estados variados (uno sin responsable).

```bash
python -m pytest -v tests/test_consulta.py      # 128 pruebas de la HU-06
python -m pytest -v                             # 364 en total
```
