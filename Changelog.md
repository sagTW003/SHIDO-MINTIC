# Changelog

Registro cronológico de versiones y cambios del sistema multiagente ODEM.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [Unreleased]

### Fixed
- **`.gitignore`**: el patrón `data/` sin ancla también ignoraba
  `scripts/init-sql/data/`, y la excepción `!scripts/init-sql/data/odemiro_db.sql.gz`
  nunca funcionaba (git no permite des-ignorar un archivo si su carpeta padre
  ya está ignorada) — el dump de la BD nunca se habría podido versionar.
  Corregido a `/data/` (anclado a la raíz del repo).
- **`Lumina_sql.py` truncaba el SQL generado** (`maxOutputTokens: 2048`) al
  pedir preguntas que cruzan SNIES con las tablas `geih_*` (esquema más
  grande, JOIN más largo) — reproducido con "ingreso e informalidad para
  Ingeniería de Sistemas en Antioquia": el SQL se cortaba a mitad del
  `WHERE`, MySQL lo aceptaba igual (sin error, por cómo evalúa una columna de
  texto como condición booleana) y devolvía 0 filas silenciosamente, sin que
  el mecanismo de auto-corrección se activara. Subido a 4096.
- **El LLM inventaba valores exactos de columnas de texto** (p.ej.
  `sector_nombre = 'Actividades de programación, consultoría...'`, un valor
  que no existe tal cual en la tabla) en vez de usar `LIKE`, dando 0 filas
  aunque el dato sí existiera. Se agregó instrucción explícita en
  `SYSTEM_BASE` (Lumina) para usar `LIKE '%palabra_clave%'` o consultar
  `SELECT DISTINCT` primero en vez de adivinar el texto completo.
- `ada-web.service` apuntaba a una ruta obsoleta (`ODEM_PORTATIL`) tras el
  renombramiento del proyecto a `SHIDO_MINTIC`, causando un bucle de reinicio
  (`status=200/CHDIR`) y dejando la demo web (`:8081`) inaccesible.
- `import anthropic` sin uso real en `Ada.py`, `Lumina.py` y `Scrapper.py`
  (ninguno invoca la API de Claude) rompía `make init` en una máquina limpia
  porque `anthropic` no estaba en el `requirements.txt` raíz. Eliminado.
- `.gitignore` con el patrón `src/agents/**/*.txt` ignoraba silenciosamente
  los 3 `requirements.txt` de los agentes (coincidencia no intencional con
  el patrón pensado para los reportes `Ada_Reporte_*.txt`). Acotado.
- `import google.generativeai as genai` en `Ada.py` era código muerto
  (`genai.` nunca se invocaba) y arrastraba una dependencia **deprecada por
  Google** ("all support has ended"). Eliminado de `Ada.py` y de
  `requirements.txt`; Gemini ya se llama por REST directo en los 3 agentes,
  así que no hace falta el SDK `google-genai` — la cascada de fallback
  (`gemini-3.5-flash` → `gemini-2.5-flash` → `gemini-2.0-flash` →
  `gemini-flash-latest`) sigue funcionando sin cambios.
- **Bug de recomendación de programas (Ada.py)**: el score de afinidad SNIES
  era un no-op — cada programa se etiquetaba con una copia del perfil del
  ESTUDIANTE en vez de su propia identidad, así que el score daba siempre el
  mismo valor y no ordenaba nada por relevancia real. Corregido en dos
  commits lógicos:
  1. `_tags_programa()`: etiqueta cada programa con las palabras clave cuyo
     patrón (`PERFIL_A_REGEXP`) coincide con SU nombre/área real, no con el
     perfil del estudiante.
  2. `_score_afinidad()`: pondera el score por el promedio real del
     estudiante en la categoría de cada palabra clave del programa
     (`self.promedios_categorias`), en vez de solo contar coincidencias —
     evita que categorías con más entradas en el diccionario (p.ej.
     "administración", 6 palabras clave) le ganen a categorías realmente
     dominantes del estudiante con menos entradas (p.ej. "analítico", 5).
  Verificado con un perfil sintético analítico/técnico: antes recomendaba
  Psicología/Derecho/Administración; después, Ingeniería Civil como primera
  opción (score 4.40 vs 3.09 del segundo lugar).
- **`poblacion_ocupada_estimada` en `consolidar_geih.py`** sumaba
  `FACTOR_EXPANSION` de los 52 meses del panel GEIH sin promediar, inflando
  la población estimada ~52x (Antioquia mostraba 7.6M de personas solo en
  construcción de edificios). Corregido: se divide por el número de meses
  distintos presentes en cada grupo.

### Added
- **Integración de GEIH-DANE (2026-07-13)**: `scripts/consolidar_geih.py`
  agrega el CSV crudo de la GEIH (3,7M registros, ene-2022 a abr-2026,
  ponderado por `FACTOR_EXPANSION`) en dos tablas nuevas de `odemiro_db`:
  `geih_departamento_resumen` (33 filas) y `geih_sector_departamento` (1.959
  filas, departamento × sector CIIU a 2 dígitos). El CSV crudo (~400MB) NO se
  versiona; las tablas agregadas sí, en el mismo dump
  (`scripts/init-sql/data/odemiro_db.sql.gz`, ahora con 5 tablas). Ada usa
  esto en `_analizar_mercado_laboral()` para agregar al reporte una sección
  real de ingreso mediano e informalidad del sector afín al programa
  recomendado, en el departamento del estudiante — determinista, sin LLM
  para los números (igual patrón que `_analizar_desercion`).
- **System prompts actualizados para usar GEIH**: `SYSTEM_BASE` (Lumina) ahora
  documenta las 5 tablas (incluyendo `geih_departamento_resumen` /
  `geih_sector_departamento`, la clave de cruce con SNIES por código de
  departamento, y que las cifras ya vienen ponderadas). `SYSTEM_Ada` ahora
  explica que Ada tiene datos reales de mercado laboral para complementar el
  análisis de deserción con "qué tan bien pago y formal es el sector al que
  ese programa suele llevar". Probado end-to-end: Lumina CLI respondió con
  cifras reales (ingreso mediano y % informalidad) cruzando "Ingeniería de
  Sistemas" + "Antioquia"; el reporte de Ada incluyó la sección "Panorama del
  mercado laboral (GEIH-DANE)" con las mismas cifras reales.
- `LICENSE` (MIT), alineado con lo declarado en `README.md`.
- Repositorio Git inicializado (`main`).
- Estructura `tests/` (unit, integration, bias_tests) con pruebas de humo
  iniciales para Lumina, Ada y la conexión a la base de datos.
- `docs/data_dictionary.md` generado a partir del esquema real
  (`scripts/init-sql/create_schema.sql`).
- `docs/planteamiento_problema.md`, `docs/fuentes_datos.md`,
  `docs/conclusiones.md`, `docs/public_impact_assessment.md`.
- Carpetas `notebooks/`, `models/`, `reports/figures/` (esqueleto).
- Workflow de CI (`.github/workflows/ci.yml`) con compilación de sintaxis
  Python y linter básico.

## [1.0.0] — 2026-07-08
- Versión presentada al concurso "Datos al Ecosistema 2026" — MinTIC:
  agentes Ada (orientación vocacional web), Lumina (text-to-SQL sobre SNIES/
  deserción), Scrapper (minería de becas/convocatorias), base de datos MySQL
  con datasets oficiales (SNIES, SPADIES, aptitudes).
