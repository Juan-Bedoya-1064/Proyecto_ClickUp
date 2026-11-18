-- =====================================================================
--  Sprint 1 · Acceso y usuarios — Esquema para MySQL 8 / MariaDB 10.4+
--  (compatible con el MySQL/MariaDB que trae XAMPP)
--
--  Mismas tablas y columnas del diagrama relacional del equipo.
--  Formas de usarlo:
--    · phpMyAdmin  → pestaña «Importar» → elegir este archivo.
--    · Consola     → mysql -u root -p < db/schema.sql
--    · Docker      → se monta solo en el primer arranque del contenedor.
--  La app también puede crear todo sola con `python run.py`.
-- =====================================================================

CREATE DATABASE IF NOT EXISTS `acceso_usuarios`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `acceso_usuarios`;

CREATE TABLE IF NOT EXISTS `roles` (
  `id`          INT NOT NULL AUTO_INCREMENT,
  `nombre`      VARCHAR(50)  NOT NULL COMMENT 'Ej. Solicitante, Responsable, Administrador',
  `descripcion` VARCHAR(255) NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_roles_nombre` (`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `permisos` (
  `id`          INT NOT NULL AUTO_INCREMENT,
  `codigo`      VARCHAR(100) NOT NULL COMMENT 'Acción permitida, ej. usuarios.crear',
  `descripcion` VARCHAR(255) NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_permisos_codigo` (`codigo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `roles_permisos` (
  `rol_id`     INT NOT NULL,
  `permiso_id` INT NOT NULL,
  PRIMARY KEY (`rol_id`, `permiso_id`),
  CONSTRAINT `fk_roles_permisos_rol`
    FOREIGN KEY (`rol_id`) REFERENCES `roles` (`id`),
  CONSTRAINT `fk_roles_permisos_permiso`
    FOREIGN KEY (`permiso_id`) REFERENCES `permisos` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `usuarios` (
  `id`                   INT NOT NULL AUTO_INCREMENT,
  `identificador_acceso` VARCHAR(100) NOT NULL COMMENT 'Identificador de acceso sin duplicados (HU-03 criterio 2)',
  `contrasena_hash`      VARCHAR(255) NOT NULL COMMENT 'Nunca se guarda la contraseña en texto plano',
  `nombre_completo`      VARCHAR(150) NOT NULL,
  `correo`               VARCHAR(150) NULL     COMMENT 'Opcional',
  `rol_id`               INT NOT NULL,
  `activo`               BOOLEAN  NOT NULL DEFAULT TRUE COMMENT 'false = cuenta inactiva, no puede iniciar sesión',
  `creado_en`            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `actualizado_en`       DATETIME NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_usuarios_identificador_acceso` (`identificador_acceso`),
  CONSTRAINT `fk_usuarios_rol`
    FOREIGN KEY (`rol_id`) REFERENCES `roles` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `tickets` (
  `id`        INT NOT NULL AUTO_INCREMENT,
  `titulo`    VARCHAR(200) NOT NULL,
  `creado_en` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Tabla mínima: solo se incluye para representar la participación en HU-02';

CREATE TABLE IF NOT EXISTS `participaciones_ticket` (
  `id`                 INT NOT NULL AUTO_INCREMENT,
  `ticket_id`          INT NOT NULL,
  `usuario_id`         INT NOT NULL,
  `tipo_participacion` VARCHAR(30) NOT NULL COMMENT 'Ej. solicitante, responsable',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_participacion` (`ticket_id`, `usuario_id`, `tipo_participacion`),
  CONSTRAINT `fk_participaciones_ticket`
    FOREIGN KEY (`ticket_id`) REFERENCES `tickets` (`id`),
  CONSTRAINT `fk_participaciones_usuario`
    FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `sesiones` (
  `id`          INT NOT NULL AUTO_INCREMENT,
  `usuario_id`  INT NOT NULL,
  `token_hash`  VARCHAR(255) NOT NULL COMMENT 'SHA-256 del token de la cookie',
  `iniciada_en` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `expira_en`   DATETIME NOT NULL,
  `cerrada_en`  DATETIME NULL COMMENT 'Si tiene valor, la sesión ya no da acceso (cierre de sesión)',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_sesiones_token_hash` (`token_hash`),
  CONSTRAINT `fk_sesiones_usuario`
    FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
--  Sprint 2 · HU-04 Catálogos y equipos
--  Los valores no se borran: se desactivan (activo = FALSE) para que los
--  equipos que ya los usan conserven la referencia histórica.
-- =====================================================================

CREATE TABLE IF NOT EXISTS `tipos_equipo` (
  `id`                 INT NOT NULL AUTO_INCREMENT,
  `nombre`             VARCHAR(100) NOT NULL COMMENT 'Ej. Portátil, Impresora',
  `periodicidad_meses` INT NULL COMMENT 'Mantenimiento preventivo cada N meses. NULL = no aplica',
  `activo`             BOOLEAN NOT NULL DEFAULT TRUE,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_tipos_equipo_nombre` (`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `ubicaciones` (
  `id`     INT NOT NULL AUTO_INCREMENT,
  `nombre` VARCHAR(100) NOT NULL COMMENT 'Ej. Laboratorio de redes',
  `activo` BOOLEAN NOT NULL DEFAULT TRUE,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_ubicaciones_nombre` (`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `categorias_servicio` (
  `id`     INT NOT NULL AUTO_INCREMENT,
  `nombre` VARCHAR(100) NOT NULL COMMENT 'Ej. Hardware, Software, Red',
  `activo` BOOLEAN NOT NULL DEFAULT TRUE,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_categorias_servicio_nombre` (`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `equipos` (
  `id`           INT NOT NULL AUTO_INCREMENT,
  `codigo`       VARCHAR(30)  NOT NULL COMMENT 'Código de inventario, sin duplicados',
  `nombre`       VARCHAR(150) NOT NULL,
  `tipo_id`      INT NOT NULL,
  `ubicacion_id` INT NOT NULL,
  `activo`       BOOLEAN  NOT NULL DEFAULT TRUE,
  `creado_en`    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_equipos_codigo` (`codigo`),
  CONSTRAINT `fk_equipos_tipo`
    FOREIGN KEY (`tipo_id`) REFERENCES `tipos_equipo` (`id`),
  CONSTRAINT `fk_equipos_ubicacion`
    FOREIGN KEY (`ubicacion_id`) REFERENCES `ubicaciones` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
--  Sprint 2 · HU-05 Registro de ticket
--  La tabla `tickets` no cambia: los datos de la solicitud de mantenimiento
--  van en una tabla aparte, unida 1 a 1 con el ticket.
-- =====================================================================

CREATE TABLE IF NOT EXISTS `solicitudes_mantenimiento` (
  `id`              INT NOT NULL AUTO_INCREMENT,
  `ticket_id`       INT NOT NULL,
  `folio`           VARCHAR(20)  NOT NULL COMMENT 'Identificador del ticket, ej. TK-2026-00004. No cambia nunca',
  `equipo_id`       INT NOT NULL,
  `categoria_id`    INT NOT NULL,
  `prioridad`       VARCHAR(10)  NOT NULL COMMENT 'baja, media, alta o critica',
  `situacion`       TEXT         NOT NULL COMMENT 'Descripcion de lo que pasa con el equipo',
  `detectado_por`   VARCHAR(150) NOT NULL COMMENT 'Persona que noto el problema',
  `fecha_deteccion` DATE         NOT NULL,
  `estado`          VARCHAR(20)  NOT NULL DEFAULT 'abierto' COMMENT 'HU-06: abierto, en_proceso, resuelto o cerrado',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_solicitudes_ticket` (`ticket_id`),
  UNIQUE KEY `uq_solicitudes_folio` (`folio`),
  CONSTRAINT `fk_solicitudes_ticket`
    FOREIGN KEY (`ticket_id`) REFERENCES `tickets` (`id`),
  CONSTRAINT `fk_solicitudes_equipo`
    FOREIGN KEY (`equipo_id`) REFERENCES `equipos` (`id`),
  CONSTRAINT `fk_solicitudes_categoria`
    FOREIGN KEY (`categoria_id`) REFERENCES `categorias_servicio` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `adjuntos_ticket` (
  `id`              INT NOT NULL AUTO_INCREMENT,
  `ticket_id`       INT NOT NULL,
  `nombre_original` VARCHAR(255) NOT NULL COMMENT 'Nombre que traia el archivo; solo se muestra',
  `nombre_guardado` VARCHAR(64)  NOT NULL COMMENT 'Nombre aleatorio con el que queda en disco',
  `tamano_bytes`    INT NOT NULL,
  `subido_por_id`   INT NOT NULL,
  `creado_en`       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_adjuntos_nombre_guardado` (`nombre_guardado`),
  CONSTRAINT `fk_adjuntos_ticket`
    FOREIGN KEY (`ticket_id`) REFERENCES `tickets` (`id`),
  CONSTRAINT `fk_adjuntos_usuario`
    FOREIGN KEY (`subido_por_id`) REFERENCES `usuarios` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
--  Sprint 2 · HU-06 Consulta de tickets
--  Solo agrega la columna `estado` a `solicitudes_mantenimiento` (ya está
--  incluida arriba). Si tu base se creó ANTES de la HU-06, `python run.py`
--  la agrega sola; a mano sería:
--    ALTER TABLE `solicitudes_mantenimiento`
--      ADD COLUMN `estado` VARCHAR(20) NOT NULL DEFAULT 'abierto';
-- =====================================================================
