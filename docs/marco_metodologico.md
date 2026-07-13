# Marco Metodológico

> El detalle completo de metodología (CRISP-ML, Scrum, Historias de Usuario
> con criterios Gherkin) está documentado en
> [`docs/Informe_MinTIC_ADA_vf.docx`](./Informe_MinTIC_ADA_vf.docx). Este
> archivo resume esa metodología en formato texto plano para navegación
> rápida por parte del jurado, sin reemplazar el informe oficial.

## Gestión del proyecto: Scrum
- **Roles:** Santiago Acuña González — Líder/Product Owner/Scrum Master/Lead
  Dev. Agentes IA como colaboradores especializados (Viernes: orquestador,
  Lumina: analítica SQL, Ada: orientación, Scrapper: minería web).
- Artefactos y eventos Scrum, Historias de Usuario (HU01, HU02, HU03) con
  criterios de aceptación en formato Gherkin: ver informe oficial.

## Ciclo de vida del dato/modelo: CRISP-ML
El proyecto sigue las 6 fases de CRISP-ML(Q) adaptadas al caso de uso:
1. **Business & Data Understanding** — `docs/planteamiento_problema.md`,
   `docs/fuentes_datos.md`.
2. **Data Preparation** — carga de SNIES/SPADIES/aptitudes a MySQL
   (`scripts/init-sql/`), normalización de collation para permitir joins.
3. **Modeling** — no hay modelo predictivo entrenado en esta entrega; el
   "modelo" es el pipeline text-to-SQL (Lumina) + generación de reporte con
   LLM (Ada), no un clasificador/regresor tradicional. Ver limitación en
   `docs/conclusiones.md`.
4. **Evaluation** — verificación manual/funcional (esta auditoría) +
   `tests/` (smoke tests agregados en esta iteración).
5. **Deployment** — servicio `systemd --user` (`ada-web.service`) sirviendo
   `web_ada.py` en `:8081`; MySQL como servicio local en `:3306`;
   `docker-compose.yml` disponible como alternativa contenedorizada.
6. **Monitoring** — pendiente: no hay logging estructurado ni métricas de uso
   más allá del log plano de systemd (`~/.openclaw/workspace/logs/ada-web.log`).

## Nota de honestidad metodológica
Dado que no hay un modelo de machine learning entrenado (el sistema es
orquestación de LLMs + consultas SQL sobre datos abiertos), términos como
"modelo predictivo" en la comunicación del proyecto deben usarse con cuidado
frente al jurado para no sobre-representar la componente de ML vs. la
componente de orquestación de agentes/LLM.
