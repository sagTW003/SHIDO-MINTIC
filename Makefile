# ==========================================
#  ODEM Multiagente - Makefile de Arranque
#  Uso típico (primera vez):   make init
#  Uso diario:                 make start
# ==========================================

SHELL := /bin/bash
PROJECT_ROOT := $(shell pwd)
SCRIPTS_DIR  := $(PROJECT_ROOT)/scripts
INITSQL_DIR  := $(SCRIPTS_DIR)/init-sql
DUMP_FILE    := $(INITSQL_DIR)/data/odemiro_db.sql.gz
SCHEMA_FILE  := $(INITSQL_DIR)/create_schema.sql
ENV_FILE     := $(PROJECT_ROOT)/.env
ENV_EXAMPLE  := $(PROJECT_ROOT)/.env.example
VENV_DIR     := $(PROJECT_ROOT)/.venv
VENV_PY      := $(VENV_DIR)/bin/python3
VENV_PIP     := $(VENV_DIR)/bin/pip

# Credenciales de la BD (se leen del .env; con defaults del proyecto)
ifneq (,$(wildcard $(ENV_FILE)))
include $(ENV_FILE)
endif

DB_HOST ?= 127.0.0.1
DB_PORT ?= 3306
DB_NAME ?= odemiro_db
DB_USER ?= odemiro
DB_PASS ?= odemiro_pass_2026
MYSQL_ROOT_PASSWORD ?= root_pass_2026

GREEN  := \033[0;32m
YELLOW := \033[1;33m
RED    := \033[0;31m
BLUE   := \033[0;34m
NC     := \033[0m

.PHONY: init check-prereqs setup-env load-data install-python test-system \
        start stop restart web help clean

# -----------------------------------------------------------------
# ARRANQUE COMPLETO (primera vez en una máquina nueva)
# -----------------------------------------------------------------
init: check-prereqs setup-env install-python load-data test-system
	@echo ""
	@echo "$(GREEN)✅ ¡SISTEMA LISTO!$(NC)"
	@echo ""
	@echo "$(BLUE)🚀 Levanta la web de Ada con:$(NC)  make web"
	@echo "$(BLUE)🌐 Luego abre:$(NC)                 http://localhost:8081"
	@echo ""
	@echo "$(BLUE)🧪 Prueba Lumina por CLI:$(NC)"
	@echo "   cd src/agents/Lumina && ../../../.venv/bin/python3 Lumina_sql.py \"Ingenierías en Bogotá\""

help:
	@echo "$(BLUE)ODEM Multiagente - Comandos:$(NC)"
	@echo "  $(GREEN)make init$(NC)          - Instala deps, carga la BD y prueba (primera vez)"
	@echo "  $(GREEN)make load-data$(NC)     - (Re)carga la BD desde el dump versionado"
	@echo "  $(GREEN)make install-python$(NC)- Instala dependencias Python de los agentes"
	@echo "  $(GREEN)make web$(NC)           - Levanta la web de Ada (http://localhost:8081)"
	@echo "  $(GREEN)make test$(NC)          - Prueba de integración Lumina -> BD"
	@echo "  $(GREEN)make clean$(NC)         - Borra la BD odemiro_db (⚠️ destructivo)"

# -----------------------------------------------------------------
# PRERREQUISITOS
# -----------------------------------------------------------------
check-prereqs:
	@echo "$(YELLOW)🔍 Verificando prerrequisitos...$(NC)"
	@command -v python3 >/dev/null 2>&1 || { echo "$(RED)❌ Falta python3$(NC)"; exit 1; }
	@command -v pip3    >/dev/null 2>&1 || { echo "$(RED)❌ Falta pip3$(NC)"; exit 1; }
	@command -v mysql   >/dev/null 2>&1 || { echo "$(RED)❌ Falta el cliente mysql (MySQL 8.0)$(NC)"; exit 1; }
	@command -v gunzip  >/dev/null 2>&1 || { echo "$(RED)❌ Falta gunzip$(NC)"; exit 1; }
	@echo "$(GREEN)✅ Prerrequisitos OK$(NC)"

# -----------------------------------------------------------------
# .ENV (copia de la plantilla si no existe)
# -----------------------------------------------------------------
setup-env:
	@if [ ! -f "$(ENV_FILE)" ]; then \
		echo "$(YELLOW)⚙️  Creando .env desde plantilla...$(NC)"; \
		cp "$(ENV_EXAMPLE)" "$(ENV_FILE)"; \
		echo "$(RED)⚠️  Edita $(ENV_FILE) y pon tus API Keys:$(NC)"; \
		echo "   - GEMINI_API_KEY (https://aistudio.google.com/apikey)"; \
		echo "   - NVIDIA_API_KEY (https://build.nvidia.com)"; \
	else \
		echo "$(GREEN)✅ .env ya existe$(NC)"; \
	fi

# -----------------------------------------------------------------
# CARGA DE DATOS  (desde el dump versionado en el repo)
#   1) crea estructura con create_schema.sql
#   2) importa el dump comprimido
#   3) crea el usuario de la app
# -----------------------------------------------------------------
load-data:
	@echo "$(YELLOW)📊 Cargando la BD odemiro_db desde el dump versionado...$(NC)"
	@if [ ! -f "$(DUMP_FILE)" ]; then \
		echo "$(RED)❌ No se encontró $(DUMP_FILE)$(NC)"; \
		echo "   Asegúrate de haber clonado el repo completo."; exit 1; \
	fi
	@echo "   → Creando estructura (create_schema.sql)..."
	@MYSQL_PWD="$(MYSQL_ROOT_PASSWORD)" mysql -h $(DB_HOST) -P $(DB_PORT) -u root < "$(SCHEMA_FILE)"
	@echo "   → Importando datos (~15MB comprimidos, 1-3 min)..."
	@gunzip -c "$(DUMP_FILE)" | MYSQL_PWD="$(MYSQL_ROOT_PASSWORD)" mysql -h $(DB_HOST) -P $(DB_PORT) -u root $(DB_NAME)
	@echo "   → Creando usuario de la app '$(DB_USER)'..."
	@MYSQL_PWD="$(MYSQL_ROOT_PASSWORD)" mysql -h $(DB_HOST) -P $(DB_PORT) -u root -e \
		"CREATE USER IF NOT EXISTS '$(DB_USER)'@'localhost' IDENTIFIED BY '$(DB_PASS)'; \
		 GRANT SELECT,INSERT,UPDATE,DELETE ON $(DB_NAME).* TO '$(DB_USER)'@'localhost'; \
		 FLUSH PRIVILEGES;"
	@echo "$(GREEN)✅ BD cargada (snies_matriculados, desercion_academica, modelado_aptitudes)$(NC)"

# -----------------------------------------------------------------
# DEPENDENCIAS PYTHON
# -----------------------------------------------------------------
install-python:
	@echo "$(YELLOW)🐍 Instalando dependencias Python...$(NC)"
	@if [ ! -x "$(VENV_PY)" ]; then \
		echo "   → Creando entorno virtual (.venv)..."; \
		python3 -m venv "$(VENV_DIR)" || { \
			echo "$(RED)❌ No se pudo crear el venv. Instala el paquete python3-venv (p.ej. 'sudo apt install python3-venv') y vuelve a intentar.$(NC)"; \
			exit 1; \
		}; \
	fi
	@"$(VENV_PIP)" install -q --upgrade pip
	@"$(VENV_PIP)" install -q -r "$(PROJECT_ROOT)/requirements.txt"
	@cd "$(PROJECT_ROOT)/src/agents/Scrapper" && "$(VENV_PY)" -m playwright install chromium >/dev/null 2>&1 || true
	@echo "$(GREEN)✅ Dependencias instaladas en .venv/$(NC)"

# -----------------------------------------------------------------
# WEB DE ADA
# -----------------------------------------------------------------
web:
	@echo "$(YELLOW)🌐 Levantando la web de Ada en http://localhost:8081 ...$(NC)"
	@cd "$(PROJECT_ROOT)/src/agents/Ada" && "$(VENV_PY)" web_ada.py

# -----------------------------------------------------------------
# TEST DE INTEGRACIÓN
# -----------------------------------------------------------------
test-system test:
	@echo "$(YELLOW)🧪 Probando Lumina -> BD...$(NC)"
	@cd "$(PROJECT_ROOT)/src/agents/Lumina" && "$(VENV_PY)" Lumina_sql.py "Cuenta programas de Ingeniería" 2>&1 | grep -q "tipo" \
		&& echo "$(GREEN)✅ Lumina responde OK$(NC)" \
		|| echo "$(YELLOW)⚠️  Lumina en modo fallback (revisa API Keys / BD en .env)$(NC)"

# -----------------------------------------------------------------
# LIMPIEZA (destructiva: borra la base)
# -----------------------------------------------------------------
clean:
	@echo "$(RED)🧹 Esto BORRA la base '$(DB_NAME)'. Escribe SI para confirmar:$(NC)"
	@read -r c && [ "$$c" = "SI" ] || { echo "Cancelado."; exit 1; }
	@MYSQL_PWD="$(MYSQL_ROOT_PASSWORD)" mysql -h $(DB_HOST) -P $(DB_PORT) -u root -e "DROP DATABASE IF EXISTS $(DB_NAME);"
	@echo "$(GREEN)✅ Base eliminada$(NC)"
