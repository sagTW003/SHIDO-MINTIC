# Estructura del Repositorio — Sistema Multiagente ODEM (MinTIC 2026)

Estructura real (limpia; se quitaron las carpetas vacías de la plantilla recomendada
que no se estaban usando).

```
ODEM_PORTATIL/
├── .env / .env.example        # Credenciales (GEMINI_API_KEY, DB) — .env NO se versiona
├── .gitignore
├── README.md                  # Guía principal del proyecto
├── Makefile
├── docker-compose.yml
├── requirements.txt           # Dependencias globales
│
├── src/
│   └── agents/                # Sistema multiagente
│       ├── Ada/               # Orientación vocacional (Ada.py + web_ada.py + preguntas)
│       ├── Lumina/            # SQL / analítica SNIES (Lumina_sql.py, Lumina.py)
│       └── Scrapper/          # Web scraping becas/convocatorias (Playwright + Gemini)
│
├── docs/                      # Documentación
│   ├── estructura.md          # Este archivo
│   └── *.docx                 # Informes, manual técnico, guía del aspirante (MinTIC)
│
├── reports/
│   └── ada_historico/         # Reportes .txt generados por Ada
│
└── scripts/
    ├── db_utils/              # Utilidades DB (exportar_csv, limpiar_db, show_schema, etc.)
    └── init-sql/              # SQL de inicialización
```

## Base de datos (la que usa Lumina)

- **Motor:** MySQL local, escuchando en `127.0.0.1:3306`
- **Base de datos:** `odemiro_db`
- **Usuario/clave:** `odemiro` / (ver `.env`, variable `DB_PASS`)
- **Ubicación física en disco (datadir):** `/var/lib/mysql/odemiro_db/`  (~364 MB)
- **Tablas:**
  - `snies_matriculados`  — ~920.934 filas (matrículas SNIES)
  - `modelado_aptitudes`  — ~163.976 filas
  - `desercion_academica` — ~3.280 filas (casos de pérdida de cupo)
- **Collation unificada:** `utf8mb4_0900_ai_ci` en ambas tablas clave, para que el
  cruce deserción↔matriculados funcione.

> No es un archivo dentro del repo: vive en el servidor MySQL del sistema (WSL),
> no en la carpeta OneDrive. Lumina se conecta por red (TCP) leyendo credenciales del `.env`.

## Operación

- **Servidor web de Ada:** servicio systemd `ada-web.service` → http://localhost:8081
  - WorkingDir: `src/agents/Ada` · `systemctl --user restart ada-web.service`
- Todos los agentes cargan `.env` de la raíz (loader propio; sube 3 niveles desde `src/agents/<Agente>/`).
