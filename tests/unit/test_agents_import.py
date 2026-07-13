"""Smoke tests: los módulos de los 3 agentes importan sin errores.

No requieren red ni API keys reales: solo validan que las dependencias
declaradas en cada requirements.txt están instaladas y que no hay errores
de sintaxis/import a nivel de módulo.
"""
import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTS = {
    "Ada": REPO_ROOT / "src" / "agents" / "Ada",
    "Lumina": REPO_ROOT / "src" / "agents" / "Lumina",
    "Scrapper": REPO_ROOT / "src" / "agents" / "Scrapper",
}
MODULES = {"Ada": "Ada", "Lumina": "Lumina", "Scrapper": "Scrapper"}


@pytest.mark.parametrize("agent", sorted(AGENTS))
def test_agent_module_imports(agent):
    agent_dir = str(AGENTS[agent])
    sys.path.insert(0, agent_dir)
    try:
        importlib.import_module(MODULES[agent])
    except ImportError as exc:
        pytest.fail(f"El módulo de {agent} no pudo importarse: {exc}")
    finally:
        sys.path.remove(agent_dir)
