# Conclusiones, Limitaciones y Próximos Pasos

## Hallazgos de la verificación técnica (2026-07-13)
- El pipeline central **funciona de extremo a extremo**: Lumina traduce
  lenguaje natural a SQL válido contra `odemiro_db` y devuelve resultados
  reales del SNIES (verificado con la consulta "Ingenierías virtuales en
  Medellín bajo 5 millones").
- Ada (servidor web, puerto 8081) sirve correctamente el frontend HTML/JS
  embebido.
- Las tres tablas de la base de datos están cargadas y accesibles con las
  credenciales declaradas en `.env`.

## Limitaciones conocidas
1. **Costos de matrícula no disponibles**: Lumina lo reporta explícitamente
   cuando se le pregunta por "programas bajo X millones" — el dataset SNIES
   cargado no incluye la variable de costo. Cualquier claim de "orientación
   por costos reales" en el README debe matizarse o completarse con esa
   fuente antes de la entrega.
2. ~~**GEIH y Saber 11 confirmados ausentes**~~ — **GEIH resuelto (2026-07-13)**:
   se ubicó el CSV real (`GEIH_consolidado_2022_2026.csv`, 3.7M registros,
   409MB) y se integró vía `scripts/consolidar_geih.py` en dos tablas nuevas
   de `odemiro_db` (`geih_departamento_resumen`, `geih_sector_departamento`),
   ya incluidas en el dump versionado. Ada las usa en
   `_analizar_mercado_laboral()` para agregar una sección real de mercado
   laboral (ingreso mediano, informalidad por sector CIIU) al reporte — ver
   detalle en `docs/fuentes_datos.md`. **Saber 11 sigue sin evidencia de estar
   cargado.**
3. **Bug de scoring corregido (2026-07-13)**: el "score de afinidad" que
   debía rankear programas SNIES según el perfil vocacional del estudiante
   era un no-op (cada programa se etiquetaba con una copia del perfil del
   ESTUDIANTE en vez de su propia área). Se corrigió en dos pasos: (a)
   etiquetar cada programa con sus propias palabras clave reales
   (`_tags_programa`), y (b) ponderar el score por el promedio real de cada
   categoría del test vocacional (`_score_afinidad`, usa
   `self.promedios_categorias`) en vez de solo contar coincidencias — esto
   evitaba que categorías con más entradas en el diccionario (p.ej.
   "administración") le ganaran a categorías realmente dominantes del
   estudiante. Verificado end-to-end: un perfil sintético analítico/técnico
   pasó de recomendar Psicología/Derecho/Administración (bug) a recomendar
   Ingeniería Civil como primera opción (score 4.40 vs 3.09 del segundo).
3. ~~**Dependencia de `google-generativeai`**~~ — **RESUELTO (2026-07-13)**:
   el import era código muerto (`genai.` nunca se invocaba en `Ada.py`); Ada,
   Lumina y Scrapper ya llaman a Gemini directamente por REST
   (`requests.post` a `generativelanguage.googleapis.com`), sin depender de
   ningún SDK de Google. Se eliminó el import y la entrada del
   `requirements.txt` raíz. No hace falta migrar a `google-genai`: la
   cascada de fallback (`gemini-3.5-flash` → `gemini-2.5-flash` →
   `gemini-2.0-flash` → `gemini-flash-latest`) sigue intacta y se probó
   funcional tras el cambio (ver `docs/planteamiento_problema.md` no aplica;
   prueba manual: `Lumina_sql.py "Ingeniería de Sistemas"` devolvió JSON
   válido después de quitar el import).
4. **Modo offline**: el README promete fallback a datos simulados si las APIs
   fallan; no se verificó ese camino en esta revisión (requeriría invalidar
   las API keys a propósito).

## Próximos pasos sugeridos
- Decidir y ejecutar la acción de `docs/fuentes_datos.md` sobre Saber 11
  (completar la ingesta real o ajustar el README) **antes de la entrega**.
- Actualizar `README.md` para reflejar que GEIH ya está integrado (la tabla
  de "Datos Abiertos Utilizados" y el diagrama de arquitectura siguen
  redactados como si fuera solo una promesa).
- Agregar pruebas automatizadas de sesgo (`tests/bias_tests/`) sobre el uso de
  `estrato` y `genero` en las recomendaciones de Ada.
- El crosswalk `AREA_CONOCIMIENTO_A_CIIU` (Ada.py) es una primera aproximación
  razonable pero manual; validar con alguien de GEIH/mercado laboral si los
  sectores CIIU asignados a cada área SNIES son los más representativos.
- Publicar el repositorio en GitHub (`git remote add origin ...` + push) —
  el README ya referencia `https://github.com/sagTW003/SHIDO-MINTIC.git`
  como si existiera.
