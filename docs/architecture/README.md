# Arquitectura Multiagente ODEM

```
Usuario (navegador)
      │  HTTP :8081
      ▼
┌─────────────┐      pregunta NL      ┌─────────────┐      SQL       ┌──────────────┐
│     Ada     │ ────────────────────▶ │   Lumina    │ ──────────────▶│  MySQL 8.0   │
│ (web_ada.py)│                        │(Lumina_sql.py)│ ◀────────────│ odemiro_db   │
│ Gemini 3.5  │ ◀──────────────────── │ Gemini/NVIDIA │   filas JSON  │  :3306       │
└─────────────┘   JSON: sql+respuesta └─────────────┘                └──────────────┘
      │
      │ genera
      ▼
Reporte HTML (Radar Chart) + Excel (openpyxl) → reports/

┌─────────────┐
│  Scrapper   │  Playwright + Gemini/NVIDIA → convocatorias/becas → reports/*.xlsx
└─────────────┘  (independiente, se invoca por CLI: python3 Scrapper.py <url>)
```

- **Ada** (`src/agents/Ada/`): único punto de entrada web. Corre como
  servicio `systemd --user` (`ada-web.service`) en `:8081`. Además de SNIES
  y deserción, `_analizar_mercado_laboral()` cruza el área de conocimiento
  del programa recomendado con sectores CIIU afines en
  `geih_sector_departamento` (GEIH/DANE, agregado por
  `scripts/consolidar_geih.py`) para dar ingreso mediano e informalidad
  reales del departamento del estudiante.
- **Lumina** (`src/agents/Lumina/`): text-to-SQL. Se invoca desde Ada vía
  `subprocess` (ver `import subprocess` en `Ada.py`) o directamente por CLI.
- **Scrapper** (`src/agents/Scrapper/`): agente independiente, no está en el
  camino crítico de la demo web; se ejecuta manualmente por CLI.
- **"Viernes"** (orquestador mencionado en el README) no tiene código propio
  en `src/agents/` — actualmente su rol de orquestación está repartido entre
  `Ada.py` (invoca a Lumina vía subprocess) y el propio flujo del frontend.
  Si el jurado pregunta por "Viernes" como agente independiente, aclarar que
  es conceptual/de coordinación, no un proceso separado en esta versión.

> Diagrama fuente (`Presentacion.pptx` / draw.io) pendiente de agregar aquí
> como imagen exportada (`.png`/`.svg`) — este README es el respaldo en texto
> mientras tanto.
