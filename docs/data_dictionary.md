# Diccionario de Datos — `odemiro_db`

Generado a partir del esquema real (`scripts/init-sql/create_schema.sql`),
extraído con `SHOW CREATE TABLE` sobre la base de datos en producción.
Motor: MySQL 8.0 · Charset: `utf8mb4` · Collation: `utf8mb4_0900_ai_ci`.

## 1. `snies_matriculados` (~921.000 filas)
**Fuente:** SNIES / MinEducación — Oferta académica oficial (datos.gov.co)

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `codigo_de_la_institucion` | bigint | Código SNIES de la IES |
| `institucion_de_educacion_superior_ies` | text | Nombre de la institución |
| `sector_ies` | text | Público / Privado |
| `caracter_ies` | text | Universidad, Institución Tecnológica, etc. |
| `departamento_de_domicilio_de_la_ies` | text | Departamento sede de la IES |
| `municipio_de_domicilio_de_la_ies` | text | Municipio sede de la IES |
| `codigo_snies_del_programa` | bigint | Código SNIES del programa académico |
| `programa_academico` | text | Nombre del programa |
| `programa_acreditado` | varchar | Indicador de acreditación de alta calidad |
| `nivel_academico` | text | Pregrado / Posgrado |
| `nivel_de_formacion` | text | Técnico, Tecnológico, Universitario, Especialización, Maestría, Doctorado |
| `metodologia` | text | Presencial, Virtual, Distancia, Dual |
| `area_de_conocimiento` | text | Área OCDE/CINE del programa |
| `nucleo_basico_del_conocimiento_nbc` | text | Núcleo básico del conocimiento (NBC) |
| `departamento_de_oferta_del_programa` | text | Departamento donde se ofrece el programa |
| `municipio_de_oferta_del_programa` | text | Municipio donde se ofrece el programa |
| `sexo` | text | Sexo de los matriculados agregados |
| `ano` / `semestre` | bigint | Periodo académico |
| `matriculados` | bigint | Número de estudiantes matriculados en el periodo |

**Uso en el sistema:** Lumina la consulta vía text-to-SQL para responder preguntas
sobre oferta académica (ej. "ingenierías virtuales en Medellín").

## 2. `desercion_academica` (~3.400 filas)
**Fuente:** SPADIES / MinEducación — Deserción por programa/estrato/género

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `periodo` | varchar | Periodo académico del registro |
| `nombre_facultad` / `nombre_programa` | varchar | Facultad y programa asociado |
| `jornada` / `modalidad` | varchar | Jornada y modalidad del programa |
| `nombre_sede` | varchar | Sede de la IES |
| `genero` | varchar | Género del estudiante |
| `estrato` | varchar | Estrato socioeconómico |
| `nombre_estado` | varchar | Estado académico (activo, desertor, graduado, etc.) |
| `origen_geografico` | varchar | Procedencia geográfica del estudiante |

**Uso en el sistema:** Ada la cruza contra el perfil del usuario (estrato,
programa de interés) para estimar riesgo de deserción en el reporte final.

> ⚠️ **Nota de sesgo:** esta tabla contiene variables sensibles (estrato,
> género, origen geográfico). Cualquier modelo o regla que use estos campos
> para influir en recomendaciones debe pasar por `tests/bias_tests/` antes de
> producción — ver `docs/public_impact_assessment.md`.

## 3. `modelado_aptitudes` (~164.000 filas)
**Fuente:** Interna — Modelado de aptitudes vocacionales

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `aptitud` | text | Nombre de la aptitud evaluada |
| `categoria` / `subcategoria` | text | Clasificación jerárquica de la aptitud |

**Uso en el sistema:** referencia para el test psicométrico de 40 ítems de Ada
(6 dimensiones vocacionales).

## 4. `geih_departamento_resumen` (33 filas — 1 por departamento)
**Fuente:** GEIH / DANE — agregado por `scripts/consolidar_geih.py` a partir
del consolidado crudo (3.696.094 registros, ene-2022 a abr-2026), ponderado
por `FACTOR_EXPANSION`.

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `dpto` | int | Código DANE de departamento (PK) — mismo código que `snies_matriculados.codigo_del_departamento_programa` |
| `departamento` | varchar | Nombre del departamento |
| `poblacion_ocupada_estimada` / `poblacion_desocupada_estimada` | bigint | Promedio mensual estimado (NO suma de los 52 meses) |
| `tasa_desempleo_pct` | decimal | Desocupados / (Ocupados + Desocupados), ponderado |
| `ingreso_mediana` / `ingreso_medio` | decimal | Ingreso mensual (COP) de ocupados, ponderado |
| `pct_informalidad` | decimal | % de ocupados clasificados como informales (`INFORMALIDAD_DANE`) |
| `pct_cabecera` | decimal | % de la muestra en zona urbana (Cabecera) |

## 5. `geih_sector_departamento` (1.959 filas — departamento × sector CIIU)
**Fuente:** igual que la anterior, desagregado por `SECTOR_CIIU_2D` (división
CIIU Rev.4 A.C. a 2 dígitos). Se descartan celdas con menos de 30 observaciones
crudas (no confiables a esa desagregación).

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `dpto`, `sector_ciiu_2d` | int | PK compuesta |
| `sector_nombre` | varchar | Nombre del sector (ver `CIIU_NOMBRE` en el script) |
| `poblacion_ocupada_estimada`, `ingreso_mediana`, `ingreso_medio`, `pct_informalidad` | — | Igual definición que en el resumen departamental, pero acotado al sector |
| `horas_promedio_semanales` | decimal | Promedio ponderado de horas trabajadas/semana |

**Uso en el sistema:** `Ada._analizar_mercado_laboral()` cruza el
`area_de_conocimiento` del programa mejor rankeado con sectores CIIU afines
(`AREA_CONOCIMIENTO_A_CIIU` en `Ada.py`) y el departamento del estudiante,
para agregar al reporte una sección real de "Panorama del mercado laboral"
(ingreso mediano, informalidad) — determinista, sin LLM para los números.

---
*No hay columnas de PII directa (nombre, documento, contacto) en ninguna de
las cinco tablas: son agregados/anonimizados en origen. La GEIH en particular
son promedios ponderados de encuesta, nunca microdatos de personas.*
