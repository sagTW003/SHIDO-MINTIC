# Fuentes de Datos

| Dataset | Fuente oficial | Registros en BD | Estado en esta entrega |
| :--- | :--- | :---: | :--- |
| SNIES Matriculados | MinEducación / [datos.gov.co](https://datos.gov.co) | ~921.000 | ✅ Cargado en `odemiro_db.snies_matriculados` |
| Deserción Académica (SPADIES) | MinEducación | ~3.400 | ✅ Cargado en `odemiro_db.desercion_academica` |
| Modelado de Aptitudes | Interno (equipo ODEM) | ~164.000 | ✅ Cargado en `odemiro_db.modelado_aptitudes` |
| GEIH 2022-2026 | DANE | 3.696.094 registros crudos → 33 + 1.959 filas agregadas | ✅ **Integrado (2026-07-13)**: el usuario ubicó el consolidado real (`GEIH_consolidado_2022_2026.csv`, 409MB, ene-2022 a abr-2026). Se escribió `scripts/consolidar_geih.py` (ahora sí existe) y se cargó en `odemiro_db.geih_departamento_resumen` (33 filas, 1/departamento) y `odemiro_db.geih_sector_departamento` (1.959 filas, departamento×sector CIIU). Ver detalle abajo. |
| Pruebas Saber 11 | ICFES | ~50K/año (según README) | ❌ **Confirmado ausente**: sin rastro de "Saber" o "ICFES" en el dump ni en la BD en vivo; `modelado_aptitudes` (163.976 filas) no tiene ninguna columna que referencie ICFES como fuente. Sigue pendiente. |

## GEIH — cómo se integró (2026-07-13)
El CSV crudo (3,7M registros de personas, 22 columnas: ingresos, informalidad,
sector CIIU, condición de actividad, factor de expansión) **no se versiona**
en el repo — supera el límite de GitHub y el patrón de dumps livianos que ya
sigue este proyecto. En su lugar:
1. `scripts/consolidar_geih.py` lee el CSV (ruta por defecto `data/raw/GEIH_consolidado_2022_2026.csv`,
   override con `--input`), agrega **ponderando por `FACTOR_EXPANSION`** (es
   una encuesta de hogares muestral, no un censo) y **promediando por mes**
   (el panel cubre 52 meses; sumar el factor de los 52 sin promediar infla la
   población estimada ~52x — bug real que se detectó y corrigió durante la
   implementación, ver `Changelog.md`).
2. Carga dos tablas pequeñas y deterministas en `odemiro_db`:
   - `geih_departamento_resumen` (1 fila por departamento: ingreso mediano,
     % informalidad, tasa de desempleo aproximada, población ocupada estimada).
   - `geih_sector_departamento` (departamento × sector CIIU a 2 dígitos, con
     el mismo tipo de cifras; se descartan celdas con <30 observaciones
     crudas por no ser confiables a esa desagregación).
3. El join con SNIES es por **código DANE de departamento** (`DPTO` en GEIH =
   `codigo_del_departamento_programa` en `snies_matriculados` — verificado
   contra la BD real, coinciden exactamente los 33 códigos).
4. Ada ahora usa esto en `_analizar_mercado_laboral()` (cruza el área de
   conocimiento del programa recomendado con sectores CIIU afines vía
   `AREA_CONOCIMIENTO_A_CIIU`, y el departamento del estudiante) para agregar
   una sección real de "Panorama del mercado laboral" al reporte — probado
   end-to-end: para un perfil analítico/técnico en Antioquia, mostró
   correctamente que "Obras de ingeniería civil" tiene el ingreso mediano más
   alto (\$1.600.000) y la informalidad más baja (19.6%) de los sectores
   afines a Ingeniería Civil.

### Cómo se verificó (2026-07-13)
```bash
zcat scripts/init-sql/data/odemiro_db.sql.gz | grep -iE '^CREATE TABLE'
# -> solo snies_matriculados, desercion_academica, modelado_aptitudes

zcat scripts/init-sql/data/odemiro_db.sql.gz | grep -ioE 'geih|saber ?11|icfes|ciiu|informalidad_dane'
# -> sin resultados

mysql ... -e "SELECT table_schema, table_name, column_name FROM information_schema.columns
              WHERE column_name LIKE '%geih%' OR column_name LIKE '%saber%' OR column_name LIKE '%icfes%'"
# -> sin resultados, revisando TODAS las bases del servidor (odemiro_db + gal_prototipo)
```

## Cómo se obtuvieron los datos ya cargados
1. Descarga de los CSV oficiales desde datos.gov.co / MinEducación.
2. Ingesta directa a MySQL sin transformación fuerte de tipos (de ahí que la
   mayoría de columnas de `snies_matriculados` sean `TEXT` — ver nota en
   `scripts/init-sql/create_schema.sql`).
3. Collation unificada `utf8mb4_0900_ai_ci` en las tres tablas para permitir
   cruces (join) entre deserción y matriculados sin errores de collation.

## Acción recomendada antes de la entrega final
GEIH ya quedó integrado (ver arriba). **Solo queda Saber 11 sin resolver**:
el README lo menciona como fuente del `modelado_aptitudes`, pero sigue sin
evidencia de estar cargado. Antes de someter el proyecto al jurado, decidir
entre completar esa ingesta o ajustar el README/arquitectura para no
mencionar Saber 11 como fuente activa.

También falta actualizar la tabla de "Datos Abiertos Utilizados" del
`README.md` (aún dice "GEIH 2022-2026 ... Uso en ADA: Ingresos reales por
sector CIIU, informalidad, empleo" sin aclarar que ya está implementado) y el
diagrama de `docs/architecture/README.md` para reflejar el nuevo cruce
GEIH↔SNIES en el flujo de Ada.
