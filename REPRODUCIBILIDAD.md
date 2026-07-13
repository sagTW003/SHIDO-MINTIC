# 🔁 Reproducibilidad — Sistema Multiagente ODEM

Guía para clonar el repositorio y dejar **todo el sistema funcionando** en otra
máquina con pocos comandos.

---

## 📦 Qué incluye el repositorio

La base de datos **viaja dentro del repo** como un dump comprimido (≈15 MB), así
que **clonar = tener los datos**. No hay descargas externas ni pasos manuales.

```
ODEM_PORTATIL/
├── scripts/init-sql/
│   ├── create_schema.sql          # Estructura REAL de las 5 tablas
│   └── data/
│       └── odemiro_db.sql.gz       # Datos comprimidos (SNIES + deserción + aptitudes + GEIH agregado)
├── src/agents/
│   ├── Ada/        # Orientación vocacional + web (:8081)
│   ├── Lumina/     # Text-to-SQL sobre la BD SNIES
│   └── Scrapper/   # Scraping de becas (ICETEX)
├── .env.example    # Plantilla de configuración (copiar a .env)
├── Makefile        # Automatización (make init / make web / make test)
└── requirements.txt
```

### Base de datos `odemiro_db` (MySQL 8.0)
| Tabla | Filas | Contenido |
|---|---|---|
| `snies_matriculados`  | ~921.000 | Oferta académica SNIES (programas, IES, matriculados) |
| `desercion_academica` | ~3.300   | Deserción por programa/estrato/género/facultad |
| `modelado_aptitudes`  | ~164.000 | Modelado de aptitudes |
| `geih_departamento_resumen` | 33 | Panorama laboral (ingreso, informalidad, desempleo) por departamento — agregado GEIH/DANE, ver `scripts/consolidar_geih.py` |
| `geih_sector_departamento` | 1.959 | Igual, desagregado por sector económico (CIIU) |

---

## ✅ Requisitos en la máquina destino

- **Python 3.10+** y `pip3`
- **MySQL 8.0** (cliente `mysql` + servidor corriendo en `127.0.0.1:3306`)
- `gunzip` y `make` (vienen en Linux/WSL/macOS por defecto)

> El código está probado sobre **MySQL nativo** (Linux/WSL). También hay un
> `docker-compose.yml` si prefieres levantar MySQL + Adminer en contenedores.

---

## 🚀 Opción A — Arranque automático (recomendado)

```bash
git clone <URL-DEL-REPO> ODEM_PORTATIL
cd ODEM_PORTATIL

cp .env.example .env
#   edita .env  ->  pon tu GEMINI_API_KEY y NVIDIA_API_KEY

make init      # instala deps, crea BD, importa datos y hace un test
make web       # levanta la web de Ada en http://localhost:8081
```

`make init` te pedirá la contraseña de **root de MySQL** para crear la base y el
usuario `odemiro`.

---

## 🔧 Opción B — Manual (3 comandos de BD)

Si no quieres usar `make`:

```bash
# 1. Estructura
mysql -u root -p < scripts/init-sql/create_schema.sql

# 2. Datos (descomprime e importa)
gunzip -c scripts/init-sql/data/odemiro_db.sql.gz | mysql -u root -p odemiro_db

# 3. Usuario de la aplicación
mysql -u root -p -e "CREATE USER IF NOT EXISTS 'odemiro'@'localhost' IDENTIFIED BY 'odemiro_pass_2026'; \
  GRANT SELECT,INSERT,UPDATE,DELETE ON odemiro_db.* TO 'odemiro'@'localhost'; FLUSH PRIVILEGES;"

# 4. Dependencias Python
pip3 install -r requirements.txt

# 5. Configuración
cp .env.example .env    # y edita tus API keys

# 6. Arranca la web
cd src/agents/Ada && python3 web_ada.py    # http://localhost:8081
```

---

## 🐳 Opción C — MySQL con Docker

```bash
docker compose up -d mysql-odem adminer       # MySQL en :3306, Adminer en :8080
make load-data                                 # carga el dump en el contenedor
```

---

## 🔑 Variables de entorno (`.env`)

```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=odemiro_db
DB_USER=odemiro
DB_PASS=odemiro_pass_2026

GEMINI_API_KEY=tu_key_de_google_aistudio
NVIDIA_API_KEY=tu_key_de_nvidia
```

- **GEMINI_API_KEY** — obligatoria (Ada y Lumina generan texto/SQL con Gemini).
  Ada y Lumina tienen **fallback automático** entre `gemini-3.5-flash` →
  `gemini-2.5-flash` → `gemini-2.0-flash` → `gemini-flash-latest` si el modelo
  primario está saturado (HTTP 503).
- **NVIDIA_API_KEY** — opcional (cliente alterno).

---

## 🧪 Verificar que quedó bien

```bash
make test
# ✅ Lumina responde OK   -> BD y API funcionando
```

O prueba manual:
```bash
cd src/agents/Lumina && python3 Lumina_sql.py "'Ingeniería de Sistemas'"
# Devuelve JSON con el SQL generado y filas reales del SNIES
```

---

## 📝 Notas para mantenimiento

- **Regenerar el dump** (si actualizas la BD):
  ```bash
  mysqldump -u odemiro -p --no-tablespaces --single-transaction \
    odemiro_db snies_matriculados desercion_academica modelado_aptitudes \
    geih_departamento_resumen geih_sector_departamento \
    | gzip -9 > scripts/init-sql/data/odemiro_db.sql.gz
  ```
- **Refrescar GEIH** (si aparece un CSV más reciente de la GEIH): coloca el
  CSV en `data/raw/` y corre `python3 scripts/consolidar_geih.py`, luego
  regenera el dump con el comando de arriba. El CSV crudo (~400MB) nunca se
  versiona; solo las tablas agregadas.
- El `.gitignore` **versiona** solo `create_schema.sql` y `odemiro_db.sql.gz`;
  ignora reportes generados, CSV crudos y `.env`.
- El dump (15 MB) está por debajo del límite de 100 MB de GitHub, por lo que
  **no requiere Git LFS**.
