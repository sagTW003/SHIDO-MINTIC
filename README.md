# 🎓 ODEM Multiagente ADA — Orientación Vocacional Basada en Evidencia
**Postulación: Concurso "Datos al Ecosistema 2026" — MinTIC Colombia**  
**Entidad:** Universidad EAN — Spin-off ODEM  
**Equipo:** Santiago Acuña González (Líder/PO/Scrum Master/Lead Dev), Viernes (Orquestador IA), Lumina (Analítica SQL), Ada (Orientadora), Scrapper (Minería Web)

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql&logoColor=white)](https://mysql.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![WSL2](https://img.shields.io/badge/WSL2-Ubuntu-0078D4?logo=windows&logoColor=white)](https://learn.microsoft.com/windows/wsl)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Datos Abiertos](https://img.shields.io/badge/Datos_Abiertos-MinTIC_2026-004884?style=flat&logo=google-drive)](https://drive.google.com/drive/folders/TU_GOOGLE_DRIVE_FOLDER_ID_AQUI)

---

## 🎯 **El Problema**
En Colombia, **la deserción universitaria supera el 40%** en muchos programas. Una causa raíz: **mala orientación vocacional**. Los estudiantes eligen carreras sin conocer el mercado laboral real, los costos reales ni su propio perfil de aptitudes.

## 💡 **La Solución: ADA (Sistema Multiagente)**
Un ecosistema de **4 IAs especializadas** que democratiza el acceso a datos oficiales (SNIES, GEIH, ICFES) y entrega una **orientación vocacional personalizada, empática y basada en evidencia** en 4 pasos:
1. **Datos Personales** → Estrato, ingresos, ICFES, municipio.
2. **Test Psicométrico (40 items)** → Escala Likert, 6 dimensiones vocacionales.
3. **Cruce SNIES + GEIH (Tiempo Real)** → Lumina traduce lenguaje natural a SQL y consulta la BD oficial.
4. **Reporte Ejecutivo + Excel** → Ada genera análisis narrativo, gráficas de radar, tablas de deserción por estrato y plan de acción descargable.

---

## 🏗️ **Arquitectura Multiagente**

| Agente | Rol | Tecnología | Entrada | Salida |
| :--- | :--- | :--- | :--- | :--- |
| **Viernes** | Orquestador Principal | Python / OpenClaw | Intención usuario | Plan de ejecución + Coordinación |
| **Lumina** | Text-to-SQL + Analítica | Python + **Gemini 3.5 Flash** + MySQL | Pregunta NL ("Ingenierías en Bogotá < 4M") | JSON: SQL generado + Resultado + Análisis estadístico |
| **Ada** | Orientadora Vocacional Web | Python (HTTP Server) + **Gemini 3.5 Flash** + OpenPyXL | Formulario Web + Respuestas Test | HTML (Radar Chart) + Excel Consolidado (4 hojas) guardado en `reports/` |
| **Scrapper** | Minería de Datos Viva | Python + **Playwright (Chromium)** | URL Objetivo (ICETEX, datos.gov.co) | Excel con convocatorias, becas, cursos actualizados guardado en `reports/` |

**Flujo:** `Usuario (Web:8081) → Ada → Lumina (SQL:3306) → MySQL (SNIES/GEIH) → Ada → Reporte + Excel`

---

## 📊 **Datos Abiertos Utilizados (Fuentes Oficiales)**
| Dataset | Fuente | Registros | Uso en ADA |
| :--- | :--- | :---: | :--- |
| **SNIES Matriculados** | MinEducación / datos.gov.co | ~1.2M | Oferta académica, costos, IES, modalidad, ubicación |
| **Deserción Académica (SPADIES)** | MinEducación | ~3.5K | Riesgo de abandono por programa, facultad, estrato, sexo |
| **GEIH 2022-2026** | DANE | ~2.1M | Ingresos reales por sector CIIU, informalidad, empleo |
| **Pruebas Saber 11** | ICFES | ~50K/año | Perfil de aptitudes entrantes (modelado_aptitudes) |

> **ETL Reproducible:** `scripts/consolidar_geih.py` (limpia 52 meses GEIH, unifica variables P3271/P6040/P6920, crea `INFORMALIDAD_DANE`).

---

## 🚀 **Puesta en Marcha para Jurados (3 Minutos)**

### **Prerrequisitos (Una sola vez)**
| SO | Acción |
| :--- | :--- |
| **Windows 10/11** | Instalar **Docker Desktop** → Settings > General > ✅ "Use WSL 2 based engine" > Resources > WSL Integration > Enable Ubuntu. |
| **Linux / Mac** | `sudo apt install docker.io docker-compose git make` / `brew install docker docker-compose make` |

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
> **Primera vez:** Tarda 3-5 min (descarga datasets ~500MB, levanta BD, carga datos, instala deps Python/Playwright).  
> **Veces siguientes:** Instantáneo (`docker-compose up -d`).

---

## ✅ **Verificación Rápida (Checklist Jurado)**

| Componente | Acceso | Qué Probar |
| :--- | :--- | :--- |
| **🌐 Ada Web (Demo Principal)** | Abrir `http://localhost:8081` | 1. Llenar datos → 2. Test 40 preg → 3. **"Generar Reporte"** → Ver Radar Chart + **Botón "Descargar Excel"** |
| **🗄️ Adminer (Inspector BD)** | Abrir `http://localhost:8080` | Sistema: MySQL / Servidor: `mysql-odem` / User: `odemiro` / Pass: `odemiro_pass_2026` / DB: `odemiro_db` → Ver tablas `snies_matriculados`, `desercion_academica` |
| **⚡ Lumina CLI (Motor SQL)** | `cd src/agents/Lumina && python3 Lumina_sql.py "Ingenierías virtuales en Medellín bajo 5 millones"` | Debe imprimir JSON: `{"tipo":"SQL", "sql":"SELECT...", "respuesta":"Análisis en lenguaje natural..."}` |
| **🕷️ Scrapper (Minería Viva)** | `cd src/agents/Scrapper && python3 Scrapper.py "https://www.icetex.gov.co/becas"` | Genera `Scrapper_ICETEX_....xlsx` en `reports/` con convocatorias reales. |

---

## 📁 **Estructura del Repositorio**
```text
SHIDO-MINTIC/
├── .github/workflows/       # CI/CD (opcional)
├── src/
│   └── agents/
│       ├── Ada/
│       │   ├── Ada.py                 # Motor principal (CLI + Multiagente API)
│       │   ├── web_ada.py             # Servidor Web HTTP (Puerto 8081) + Frontend HTML/JS embebido
│       │   ├── preguntas_estructuradas.json   # 40 items test vocacional (6 dimensiones)
│       │   └── requirements.txt
│       ├── Lumina/
│       │   ├── Lumina.py
│       │   ├── Lumina_sql.py          # Text-to-SQL + Gemini + MySQL + Fallback Offline
│       │   └── requirements.txt
│       └── Scrapper/
│           ├── Scrapper.py            # Playwright Chromium + Selectores multi-plataforma
│           └── requirements.txt
├── scripts/
│   ├── db_utils/                  # Utilidades y ETL de la BD
│   ├── init-sql/
│   │   └── create_schema.sql      # DDL Tablas SNIES, Deserción, Modelado
│   ├── consolidar_geih.py         # ETL GEIH 52 meses → CSV unificado + INFORMALIDAD_DANE
│   ├── download_data.sh           # Descarga datasets desde Google Drive (wget + gdown)
│   └── load_mysql.sh              # Carga masiva SQL/CSV en contenedor MySQL
├── docs/
│   ├── Informe_MinTIC_ADA.docx    # Informe técnico CRISP-ML + Scrum (9 secciones)
│   └── Manual_Usuario_ADA.docx    # Manual usuario final + Instalación + Troubleshooting
├── reports/                       # Carpeta para reportes generados (.txt, .xlsx)
├── data/                          # Carpeta local para exportables (.csv, dumps)
├── docker-compose.yml             # Orquesta: MySQL 8.0 + Adminer (UI BD)
├── Makefile                       # 🎯 ENTRY POINT: make init
├── .env.example                   # Plantilla config (API Keys, DB)
├── .gitignore                     # Ignora .env, data/, venv/, *.sql.gz, *.xlsx, __pycache__
├── requirements.txt               # Deps Python globales
└── README.md                      # Este archivo
```

---

## ⚙️ **Detalles Técnicos Clave**

### **Modelos de IA (Estrategia Híbrida Costo-Cero)**
| Tarea | Modelo | Proveedor | Costo | Fallback |
| :--- | :--- | :--- | :--- | :--- |
| Chat diario, Scrapper, Lumina SQL Gen | **Nemotron 3 Ultra 550B** | NVIDIA | **$0 (Gratis)** | Gemini 3.5 Flash |
| Reporte Ada (RAG + Redacción), Lumina Análisis | **Gemini 3.5 Flash** | Google | **$0 (Free Tier)** | Nemotron 3 Ultra |
| *Configurable en `.env` y `session_status`* | | | | |

### **Base de Datos (MySQL 8.0 en Docker)**
- **Volumen persistente:** `mysql_data` (sobrevive a `docker-compose down`).
- **Healthcheck:** `mysqladmin ping` antes de aceptar conexiones.
- **Usuario app:** `odemiro` / `odemiro_pass_2026` (solo localhost / red docker).
- **Adminer:** Puerto 8080 para inspección visual del jurado.

### **Frontend Web (Ada)**
- **Single-file:** `web_ada.py` sirve HTML/JS/CSS embebido (sin build, sin Node).
- **Test 40 preguntas:** Cargadas dinámicas desde `preguntas_estructuradas.json`.
- **Progreso:** Guardado en `localStorage` (sobrevive a recargas).
- **Charts:** Radar Chart via QuickChart.io (no requiere librerías pesadas en cliente).
- **Excel:** Generado en backend con OpenPyXL (3 hojas principales + 1 hoja dinámica por carrera consultada).

---

## 🛠️ **Comandos Útiles (Makefile)**

```bash
make init          # 🎯 Setup completo (prerrequisitos, .env, BD, datos, deps, test)
make start         # Levanta solo BD (docker-compose up -d)
make stop          # Para contenedores (docker-compose down)
make logs          # Ver logs de MySQL
make test-lumina   # Prueba rápida Lumina CLI
make test-ada      # Levanta web_ada.py en background y prueba curl
make clean         # 💥 NUCLEAR: Borra contenedores, volúmenes, .env, data/, __pycache__
make rebuild       # clean + init (empezar de cero limpio)
```

---

## 🐛 **Troubleshooting Rápido**

| Síntoma | Causa Probable | Solución |
| :--- | :--- | :--- |
| `make init` falla en `download-data` | IDs de Google Drive incorrectos | Edita `Makefile` líneas `wget ... id=TU_FILE_ID...` con tus File IDs reales |
| `docker-compose up` puerto 3306 ocupado | MySQL local corriendo en host | `sudo systemctl stop mysql` (Linux) / Detener servicio MySQL en Windows Services |
| Ada Web: "Error 500 / Timeout" | Lumina tarda > 120s (Gemini lento) | Aumenta timeout en `web_ada.py` línea `timeout=120` → `300` |
| Lumina: "BD Error 1045 Access denied" | Contenedor MySQL no healthy aún | `make stop && make start` y espera 10s antes de `make load-data` |
| Scrapper: "playwright not found" | Deps no instaladas | `cd src/agents/Scrapper && pip3 install -r requirements.txt && python3 -m playwright install chromium` |
| **API Key Inválida (401/400)** | Key expirada / mal copiada | Regenera en proveedor → Edita `.env` → `make stop && make start` (Modo Offline automático cubre demo) |

> **Modo Offline Automático:** Si *cualquier* API falla, Lumina y Ada responden con **datos simulados realistas** (8.430 matriculados, 14.2% deserción, distribución género 55/45) para que la demo **nunca se rompa**.

---

## 📄 **Documentación Entregada (Carpeta `docs/`)**
1.  **`Informe_MinTIC_ADA.docx`** — Informe técnico oficial estructura MinTIC: Ciclo de vida SW, Metodologías vs Ágiles, Scrum (Roles/Eventos/Artefactos), CRISP-ML (6 Fases), Integración Scrum+CRISP-ML, Historias de Usuario (HU01, HU02, HU03) con Criterios Gherkin.
2.  **`Manual_Usuario_ADA.docx`** — Guía completa: Modelo multiagente explicado simple, Web Ada paso a paso, Requisitos HW/SW, Instalación OpenClaw + Docker + WSL2, Configuración TODAS las API Keys, Instalación en nueva PC, **Troubleshooting 10 errores comunes** con solución copy-paste.

---

## 🔗 **Datos Abiertos (Entrega MinTIC)**
Los datasets pesados (>100MB) **NO están en GitHub**. Se entregan vía **Google Drive / Zenodo** (enlace público):
- `odemiro_db_dump.sql.gz` — Dump completo BD (esquema + datos)
- `snies_matriculados.csv` — Tabla principal limpia
- `desercion_academica.csv` — Tabla deserción por estrato/sexo/programa
- `geih_consolidado_2022_2026.csv` — GEIH 52 meses unificado (script `consolidar_geih.py`)
- `diccionario_datos.xlsx` — Metadatos: campo, tipo, descripción, fuente, ejemplo

> **Enlace Jurado:** [📁 Carpeta Datos Abiertos MinTIC 2026](https://drive.google.com/drive/folders/TU_GOOGLE_DRIVE_FOLDER_ID_AQUI)

---

## 👨‍💻 **Autores & Contacto**
- **Santiago Acuña González** — Ingeniero Sistemas, Líder Técnico ODEM, Universidad EAN  
  📧 `sacunag19002@universidadean.edu.co` | 💼 LinkedIn: `santiago-acuna-gonzalez`
- **Equipo IA ODEM:** Viernes (Orquestador), Lumina (SQL), Ada (Vocacional), Scrapper (Web)

---

## 📜 **Licencia**
Código: **MIT License** — Úsalo, modifícalo, aprende.  
Datos: **CC0 / Dominio Público** (Fuentes: SNIES MinEducación, GEIH DANE, ICFES — Ley 1712 Transparencia).

---

> **"La mejor orientación no es la que te dice qué estudiar, sino la que te muestra la realidad para que tú decidas."** — ADA, 2026