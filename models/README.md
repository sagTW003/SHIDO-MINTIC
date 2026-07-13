# Models

Carpeta reservada para artefactos de modelos, siguiendo la convención sugerida:

- `predictive/` — modelos de analítica avanzada / detección de anomalías
  (ej. un futuro modelo de riesgo de deserción entrenado sobre
  `desercion_academica`, hoy usada solo como consulta agregada — ver
  limitación en `docs/conclusiones.md`).
- `llm_rag/` — embeddings/prompts del sistema conversacional. **Nota:** hoy
  Ada y Lumina no usan RAG ni embeddings; llaman directamente a la API de
  Gemini/NVIDIA con prompt engineering. Esta carpeta queda vacía hasta que se
  implemente recuperación aumentada real (ej. sobre `docs/data_dictionary.md`
  o el `Informe_MinTIC_ADA_vf.docx`).
- `simulation/` — no aplica todavía a este proyecto (no hay simulación de
  escenarios sociodemográficos implementada).

**Estado actual:** el sistema no entrena ni serializa modelos propios — es
orquestación de LLMs externos (Gemini/NVIDIA) + consultas SQL. Ver
`docs/marco_metodologico.md`, sección "Nota de honestidad metodológica".
