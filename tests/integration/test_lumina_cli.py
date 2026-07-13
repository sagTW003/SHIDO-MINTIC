"""Smoke test end-to-end: Lumina_sql.py responde con JSON válido a una
pregunta en lenguaje natural, usando la BD y la API key reales del .env.

Se marca `integration` porque depende de red (Gemini/NVIDIA) y de que la BD
esté cargada. Se salta automáticamente si no hay API key configurada.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
LUMINA_DIR = REPO_ROOT / "src" / "agents" / "Lumina"

load_dotenv(REPO_ROOT / ".env")

pytestmark = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY") and not os.environ.get("NVIDIA_API_KEY"),
    reason="Requiere GEMINI_API_KEY o NVIDIA_API_KEY configurada en .env",
)


def test_lumina_sql_returns_valid_json():
    result = subprocess.run(
        [sys.executable, "Lumina_sql.py", "Ingeniería de Sistemas"],
        cwd=str(LUMINA_DIR),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"Lumina_sql.py falló: {result.stderr}"
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert "sql" in payload
    assert "respuesta" in payload
