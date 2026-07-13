# Evaluación de Impacto, Ética y Mitigación de Sesgos

## Impacto público esperado
ODEM busca reducir la asimetría de información que enfrenta un aspirante a
educación superior de bajos recursos frente a uno con acceso a orientación
vocacional privada, usando exclusivamente datos abiertos oficiales (SNIES,
SPADIES, ICFES/GEIH cuando estén integrados).

## Variables sensibles identificadas
La tabla `desercion_academica` (ver `docs/data_dictionary.md`) contiene:
`estrato`, `genero`, `origen_geografico`. Estas variables son necesarias para
que el análisis de riesgo de deserción sea representativo (la deserción en
Colombia está correlacionada con estrato y procedencia geográfica según
SPADIES), pero su uso indebido puede producir:
- **Sesgo de desaliento**: recomendar en contra de una carrera a un estudiante
  de estrato bajo basándose solo en la tasa histórica de deserción de su
  estrato, en vez de en su perfil individual (aptitudes, motivación).
- **Estereotipos de género** en la sugerencia de programas académicos.

## Mitigaciones actuales
- Las variables sensibles se usan para **contextualizar el reporte**
  (ej. "en tu estrato la deserción en este programa es X%, considera estos
  apoyos"), no para bloquear ni filtrar programas disponibles al usuario.
- El test vocacional (40 ítems, 6 dimensiones) pondera el perfil individual
  del estudiante, no solo variables demográficas.

## Mitigaciones pendientes (no implementadas aún)
- No existen pruebas automatizadas (`tests/bias_tests/`) que verifiquen que,
  ante perfiles idénticos salvo por `estrato` o `genero`, el sistema no
  cambie sistemáticamente el conjunto de programas recomendados.
- No hay un mecanismo de auditoría/logging que permita revisar después si el
  agente Ada generó lenguaje desalentador correlacionado con estas variables.

## Privacidad
Ninguna de las tres tablas cargadas contiene PII directa (nombre, documento,
contacto) — ver nota final de `docs/data_dictionary.md`. Los datos que el
usuario ingresa en el formulario web (Ada) para generar su reporte
personalizado deben tratarse conforme a la Ley 1581 de 2012 (Habeas Data);
verificar que `reports/` (donde se guardan los reportes generados) no se
versione en Git con datos de usuarios reales — ya cubierto por `.gitignore`
(`reports/*.txt`, `reports/*.xlsx`).

## Recomendación
Antes de escalar el sistema más allá de esta demo, priorizar la
implementación de `tests/bias_tests/` como criterio de aceptación, no como
mejora opcional.
