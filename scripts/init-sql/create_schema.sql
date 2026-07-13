-- ============================================================
--  ESQUEMA REAL BD ODEM — SNIES + DESERCIÓN + MODELADO
--  Motor: MySQL 8.0  (utf8mb4 / utf8mb4_0900_ai_ci)
--
--  Este DDL refleja EXACTAMENTE la estructura de las tablas
--  que consultan Lumina y Ada en producción. Fue extraído con
--  SHOW CREATE TABLE de la base real `odemiro_db`.
--
--  Orden de carga recomendado:
--    1) Ejecutar este archivo  -> crea la base y las tablas vacías
--    2) Importar los datos      -> ver scripts/init-sql/data/ (CSV) o
--                                  el dump completo (odemiro_db.sql.gz)
--
--  Nota: los tipos son mayormente TEXT/BIGINT porque las tablas se
--  cargaron por ingesta directa de los CSV oficiales (SNIES / SPADIES).
--  Las consultas usan índices funcionales sobre estas columnas.
-- ============================================================

CREATE DATABASE IF NOT EXISTS `odemiro_db`
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE `odemiro_db`;

-- ------------------------------------------------------------
-- 1. SNIES MATRICULADOS  (oferta académica oficial, ~1.05M filas)
--    Fuente: SNIES / MinEducación
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `snies_matriculados`;
CREATE TABLE `snies_matriculados` (
  `id` text,
  `pli` text,
  `fecha` text,
  `codigo_de_la_institucion` bigint DEFAULT NULL,
  `ies_padre` bigint DEFAULT NULL,
  `institucion_de_educacion_superior_ies` text,
  `principal_o_seccional` text,
  `id_sector_ies` varchar(255) DEFAULT NULL,
  `sector_ies` text,
  `id_caracter` varchar(255) DEFAULT NULL,
  `caracter_ies` text,
  `codigo_del_departamento_ies` varchar(255) DEFAULT NULL,
  `codigo_del_departamento_ies_1` bigint DEFAULT NULL,
  `departamento_de_domicilio_de_la_ies` text,
  `codigo_del_municipio` bigint DEFAULT NULL,
  `ies_acreditada` varchar(255) DEFAULT NULL,
  `municipio_de_domicilio_de_la_ies` text,
  `codigo_snies_del_programa` bigint DEFAULT NULL,
  `programa_academico` text,
  `programa_acreditado` varchar(255) DEFAULT NULL,
  `id_nivel_academico` bigint DEFAULT NULL,
  `nivel_academico` text,
  `id_nivel_de_formacion` bigint DEFAULT NULL,
  `nivel_de_formacion` text,
  `id_metodologia` bigint DEFAULT NULL,
  `metodologia` text,
  `id_area` bigint DEFAULT NULL,
  `area_de_conocimiento` text,
  `id_nucleo` bigint DEFAULT NULL,
  `nucleo_basico_del_conocimiento_nbc` text,
  `id_cine_campo_amplio` bigint DEFAULT NULL,
  `desc_cine_campo_amplio` text,
  `id_cine_campo_especifico` bigint DEFAULT NULL,
  `desc_cine_campo_especifico` text,
  `id_cine_codigo_detallado` bigint DEFAULT NULL,
  `desc_cine_codigo_detallado` text,
  `codigo_del_departamento_programa` bigint DEFAULT NULL,
  `departamento_de_oferta_del_programa` text,
  `codigo_del_municipio_programa` bigint DEFAULT NULL,
  `municipio_de_oferta_del_programa` text,
  `id_sexo` bigint DEFAULT NULL,
  `sexo` text,
  `ano` bigint DEFAULT NULL,
  `semestre` bigint DEFAULT NULL,
  `matriculados` bigint DEFAULT NULL,
  `_rowid` int NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`_rowid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Índices funcionales que aceleran las consultas de Lumina/Ada.
-- (Se crean tras la carga para no ralentizar el import.)
-- Descomenta si tu import no los crea:
-- CREATE INDEX idx_prog ON snies_matriculados (programa_academico(100));
-- CREATE INDEX idx_muni ON snies_matriculados (municipio_de_oferta_del_programa(60));
-- CREATE INDEX idx_area ON snies_matriculados (area_de_conocimiento(80));

-- ------------------------------------------------------------
-- 2. DESERCIÓN ACADÉMICA  (SPADIES / MinEducación, ~3.4K filas)
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `desercion_academica`;
CREATE TABLE `desercion_academica` (
  `id` int NOT NULL AUTO_INCREMENT,
  `periodo` varchar(255) DEFAULT NULL,
  `nombre_facultad` varchar(255) DEFAULT NULL,
  `nombre_programa` varchar(255) DEFAULT NULL,
  `jornada` varchar(255) DEFAULT NULL,
  `modalidad` varchar(255) DEFAULT NULL,
  `nombre_sede` varchar(255) DEFAULT NULL,
  `tipo_iden_est` varchar(50) DEFAULT NULL,
  `fecha_nacimiento` varchar(255) DEFAULT NULL,
  `genero` varchar(50) DEFAULT NULL,
  `estrato` varchar(255) DEFAULT NULL,
  `nombre_estado` varchar(255) DEFAULT NULL,
  `origen_geografico` varchar(255) DEFAULT NULL,
  `lugar_expedicion` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ------------------------------------------------------------
-- 3. MODELADO DE APTITUDES  (~164K filas)
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `modelado_aptitudes`;
CREATE TABLE `modelado_aptitudes` (
  `id` bigint DEFAULT NULL,
  `aptitud` text,
  `categoria` text,
  `subcategoria` text,
  `_rowid` int NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`_rowid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ------------------------------------------------------------
-- 4. MERCADO LABORAL GEIH (DANE) — agregados, NO microdatos
--    Generadas por scripts/consolidar_geih.py a partir del CSV crudo de la
--    GEIH (~3.7M registros, ene-2022 a abr-2026), ponderando por
--    FACTOR_EXPANSION (encuesta muestral) y promediando por mes (el panel es
--    mensual: sumar los 52 meses sin promediar infla la población ~52x).
--    El CSV crudo NO se versiona (~400MB); solo estos agregados livianos.
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `geih_departamento_resumen`;
CREATE TABLE `geih_departamento_resumen` (
  `dpto` int NOT NULL,
  `departamento` varchar(80) DEFAULT NULL,
  `n_observaciones` int DEFAULT NULL,
  `poblacion_ocupada_estimada` bigint DEFAULT NULL,
  `poblacion_desocupada_estimada` bigint DEFAULT NULL,
  `tasa_desempleo_pct` decimal(5,2) DEFAULT NULL,
  `ingreso_mediana` decimal(12,2) DEFAULT NULL,
  `ingreso_medio` decimal(12,2) DEFAULT NULL,
  `pct_informalidad` decimal(5,2) DEFAULT NULL,
  `pct_cabecera` decimal(5,2) DEFAULT NULL,
  `anio_inicio` int DEFAULT NULL,
  `anio_fin` int DEFAULT NULL,
  PRIMARY KEY (`dpto`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `geih_sector_departamento`;
CREATE TABLE `geih_sector_departamento` (
  `dpto` int NOT NULL,
  `departamento` varchar(80) DEFAULT NULL,
  `sector_ciiu_2d` int NOT NULL,
  `sector_nombre` varchar(120) DEFAULT NULL,
  `n_observaciones` int DEFAULT NULL,
  `poblacion_ocupada_estimada` bigint DEFAULT NULL,
  `ingreso_mediana` decimal(12,2) DEFAULT NULL,
  `ingreso_medio` decimal(12,2) DEFAULT NULL,
  `pct_informalidad` decimal(5,2) DEFAULT NULL,
  `horas_promedio_semanales` decimal(5,2) DEFAULT NULL,
  `anio_inicio` int DEFAULT NULL,
  `anio_fin` int DEFAULT NULL,
  PRIMARY KEY (`dpto`,`sector_ciiu_2d`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
