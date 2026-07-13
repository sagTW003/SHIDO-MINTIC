import mysql.connector
import sys
import json
import requests
import os

BASES_SISTEMA = {'information_schema', 'mysql', 'performance_schema', 'sys'}


def _cargar_env():
    """Carga variables de un archivo .env en la raiz de SHIDO_MINTIC (sin dependencias)."""
    aqui = os.path.dirname(os.path.abspath(__file__))
    raiz = os.path.dirname(os.path.dirname(os.path.dirname(aqui)))  # .../SHIDO_MINTIC
    ruta_env = os.path.join(raiz, ".env")
    if not os.path.exists(ruta_env):
        return
    try:
        with open(ruta_env, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea or linea.startswith("#") or "=" not in linea:
                    continue
                clave, _, valor = linea.partition("=")
                clave = clave.strip()
                valor = valor.strip().strip('"').strip("'")
                # No pisar variables ya definidas en el entorno real
                if clave and clave not in os.environ:
                    os.environ[clave] = valor
    except Exception:
        pass


_cargar_env()

# API Key de Gemini (leída de variable de entorno GEMINI_API_KEY o del .env)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    print("ADVERTENCIA: Variable de entorno GEMINI_API_KEY no establecida. Las llamadas a la API fallarán.", file=sys.stderr)

# Credenciales de base de datos (leídas del entorno / .env)
DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
DB_PORT = int(os.environ.get("DB_PORT", "3306"))
DB_USER = os.environ.get("DB_USER", "odemiro")
DB_PASS = os.environ.get("DB_PASS", "")
DB_NAME = os.environ.get("DB_NAME", "odemiro_db")


def conectar_db():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        connection_timeout=10
    )

def consultar_db(query):
    conexion = conectar_db()
    cursor = conexion.cursor()
    cursor.execute(query)
    resultados = cursor.fetchall()
    columnas = [col[0] for col in cursor.description]
    cursor.close()
    conexion.close()
    return resultados, columnas

def obtener_schema():
    try:
        conexion = conectar_db()
        cursor = conexion.cursor()
        cursor.execute("SHOW DATABASES")
        todas_las_bases = [row[0] for row in cursor.fetchall()]
        bases_usuario = [db for db in todas_las_bases if db.lower() not in BASES_SISTEMA]
        schema_text = "Bases de datos disponibles:\n\n"
        for base in bases_usuario:
            cursor.execute(f"SELECT table_name, column_name, column_type FROM information_schema.columns WHERE table_schema = '{base}' ORDER BY table_name, ordinal_position")
            tablas = {}
            for tabla, columna, tipo in cursor.fetchall():
                if tabla not in tablas: tablas[tabla] = []
                tablas[tabla].append(f"{columna} ({tipo})")
            if tablas:
                schema_text += f"--- Base de datos: {base} ---\n"
                for tabla, columnas in tablas.items():
                    schema_text += f"  {tabla}({', '.join(columnas)})\n"
                schema_text += "\n"
        cursor.close()
        conexion.close()
        return schema_text
    except Exception as e:
        return f"Error leyendo esquema DB: {str(e)}"

historial = []

# Modelo primario + fallbacks de rendimiento similar para Lumina.
# Si gemini-3.5-flash esta saturado (503/5xx) se reintenta en cascada.
MODELOS_FALLBACK = [
    "gemini-3.5-flash",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-flash-latest",
]


def chat(client_placeholder, prompt_usuario, system_prompt):
    historial.append({"role": "user", "content": prompt_usuario})
    
    contents = []
    es_primero = True
    for msg in historial:
        r = "user" if msg["role"] == "user" else "model"
        t = msg["content"]
        if es_primero and r == "user":
            t = f"INSTRUCCIONES DEL SISTEMA:\n{system_prompt}\n\nUSUARIO:\n{t}"
            es_primero = False
        contents.append({"role": r, "parts": [{"text": t}]})
        
    payload = {
        "contents": contents,
        # 2048 se quedaba corto y truncaba el SQL a mitad de un JOIN/WHERE
        # (reproducido con preguntas que cruzan snies_matriculados con las
        # tablas geih_* -- el esquema ahora es mas grande y el JOIN mas largo).
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 4096}
    }
    
    ultimo_error = None
    for model_name in MODELOS_FALLBACK:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        try:
            res = requests.post(url, json=payload, timeout=45)
            if res.status_code == 200:
                data = res.json()
                respuesta = data["candidates"][0]["content"]["parts"][0]["text"]
                historial.append({"role": "assistant", "content": respuesta})
                return respuesta
            else:
                ultimo_error = f"Gemini HTTP {res.status_code}: {res.text}"
                # Modelo saturado / no disponible / no encontrado -> probar el siguiente
                if res.status_code in (500, 503, 429, 404, 400):
                    continue
                # Error de auth -> no lo arregla otro modelo
                if res.status_code in (401, 403):
                    break
        except Exception as e:
            ultimo_error = f"Excepcion con {model_name}: {str(e)}"
            continue
    raise Exception(ultimo_error or "Gemini no devolvio respuesta con ningun modelo.")

SYSTEM_BASE = (
    "Eres Lumina, asistente virtual para ODEM (Universidad EAN). "
    "Tu objetivo es traducir el lenguaje natural a consultas SQL precisas o dar respuestas conversacionales. "
    "Tienes 5 tablas en odemiro_db: "
    "snies_matriculados (oferta académica SNIES: programa, IES, área de conocimiento, "
    "departamento/municipio de oferta, matriculados; NO incluye costo de matrícula); "
    "desercion_academica (casos de pérdida de cupo por programa/estrato/género, SPADIES); "
    "modelado_aptitudes (aptitudes vocacionales de referencia); "
    "geih_departamento_resumen (1 fila por departamento: ingreso mediano, % informalidad, "
    "tasa de desempleo — encuesta GEIH-DANE); "
    "geih_sector_departamento (lo mismo, desagregado por sector económico CIIU a 2 dígitos). "
    "El cruce entre SNIES y GEIH es por código de departamento: "
    "snies_matriculados.codigo_del_departamento_programa = geih_departamento_resumen.dpto "
    "= geih_sector_departamento.dpto. "
    "Las cifras de las tablas geih_* YA vienen agregadas y ponderadas por el factor de "
    "expansión de la encuesta — NO intentes recalcularlas ni volver a promediarlas, úsalas "
    "tal cual. "
    "Cuando la pregunta sea sobre oportunidades laborales, empleabilidad, ingresos o mercado "
    "de trabajo de una carrera (no solo sobre matrícula/oferta académica), cruza SNIES con "
    "geih_sector_departamento por departamento en vez de responder solo con matrícula. "
    "IMPORTANTE sobre columnas de texto (sector_nombre, departamento, programa_academico, etc.): "
    "NO conoces los valores EXACTOS almacenados, así que NUNCA los compares con '=' adivinando "
    "el texto completo (p.ej. sector_nombre = 'Actividades de programación...') — eso casi "
    "siempre da 0 filas aunque el dato exista. En vez de eso, usa `LIKE '%palabra_clave%'` con "
    "1-2 palabras clave del tema (p.ej. sector_nombre LIKE '%program%' o LIKE '%inform%' para "
    "tecnología/sistemas), o si no estás segura, primero consulta los valores distintos "
    "(SELECT DISTINCT sector_nombre FROM geih_sector_departamento) antes de filtrar. "
    "Sé analítica y precisa; nunca inventes cifras que no vengan de la base de datos — si un "
    "dato no está disponible (p.ej. costo de matrícula), dilo explícitamente en vez de estimarlo."
)

def decidir_tipo_pregunta(client, pregunta):
    prompt = f"Decide si la pregunta requiere consultar una base de datos (SQL) o es solo conversación (CHAT). Responde ÚNICAMENTE con: SQL o CHAT.\n\nPregunta: {pregunta}"
    try:
        return chat(None, prompt, SYSTEM_BASE).strip().upper().replace('```', '')
    except:
        return "SQL"

def _limpiar_sql(sql):
    """Extrae una unica sentencia SQL limpia del texto devuelto por el modelo.
    Elimina bloques de codigo markdown, prosa y texto posterior al ';'."""
    import re as _re
    if not sql:
        return ""
    # Quitar fences de markdown
    sql = sql.replace("```sql", "").replace("```SQL", "").replace("```", "").strip()
    # Si hay un bloque que empieza en una palabra clave SQL, tomar desde ahi
    m = _re.search(r"(SELECT|WITH|SHOW|DESCRIBE|EXPLAIN)\b", sql, _re.IGNORECASE)
    if m:
        sql = sql[m.start():]
    # Cortar en el primer ';' (una sola sentencia) y descartar prosa posterior
    if ";" in sql:
        sql = sql.split(";", 1)[0]
    # Eliminar lineas que sean claramente prosa (no contienen tokens SQL tipicos
    # y parecen frases en lenguaje natural con puntuacion de oracion)
    lineas = []
    for ln in sql.splitlines():
        stripped = ln.strip()
        # Descartar comentarios en linea con prosa larga
        if stripped.startswith("--") and len(stripped) > 60:
            continue
        lineas.append(ln)
    sql = "\n".join(lineas).strip()
    return sql


def generar_sql(client, pregunta, schema):
    prompt = (
        f"Usa este esquema para generar UNA sola consulta SQL de MySQL valida. Usa `base.tabla` siempre.\n\n{schema}\n\n"
        f"Pregunta: {pregunta}\n\n"
        f"REGLAS ESTRICTAS:\n"
        f"- Devuelve UNICAMENTE la sentencia SQL, nada mas.\n"
        f"- NO uses bloques de codigo markdown.\n"
        f"- NO agregues explicaciones, prosa ni comentarios en lenguaje natural.\n"
        f"- Debe ser una unica sentencia terminada en ';'.\n"
        f"- Si necesitas justificaciones o analisis, NO los incluyas en el SQL; solo consulta los datos."
    )
    sql = chat(None, prompt, SYSTEM_BASE).strip()
    sql = _limpiar_sql(sql)
    return sql

def corregir_sql(client, pregunta, schema, sql_malo, error_db):
    """Pide a Gemini corregir un SQL que fallo, dandole el error exacto de MySQL."""
    prompt = (
        f"La siguiente consulta SQL de MySQL fallo. Corrigela.\n\n"
        f"Esquema disponible:\n{schema}\n\n"
        f"Pregunta original: {pregunta}\n\n"
        f"SQL que fallo:\n{sql_malo}\n\n"
        f"Error de MySQL:\n{error_db}\n\n"
        f"REGLAS ESTRICTAS:\n"
        f"- Devuelve UNICAMENTE la sentencia SQL corregida, nada mas.\n"
        f"- NO uses bloques de codigo markdown ni explicaciones.\n"
        f"- Presta atencion a comillas mal cerradas y nombres de columnas del esquema.\n"
        f"- Debe ser una unica sentencia terminada en ';'."
    )
    sql = chat(None, prompt, SYSTEM_BASE).strip()
    return _limpiar_sql(sql)


def ejecutar_sql_con_reintentos(pregunta, schema, sql_inicial, max_reintentos=2):
    """Ejecuta SQL; si falla por error de sintaxis/DB, pide correccion a Gemini y reintenta.
    Retorna (datos, columnas, sql_final). Lanza la ultima excepcion si agota reintentos."""
    sql = sql_inicial
    ultimo_error = None
    for intento in range(max_reintentos + 1):
        try:
            datos, columnas = consultar_db(sql)
            return datos, columnas, sql
        except Exception as e_db:
            ultimo_error = e_db
            if intento < max_reintentos:
                try:
                    sql_corregido = corregir_sql(None, pregunta, schema, sql, str(e_db))
                    if sql_corregido and sql_corregido.strip() and sql_corregido.strip() != sql.strip():
                        sql = sql_corregido
                        continue
                except Exception:
                    pass
            # Sin correccion util o reintentos agotados
            raise ultimo_error
    raise ultimo_error


def responder_con_datos(client, pregunta, datos, columnas):
    prompt = f"El usuario preguntó: {pregunta}\n\nColumnas: {columnas}\nDatos (limitados): {str(datos)[:2000]}\n\nExplica el resultado de forma clara, con cifras concretas y un análisis estadístico amigable."
    return chat(None, prompt, SYSTEM_BASE)

def responder_chat(client, pregunta):
    return chat(None, pregunta, SYSTEM_BASE)

def main():
    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
        schema = obtener_schema()
        try:
            tipo = decidir_tipo_pregunta(None, user_input)
            if "SQL" in tipo:
                sql = generar_sql(None, user_input, schema)
                try:
                    # Ejecutar con auto-reintento: si el SQL falla, Gemini lo corrige.
                    datos, columnas, sql = ejecutar_sql_con_reintentos(user_input, schema, sql)
                    respuesta = responder_con_datos(None, user_input, datos, columnas)
                    # Incluir tambien filas crudas (como lista de dicts) para consumo programatico
                    filas = [dict(zip(columnas, [str(v) if v is not None else None for v in fila])) for fila in datos[:50]]
                    print(json.dumps({
                        "tipo": "SQL",
                        "sql": sql,
                        "columnas": columnas,
                        "datos": filas,
                        "respuesta": respuesta
                    }, ensure_ascii=False))
                except Exception as e_db:
                    # Error honesto: NO inventar datos. Reportar el fallo real de la DB.
                    print(json.dumps({
                        "tipo": "SQL",
                        "sql": sql,
                        "error": f"Error ejecutando la consulta en la base de datos: {str(e_db)}",
                        "respuesta": None
                    }, ensure_ascii=False))
            else:
                respuesta = responder_chat(None, user_input)
                print(json.dumps({"tipo": "CHAT", "respuesta": respuesta}, ensure_ascii=False))
        except Exception as e:
            # Error honesto a nivel de flujo (API Gemini u otro). NO inventar datos.
            print(json.dumps({
                "tipo": "ERROR",
                "error": f"No se pudo procesar la consulta: {str(e)}",
                "respuesta": None
            }, ensure_ascii=False))
        return

    print("Lumina al habla (Motor: Gemini 3.5 Flash)")
    schema = obtener_schema()
    while True:
        user_input = input("Tu: ").strip()
        if user_input.lower() == "salir": break
        try:
            tipo = decidir_tipo_pregunta(None, user_input)
            if "SQL" in tipo:
                sql = generar_sql(None, user_input, schema)
                print("SQL generado:", sql)
                datos, columnas, sql = ejecutar_sql_con_reintentos(user_input, schema, sql)
                print("SQL ejecutado:", sql)
                print("Lumina:", responder_con_datos(None, user_input, datos, columnas))
            else:
                print("Lumina:", responder_chat(None, user_input))
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    main()