# Casos de prueba · Sprint 1

Se ejecutan con `python -m pytest -v`. Cada caso coincide con una prueba de `tests/`.

## HU-01 · Inicio y cierre de sesión (`tests/test_auth.py`)

| ID | Escenario | Resultado esperado | Tipo |
|---|---|---|---|
| CP-01 | `solicitante1` con su contraseña | Redirige a `/panel`; el panel carga | Válido |
| CP-02 | Identificador `  SOLICITANTE1 ` | Inicia sesión (se normaliza) | Válido |
| CP-03 | Login correcto | Cookie `HttpOnly` y `SameSite=Lax` | Válido |
| CP-04 | Abrir `/login` con sesión activa | Redirige a `/panel` | Válido |
| CP-05 | Login correcto | Fila en `sesiones` con hash de 64 caracteres | Válido |
| CP-06 | Contraseña errada vs. cuenta inexistente | Mismo 401, misma página | Inválido |
| CP-07 | Cuenta inexistente | El mensaje no dice «no existe», «inactiva», «bloqueada» | Inválido |
| CP-08 | `inactivo1` con contraseña correcta | 401 genérico; sin acceso | Inválido |
| CP-09 | Inactiva vs. inexistente | Páginas idénticas | Inválido |
| CP-10 | Desactivar cuenta con sesión abierta | Pierde acceso | Inválido |
| CP-11 | Cerrar sesión | `/panel` y `/tickets` ya no abren; `cerrada_en` con valor | Válido |
| CP-12 | Reusar cookie anterior al logout | Redirige a `/login` | Inválido |
| CP-13 | `GET /logout` | 405; la sesión sigue | Inválido |
| CP-14 | Páginas protegidas | `Cache-Control: no-store` | Válido |
| CP-15 | Rutas protegidas sin sesión | Redirigen a `/login` | Inválido |
| CP-16 | Sesión vencida | Pierde acceso | Inválido |
| CP-17 | Campos vacíos | 400 con mensaje por campo | Inválido |
| CP-18 | Identificador con caracteres no permitidos | 400 | Inválido |
| CP-19 | Contraseña de 129 caracteres | 400 | Inválido |
| CP-20 | Inyección SQL | No inicia sesión | Inválido |
| CP-21 | Contraseña en BD | Solo hash | Válido |
| CP-22 | Carga de más de 10 MB | 413 | Inválido |
| CP-23 | POST sin token CSRF | 400 | Inválido |
| CP-24 | POST con token CSRF | Inicia sesión | Válido |
| CP-25 | `GET /health` | `{"estado":"ok"}` | Válido |

## HU-02 · Control de acceso (`tests/test_autorizacion.py`)

| ID | Escenario | Resultado esperado | Tipo |
|---|---|---|---|
| AC-01 | **Matriz de 27 URL** (4 personas × tickets/crear/editar, por acceso directo) | 200 / 403 / 404 según [matriz](MATRIZ_PERMISOS.md) | Ambos |
| AC-02 | `solicitante1` lista tickets | Ve #1 y #3; no ve #2 | Válido |
| AC-03 | `responsable1` lista tickets | Solo #1 | Válido |
| AC-04 | `admin1` lista tickets | Ve #1, #2 y #3 | Válido |
| AC-05 | Solicitante crea ticket | Queda como solicitante; otro solicitante no lo ve (404) | Válido |
| AC-06 | Responsable edita su ticket | Título actualizado | Válido |
| AC-07 | Admin edita y asigna responsable | La persona asignada ya ve y edita el ticket | Válido |
| AC-08 | Título con `<script>` | Se muestra escapado | Válido |
| AC-09 | **19 operaciones indebidas** (rol sin permiso, ticket ajeno, sin sesión, datos inválidos, duplicado, rol incompatible) | Rechazo con 403/404/302/400/409 y **base de datos idéntica** | Inválido |
| AC-10 | Ticket ajeno vs. inexistente | Misma respuesta 404 | Inválido |
| AC-11 | Pantallas permitidas de `solicitante1` | Sin datos del ticket #2 | Inválido |
| AC-12 | Cambiar el rol de una persona | Aplica en la siguiente petición | Inválido |
| AC-13 | Retirar participación | Pasa de 200 a 404 | Inválido |
| AC-14 | Desactivar cuenta | Pierde acceso a tickets | Inválido |
| AC-15 | Cerrar sesión | Acceso directo a `/tickets/1` queda bloqueado | Inválido |
| AC-16 | Roles y permisos sembrados | Coinciden con la matriz | Válido |
| AC-17 | Permisos del responsable | Sin crear, asignar, ver ni editar todo | Inválido |

## Guion de la demostración (≈7 min)

1. `docker compose up --build` → <http://localhost:5000>.
2. **HU-01 inválido:** `solicitante1` con clave errada; `noexiste`; `inactivo1` con su clave → siempre el mismo mensaje.
3. **HU-01 válido:** `solicitante1` → panel con su rol y lo que le permite.
4. **HU-02 permitido:** Tickets → ve #1 y #3; abre #1; crea uno nuevo.
5. **HU-02 rechazado:** escribir en la barra `/tickets/2` → «No existe o no tienes acceso»; `/tickets/1/editar` → «Tu rol no permite esta acción».
6. Cerrar sesión; entrar como `responsable1` → ve solo #1, edita su título; `/tickets/registrar` → 403.
7. Entrar como `admin1` → ve los tres, asigna a `responsable1` al ticket #2.
8. `responsable1` vuelve a entrar y ahora ve el #2.
9. Mostrar `python -m pytest -v` en verde y, en phpMyAdmin (http://localhost/phpmyadmin → base `acceso_usuarios`), `SELECT * FROM participaciones_ticket;` y `SELECT * FROM sesiones;` para ver `cerrada_en` tras cerrar sesión.
