# Matriz de roles, permisos y participación (HU-02)

## Permisos (tabla `permisos`)

| Código | Descripción |
|---|---|
| `tickets.ver` | Ver tickets en los que participas |
| `tickets.ver_todos` | Ver todos los tickets |
| `tickets.crear` | Crear tickets |
| `tickets.editar` | Editar tickets en los que eres responsable |
| `tickets.editar_todos` | Editar cualquier ticket |
| `tickets.asignar` | Asignar solicitantes y responsables a un ticket |

## Permisos por rol (tabla `roles_permisos`)

| Permiso | Solicitante | Responsable | Administrador |
|---|:-:|:-:|:-:|
| `tickets.ver` | ✔ | ✔ | ✔ |
| `tickets.ver_todos` | | | ✔ |
| `tickets.crear` | ✔ | | ✔ |
| `tickets.editar` | | ✔ | ✔ |
| `tickets.editar_todos` | | | ✔ |
| `tickets.asignar` | | | ✔ |

## Reglas con participación (`participaciones_ticket`)

| Acción | Regla | Si no se cumple |
|---|---|---|
| Listar tickets | Con `tickets.ver_todos` ve todos; si no, solo donde participa | 403 sin `tickets.ver` |
| Ver un ticket | `tickets.ver` **y** (`ver_todos` **o** participa) | 404 (igual que inexistente) |
| Crear ticket | `tickets.crear`; quien crea queda como `solicitante` | 403 |
| Editar título | `tickets.editar` **y** ver el ticket **y** (`editar_todos` **o** ser `responsable` del ticket) | 403 sin permiso o sin ser responsable; 404 si no lo ve |
| Asignar persona | `tickets.asignar`; persona activa; tipo válido; rol compatible (`solicitante` exige `tickets.crear`, `responsable` exige `tickets.editar`); sin duplicar | 403 sin permiso; 400 datos inválidos; 409 duplicado |

## Códigos HTTP y por qué

- **403 Prohibido:** el rol no permite esa clase de acción; no depende del ticket.
- **404 No encontrado:** el ticket no existe *o* la persona no participa: se responde igual para no revelar su existencia.
- **302 a /login:** no hay sesión válida (nunca llega a evaluarse el rol).
