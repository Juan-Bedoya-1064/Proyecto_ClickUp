# Trazabilidad y Definición de Hecho (DoD) · Sprint 1

Completa las columnas **Tarea** y **Evidencia** con los enlaces de tu tablero y repositorio.

## Trazabilidad

| HU | Criterio | Código | Pruebas | Tarea | Evidencia |
|---|---|---|---|---|---|
| HU-01 | Inicia sesión con credenciales válidas | `app/auth.py`, `app/security.py` | CP-01…CP-05 | _enlace_ | _captura / video_ |
| HU-01 | Credenciales inválidas no revelan el dato | `app/auth.py` | CP-06, CP-07 | _enlace_ | _captura_ |
| HU-01 | Cuenta inactiva no ingresa | `app/auth.py`, `app/security.py` | CP-08…CP-10 | _enlace_ | _captura_ |
| HU-01 | Cerrar sesión elimina acceso | `app/security.py` | CP-11…CP-16 | _enlace_ | _captura_ |
| HU-02 | Autorizados realizan acciones permitidas | `app/autorizacion.py`, `app/tickets.py` | AC-02…AC-08 | _enlace_ | _captura_ |
| HU-02 | No autorizados no consultan ni modifican | `app/autorizacion.py` | AC-01, AC-10, AC-11 | _enlace_ | _captura_ |
| HU-02 | Rechazos sin alterar datos | `app/tickets.py` | AC-09 | _enlace_ | _salida de pytest_ |
| HU-02 | Reglas también en acceso directo | `app/autorizacion.py` | AC-01, AC-12…AC-15 | _enlace_ | _captura de URL directa_ |

## Definición de Hecho

- [x] Funcionalidad integrada de punta a punta (login → tickets → logout).
- [x] Pruebas automáticas en verde (86) en SQLite y en MySQL/MariaDB real.
- [x] Documentación: README, matriz de permisos, casos de prueba, esquema.
- [x] Stack: Python, Flask, MySQL (XAMPP o Docker Compose); datos ficticios; adjuntos máx. 10 MB.
- [ ] `docker compose up --build` verificado en el equipo del integrante.
- [ ] Enlaces a tareas, commits/PR y evidencias completados en la tabla de arriba.
- [ ] Presentado en la Sprint Review.
