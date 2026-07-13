"""Smoke tests: la BD odemiro_db está viva y las 3 tablas tienen datos."""
import os
import sys

import mysql.connector
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

REQUIRED_TABLES = {"snies_matriculados", "desercion_academica", "modelado_aptitudes"}


def _connect():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("DB_PORT", 3306)),
        user=os.environ.get("DB_USER", "odemiro"),
        password=os.environ.get("DB_PASS", ""),
        database=os.environ.get("DB_NAME", "odemiro_db"),
    )


@pytest.fixture(scope="module")
def db_conn():
    try:
        conn = _connect()
    except mysql.connector.Error as exc:
        pytest.skip(f"MySQL no disponible en este entorno: {exc}")
    yield conn
    conn.close()


def test_required_tables_exist(db_conn):
    cur = db_conn.cursor()
    cur.execute("SHOW TABLES")
    tables = {row[0] for row in cur.fetchall()}
    missing = REQUIRED_TABLES - tables
    assert not missing, f"Faltan tablas requeridas: {missing}"


@pytest.mark.parametrize("table", sorted(REQUIRED_TABLES))
def test_tables_have_rows(db_conn, table):
    cur = db_conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM `{table}`")
    count = cur.fetchone()[0]
    assert count > 0, f"La tabla {table} está vacía"
