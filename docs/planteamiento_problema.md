# Planteamiento del Problema

## Contexto
En Colombia, la deserción universitaria supera el **40%** en muchos programas
(SPADIES / MinEducación). Una causa raíz identificada es la **mala orientación
vocacional**: los estudiantes eligen carrera sin conocer el mercado laboral
real, los costos reales de la formación ni su propio perfil de aptitudes.

## Problema específico
La información oficial que permitiría una decisión informada existe (SNIES,
GEIH, SPADIES, Saber 11) pero está **fragmentada, dispersa en portales
distintos y en formato no accesible** para un aspirante a educación superior
o su familia. No existe una herramienta que:
1. Traduzca preguntas en lenguaje natural a consultas sobre estos datasets.
2. Cruce el perfil socioeconómico y vocacional del estudiante con la oferta
   académica real y las probabilidades de deserción por programa/estrato.
3. Entregue un reporte accionable (no solo datos crudos).

## Población objetivo
Aspirantes a educación superior en Colombia (recién egresados de bachillerato,
población en riesgo de deserción temprana) y sus familias, particularmente en
municipios/estratos con menor acceso a orientación vocacional profesional.

## Hipótesis de solución
Un sistema multiagente que democratiza el acceso a estos datos abiertos vía
lenguaje natural (Lumina), los combina con un perfil vocacional psicométrico
(Ada) y monitorea oportunidades de financiación vigentes (Scrapper) reduce la
fricción de acceso a información que hoy solo está al alcance de quienes
pueden pagar orientación vocacional privada.

## Alcance de esta entrega
- Fuente de datos: SNIES matriculados, deserción académica (SPADIES),
  modelado de aptitudes — ver `docs/data_dictionary.md` y `docs/fuentes_datos.md`.
- Fuera de alcance en esta versión: costos de matrícula por programa (no
  disponibles en el dataset SNIES usado — ver limitación en
  `docs/conclusiones.md`), datos GEIH consolidados (ETL referenciado pero no
  incluido en esta entrega), predicción individual de deserción (la tabla
  `desercion_academica` se usa como referencia agregada, no como modelo
  predictivo entrenado).
