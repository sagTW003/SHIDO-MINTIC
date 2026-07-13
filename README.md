# 🎓 ODEM Multiagente ADA — Orientación Vocacional Basada en Evidencia
**Postulación: Concurso "Datos al Ecosistema 2026" — MinTIC Colombia**  
**Entidad:** Universidad EAN — Spin-off ODEM  
**Equipo:** Santiago Acuña González (Líder/PO/Scrum Master/Lead Dev), Viernes (Orquestador IA), Lumina (Analítica SQL), Ada (Orientadora), Scrapper (Minería Web)

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql&logoColor=white)](https://mysql.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![WSL2](https://img.shields.io/badge/WSL2-Ubuntu-0078D4?logo=windows&logoColor=white)](https://learn.microsoft.com/windows/wsl)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Datos Abiertos](https://img.shields.io/badge/Datos_Abiertos-incluidos_en_el_repo-004884?style=flat&logo=github)](scripts/init-sql/data/odemiro_db.sql.gz)

---

## 🎯 **El Problema**
En Colombia, **la deserción universitaria supera el 40%** en muchos programas. Una causa raíz: **mala orientación vocacional**. Los estudiantes eligen carreras sin conocer el mercado laboral real, los costos reales ni su propio perfil de aptitudes.

## 💡 **La Solución: ADA (Sistema Multiagente)**
Un ecosistema de **3 agentes de IA especializados** (Lumina, Ada, Scrapper) que democratiza el acceso a datos oficiales (SNIES, GEIH) y entrega una **orientación vocacional personalizada, empática y basada en evidencia** en 4 pasos:
1. **Datos Personales** → Estrato, ingresos, ICFES, municipio.
2. **Test Psicométrico (40 items)** → Escala Likert, 6 dimensiones vocacionales.
3. **Cruce SNIES + GEIH (Tiempo Real)** → Lumina traduce lenguaje natural a SQL y consulta la BD oficial.
4. **Reporte Ejecutivo + Excel** → Ada genera análisis narrativo, gráficas de radar, tablas de deserción por estrato y plan de acción descargable.

---

## 🏗️ **Arquitectura Multiagente**

| Agente | Rol | Tecnología | Entrada | Salida |
| :--- | :--- | :--- | :--- | :--- |
| **Lumina** | Text-to-SQL + Analítica | Python + **Gemini 3.5 Flash** + MySQL (5 tablas) | Pregunta NL ("Ingenierías en Bogotá", "ingreso e informalidad en Antioquia") | JSON: SQL generado + Resultado + Análisis estadístico |
| **Ada** | Orientadora Vocacional Web | Python (HTTP Server) + **Gemini 3.5 Flash** + OpenPyXL | Formulario Web + Respuestas Test | HTML (Radar Chart) + Excel + reporte con deserción y mercado laboral (GEIH), guardado en `reports/` |
| **Scrapper** | Minería de Datos Viva | Python + **Playwright (Chromium)** | URL Objetivo (ICETEX, datos.gov.co) | Excel con convocatorias, becas, cursos actualizados guardado en `reports/` |

> **Nota sobre "Viernes":** aparece en la concepción del equipo como orquestador
> conceptual, pero **no tiene código propio** en `src/agents/` — hoy Ada
> invoca a Lumina directamente vía `subprocess` (ver `Ada.py`). Ver
> `docs/architecture/README.md` para el detalle.

**Flujo real:** `Usuario (Web:8081) → Ada → Lumina (subprocess, SQL:3306) → MySQL (SNIES+deserción+GEIH) → Ada → Reporte + Excel`

---

## 📊 **Datos Abiertos Utilizados (Fuentes Oficiales)**
| Dataset | Fuente | Registros | Uso en ADA |
| :--- | :--- | :---: | :--- |
| **SNIES Matriculados** | MinEducación / datos.gov.co | 1.048.575 | Oferta académica, IES, modalidad, ubicación (NO incluye costo de matrícula) |
| **Deserción Académica (SPADIES)** | MinEducación | 3.368 | Riesgo de abandono por programa, facultad, estrato, sexo |
| **GEIH 2022-2026** | DANE | 3.696.094 registros crudos → agregados en 33 (por depto.) + 1.959 (depto.×sector CIIU) filas | Ingreso mediano e informalidad real por sector económico y departamento |
| **Modelado de Aptitudes** | Interno ODEM | 163.739 | Referencia para el test vocacional de 40 ítems |

> ⚠️ Pruebas Saber 11 (ICFES) se planeó como fuente pero **no está integrada todavía** — no confundir con `modelado_aptitudes`, que es una tabla interna sin relación verificada con ICFES.
>
> **ETL Reproducible:** `scripts/consolidar_geih.py` — agrega el CSV crudo de la GEIH (52 meses) ponderando por `FACTOR_EXPANSION`, promediando por mes, y carga dos tablas (`geih_departamento_resumen`, `geih_sector_departamento`) en `odemiro_db`.

---

## 🚀 **Puesta en Marcha para Jurados (3 Minutos)**

### **Prerrequisitos (Una sola vez)**
`make init` (el flujo probado y recomendado) usa **MySQL nativo**, no Docker:

| SO | Acción |
| :--- | :--- |
| **Windows 10/11** | WSL2 + Ubuntu, con `python3`, `pip3`, `mysql-server` (o cliente `mysql` apuntando a un MySQL 8.0 accesible) y `make` instalados dentro de la distro. |
| **Linux / Mac** | `sudo apt install mysql-server git make python3-pip` / `brew install mysql git make python` |

> Alternativa: si prefieres MySQL en contenedor, `docker-compose.yml` levanta MySQL 8.0 + Adminer (`docker compose up -d`) — pero **`make init` no lo usa por defecto**, así que si vas por Docker tendrás que cargar el dump manualmente (ver `REPRODUCIBILIDAD.md`, Opción C).

### **Clonar, Configurar y Arrancar**
```bash
# 1. Clonar repositorio
git clone https://github.com/sagTW003/SHIDO-MINTIC.git
cd SHIDO-MINTIC

# 2. Configurar API Keys (OBLIGATORIO - 2 keys gratuitas)
#    Copia el archivo de ejemplo para crear tu propio archivo oculto .env:
cp .env.example .env

# 👇 EDITA .env AHORA (Puedes usar nano .env o code .env)
#    Dentro del archivo .env, pega tus claves en las siguientes variables:
#    NVIDIA_API_KEY=tu_clave_aqui   (gratis: https://build.nvidia.com/explore/discover)
#    GEMINI_API_KEY=tu_clave_aqui   (gratis: https://aistudio.google.com/apikey)
#    (Nota: Anthropic Claude es opcional y de pago, puedes dejarla comentada).

# 3. COMANDO MÁGICO ÚNICO ☕
make init
```
> `make init` instala dependencias Python, importa el dump versionado del repo
> (`scripts/init-sql/data/odemiro_db.sql.gz`, ~15MB, ya incluye SNIES +
> deserción + aptitudes + GEIH — **no descarga nada externo**) y corre una
> prueba de integración. Toma 1-3 minutos.
> **Veces siguientes:** `make load-data` para recargar la BD, `make web` para levantar la demo.

---

## ✅ **Verificación Rápida (Checklist Jurado)**

| Componente | Acceso | Qué Probar |
| :--- | :--- | :--- |
| **🌐 Ada Web (Demo Principal)** | Abrir `http://localhost:8081` | 1. Llenar datos → 2. Test 40 preg → 3. **"Generar Reporte"** → Ver Radar Chart + **Botón "Descargar Excel"** |
| **🗄️ Inspector BD (mysql CLI)** | `mysql -u odemiro -p odemiro_db -e "SHOW TABLES;"` (pass en tu `.env`) | Ver las 5 tablas: `snies_matriculados`, `desercion_academica`, `modelado_aptitudes`, `geih_departamento_resumen`, `geih_sector_departamento`. Si prefieres una UI, usa Adminer vía `docker compose up -d adminer` (puerto 8080) contra tu MySQL. |
| **⚡ Lumina CLI (Motor SQL)** | `cd src/agents/Lumina && python3 Lumina_sql.py "Ingenierías virtuales en Medellín"` | Debe imprimir JSON: `{"tipo":"SQL", "sql":"SELECT...", "respuesta":"Análisis en lenguaje natural..."}` |
| **🕷️ Scrapper (Minería Viva)** | `cd src/agents/Scrapper && python3 Scrapper.py "https://www.icetex.gov.co/becas"` | Genera `Scrapper_ICETEX_....xlsx` en `reports/` con convocatorias reales. |

---

## 📁 **Estructura del Repositorio**
```text
SHIDO-MINTIC/
├── .github/workflows/ci.yml       # CI: compila sintaxis Python + tests unitarios
├── src/
│   ├── agents/
│   │   ├── Ada/
│   │   │   ├── Ada.py                 # Motor principal (CLI + Multiagente API)
│   │   │   ├── web_ada.py             # Servidor Web HTTP (Puerto 8081) + Frontend HTML/JS embebido
│   │   │   ├── preguntas_estructuradas.json   # 40 items test vocacional (6 dimensiones)
│   │   │   └── requirements.txt
│   │   ├── Lumina/
│   │   │   ├── Lumina.py
│   │   │   ├── Lumina_sql.py          # Text-to-SQL + Gemini + MySQL (5 tablas, incl. GEIH)
│   │   │   └── requirements.txt
│   │   └── Scrapper/
│   │       ├── Scrapper.py            # Playwright Chromium + Selectores multi-plataforma
│   │       └── requirements.txt
│   └── __init__.py
├── scripts/
│   ├── db_utils/                  # Utilidades de la BD (exportar, limpiar, ver esquema)
│   ├── init-sql/
│   │   ├── create_schema.sql      # DDL de las 5 tablas
│   │   └── data/odemiro_db.sql.gz # Dump versionado (~15MB): SNIES+deserción+aptitudes+GEIH
│   └── consolidar_geih.py         # ETL: CSV crudo GEIH (52 meses) → tablas geih_* agregadas
├── docs/                          # Informes oficiales MinTIC + documentación técnica (ver docs/)
├── tests/                         # unit / integration / bias_tests (pytest)
├── notebooks/, models/, data/     # Esqueleto para EDA / artefactos de modelo — ver README de cada carpeta
├── reports/                       # Reportes generados en runtime (.txt, .xlsx) — no versionados
├── docker-compose.yml             # MySQL 8.0 + Adminer en contenedor (alternativa opcional, no usada por `make init`)
├── Makefile                       # 🎯 ENTRY POINT: make init
├── .env.example                   # Plantilla config (API Keys, DB)
├── .gitignore
├── requirements.txt               # Deps Python globales
├── LICENSE, Changelog.md, REPRODUCIBILIDAD.md
└── README.md                      # Este archivo
```

---

## ⚙️ **Detalles Técnicos Clave**

### **Modelos de IA (Estrategia Híbrida Costo-Cero)**
| Tarea | Modelo primario | Proveedor | Costo | Fallback |
| :--- | :--- | :--- | :--- | :--- |
| Ada (reporte), Lumina (SQL Gen + Análisis), Scrapper | **Gemini 3.5 Flash** (con cascada a 2.5/2.0/flash-latest si el primario satura) | Google | **$0 (Free Tier)** | Nemotron 3 Ultra (NVIDIA) — solo si hay `NVIDIA_API_KEY` configurada |
| *Todos los agentes llaman a Gemini directamente por REST (sin SDK); NVIDIA es opcional* | | | | |

### **Base de Datos (MySQL 8.0)**
- **Setup por defecto:** MySQL nativo (WSL/Linux), servicio `mysql`/`mysqld` en `127.0.0.1:3306` — así corre en el entorno probado para esta entrega.
- **Alternativa en contenedor:** `docker-compose.yml` (MySQL 8.0 + Adminer), opcional, no usada por `make init`.
- **Usuario app:** `odemiro` / (ver `DB_PASS` en tu `.env`).
- **Datos:** dump versionado en `scripts/init-sql/data/odemiro_db.sql.gz` — 5 tablas, se carga automáticamente con `make init` / `make load-data`.

### **Frontend Web (Ada)**
- **Single-file:** `web_ada.py` sirve HTML/JS/CSS embebido (sin build, sin Node).
- **Test 40 preguntas:** Cargadas dinámicas desde `preguntas_estructuradas.json`.
- **Progreso:** Guardado en `localStorage` (sobrevive a recargas).
- **Charts:** Radar Chart via QuickChart.io (no requiere librerías pesadas en cliente).
- **Excel:** Generado en backend con OpenPyXL (3 hojas principales + 1 hoja dinámica por carrera consultada).

---

## 🛠️ **Comandos Útiles (Makefile)**

```bash
make init          # 🎯 Setup completo (prerrequisitos, .env, deps Python, carga BD, test)
make help          # Lista todos los comandos disponibles
make load-data     # (Re)carga la BD desde el dump versionado del repo
make install-python# Instala/actualiza dependencias Python de los agentes
make web           # Levanta la web de Ada (http://localhost:8081)
make test          # Prueba de integración: Lumina -> BD
make clean         # ⚠️ Destructivo: DROP DATABASE odemiro_db (pide confirmación explícita)
```

---

## 🐛 **Troubleshooting Rápido**

| Síntoma | Causa Probable | Solución |
| :--- | :--- | :--- |
| `make init` falla en `load-data` | MySQL no está corriendo, o falta `mysql` client | Verifica `mysql --version` y que el servicio esté activo (`sudo systemctl status mysql`) |
| Puerto 3306 ocupado por otro MySQL | Otra instancia de MySQL corriendo | Detén la otra instancia, o ajusta `DB_PORT` en `.env` si vas a usar el `docker-compose.yml` opcional |
| Ada Web: "Error 500 / Timeout" | Lumina tarda > 220s (Gemini lento/saturado) | El timeout entre `web_ada.py` y `Ada.py` está en `subprocess.run(..., timeout=220)` en `web_ada.py`; auméntalo si hace falta |
| Lumina: "BD Error 1045 Access denied" | Usuario `odemiro` no creado aún, o `.env` con credenciales distintas a las de tu MySQL | Vuelve a correr `make load-data` (crea el usuario) y revisa `DB_USER`/`DB_PASS` en `.env` |
| Scrapper: "playwright not found" | Deps no instaladas | `cd src/agents/Scrapper && pip3 install -r requirements.txt && python3 -m playwright install chromium` |
| **API Key Inválida (401/400)** | Key expirada / mal copiada | Regenera en el proveedor (Gemini o NVIDIA) → edita `.env` |

> **Nota sobre disponibilidad:** el flujo de recomendación de programas SNIES de Ada tiene una cascada de respaldo (consulta directa a MySQL → Lumina vía LLM → datos locales de referencia) que no depende de que las APIs de IA respondan. La **redacción del reporte final sí requiere** que al menos un proveedor de IA (Gemini o NVIDIA) esté disponible — si ambos fallan, el reporte muestra el error real en vez de inventar contenido.

---

## 📄 **Documentación Entregada (Carpeta `docs/`)**
1.  **`Informe_MinTIC_ADA_vf.docx`** — Informe técnico oficial estructura MinTIC: Ciclo de vida SW, Metodologías vs Ágiles, Scrum (Roles/Eventos/Artefactos), CRISP-ML (6 Fases), Integración Scrum+CRISP-ML, Historias de Usuario con Criterios Gherkin.
2.  **`Manual_tecnico_ADA_vf.docx`** — Manual técnico: modelo multiagente, instalación, configuración de API Keys, troubleshooting.
3.  **`Guia_del_aspirante_ADA.docx`** — Guía dirigida al usuario final (aspirante a educación superior).
4.  Además, `docs/*.md` — diccionario de datos, fuentes de datos, planteamiento del problema, marco metodológico, evaluación de impacto público, y arquitectura, generados a partir del estado real del sistema (ver cada archivo).

---

## 🔗 **Datos Abiertos (Entrega MinTIC)**
El dump completo de la base de datos (esquema + datos, las 5 tablas: SNIES,
deserción, aptitudes y los dos agregados de GEIH) **sí está en este
repositorio de GitHub** — pesa ~15MB, muy por debajo del límite de 100MB, así
que **clonar el repo = tener los datos**, sin pasos manuales ni enlaces
externos:
- [`scripts/init-sql/data/odemiro_db.sql.gz`](scripts/init-sql/data/odemiro_db.sql.gz) — dump completo (se carga automático con `make init`)
- [`scripts/init-sql/create_schema.sql`](scripts/init-sql/create_schema.sql) — DDL de las 5 tablas
- [`docs/data_dictionary.md`](docs/data_dictionary.md) — diccionario de datos (campo, tipo, descripción, fuente)

**Lo único que NO viaja en el repo** es el CSV crudo de la GEIH
(`GEIH_consolidado_2022_2026.csv`, ~400MB, 3,7M registros de personas) — ya
está agregado y cargado en las tablas `geih_departamento_resumen` /
`geih_sector_departamento` del dump de arriba, así que no hace falta para
correr o evaluar el sistema. Si se quiere reprocesar desde cero con un CSV
más reciente: colocarlo en `data/raw/` y correr `scripts/consolidar_geih.py`
(ver `REPRODUCIBILIDAD.md`).

---

## 👨‍💻 **Autores & Contacto**
- **Santiago Acuña González** — Ingeniero Sistemas, Líder Técnico ODEM, Universidad EAN  
  📧 `sacunag19002@universidadean.edu.co` | 💼 LinkedIn: `santiago-acuna-gonzalez`
- **Equipo IA ODEM:** Viernes (Orquestador), Lumina (SQL), Ada (Vocacional), Scrapper (Web)

---

## 📜 **Licencia**
Código: **MIT License** — Úsalo, modifícalo, aprende.  
Datos: **CC0 / Dominio Público** (Fuentes: SNIES MinEducación, SPADIES MinEducación, GEIH DANE — Ley 1712 Transparencia).

---

> **"La mejor orientación no es la que te dice qué estudiar, sino la que te muestra la realidad para que tú decidas."** — ADA, 2026