import openai
import mysql.connector
import sys
import json
import os

# ============================================================
# Lumina — Agente unificado Lumina + Lumina
# Rama educativa y comercial del ODEM, Universidad EAN.
# Antes separados, ahora un solo agente con doble capacidad:
#   - Análisis de mercado y negocios (Lumina)
#   - Orientación educativa SNIES (Lumina)
# ============================================================

BASES_SISTEMA = {'information_schema', 'mysql', 'performance_schema', 'sys'}

API_KEY = os.getenv("NVIDIA_API_KEY", "TU_NVIDIA_API_KEY")

def conectar_db():
    # Tolerancia a fallos: timeout de conexión para evitar cuelgues indefinidos
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        user=os.getenv("DB_USER", "odemiro"),
        password=os.getenv("DB_PASS", "odemiro_pass_2026"),
        database=os.getenv("DB_NAME", "odemiro_db"),
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
    conexion = conectar_db()
    cursor = conexion.cursor()

    cursor.execute("SHOW DATABASES")
    todas_las_bases = [row[0] for row in cursor.fetchall()]
    bases_usuario = [db for db in todas_las_bases if db.lower() not in BASES_SISTEMA]

    schema_text = "Bases de datos disponibles:\n\n"
    for base in bases_usuario:
        cursor.execute(f"""
            SELECT table_name, column_name, column_type
            FROM information_schema.columns
            WHERE table_schema = '{base}'
            ORDER BY table_name, ordinal_position
        """)
        tablas = {}
        for tabla, columna, tipo in cursor.fetchall():
            if tabla not in tablas:
                tablas[tabla] = []
            tablas[tabla].append(f"{columna} ({tipo})")
        if tablas:
            schema_text += f"--- Base de datos: {base} ---\n"
            for tabla, columnas in tablas.items():
                schema_text += f"  {tabla}({', '.join(columnas)})\n"
            schema_text += "\n"

    cursor.close()
    conexion.close()
    return schema_text

historial = []

SYSTEM_LUMINA = (
    "Eres Lumina, agente unificado del ODEM (Observatorio de Mercadeo, Universidad EAN). "
    "Integras las capacidades de Lumina (análisis de mercado, negocios y marketing) "
    "y de Lumina (orientación educativa e innovación social). "
    "\n\n"
    "CAPACIDADES:\n"
    "1. MERCADEO Y NEGOCIOS: Analiza tendencias, segmentos, competencia y datos comerciales del ODEM.\n"
    "2. ORIENTACIÓN EDUCATIVA: Consulta el SNIES (snies_matriculados) para recomendar programas "
    "académicos según perfil del usuario (aptitudes, estrato, municipio, intereses). "
    "Cruza con modelado_aptitudes para recomendaciones personalizadas.\n"
    "\n"
    "REGLAS SQL:\n"
    "- Usa siempre el formato completo `base_de_datos.tabla` (ej: lumina_db.snies_matriculados).\n"
    "- El municipio de Bogotá en la BD es exactamente: 'BOGOTÁ, D.C.' (con coma y punto).\n"
    "- Para búsquedas de municipio usa LIKE '%BOGOTÁ%' para mayor flexibilidad.\n"
    "\n"
    "Respondes de forma clara, profesional y orientada al impacto. "
    "En modo integración (llamado con argumentos), devuelves JSON estructurado."
)

def chat(client, prompt_usuario):
    # Ensure system prompt is the first message for OpenAI standard
    messages_to_send = [{"role": "system", "content": SYSTEM_LUMINA}] + historial
    messages_to_send.append({"role": "user", "content": prompt_usuario})
    
    response = client.chat.completions.create(
        model="nvidia/nemotron-3-ultra-550b-a55b",
        max_tokens=2048,
        messages=messages_to_send
    )
    historial.append({"role": "user", "content": prompt_usuario})
    respuesta = response.choices[0].message.content
    historial.append({"role": "assistant", "content": respuesta})
    return respuesta

def decidir_tipo_pregunta(client, pregunta):
    prompt = (
        f"Decide si la siguiente pregunta requiere consultar una base de datos (SQL) "
        f"o es solo conversación/análisis. Responde ÚNICAMENTE con: SQL o CHAT.\n\nPregunta: {pregunta}"
    )
    response = client.chat.completions.create(
        model="nvidia/nemotron-3-ultra-550b-a55b",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip().upper()

def generar_sql(client, pregunta, schema):
    prompt = (
        f"Genera una consulta SQL válida para MySQL basada en el siguiente esquema.\n"
        f"IMPORTANTE: Usa el formato completo `base_de_datos.tabla`. "
        f"Para Bogotá usa: municipio_de_oferta_del_programa LIKE '%BOGOTÁ%'\n\n"
        f"{schema}\n\nPregunta: {pregunta}\n\n"
        f"Devuelve SOLO la consulta SQL, sin bloques de código ni explicaciones."
    )
    response = client.chat.completions.create(
        model="nvidia/nemotron-3-ultra-550b-a55b",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    sql = response.choices[0].message.content.strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()
    return sql

def responder_con_datos(client, pregunta, datos, columnas):
    prompt = (
        f"El usuario preguntó: {pregunta}\n\n"
        f"Columnas: {columnas}\nDatos: {datos[:50]}\n\n"
        f"Explica el resultado de forma clara, útil y amigable. "
        f"Si son datos educativos, da recomendaciones. Si son datos de mercado, da análisis."
    )
    response = client.chat.completions.create(
        model="nvidia/nemotron-3-ultra-550b-a55b",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def responder_chat(client, pregunta):
    return chat(client, pregunta)

def main():
    client = openai.OpenAI(api_key=API_KEY, base_url="https://integrate.api.nvidia.com/v1")

    # Modo no-interactivo: recibe pregunta como argumento (integración con Viernes/MINTIC)
    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
        schema = obtener_schema()
        try:
            tipo = decidir_tipo_pregunta(client, user_input)
            if tipo == "SQL":
                sql = generar_sql(client, user_input, schema)
                datos, columnas = consultar_db(sql)
                respuesta = responder_con_datos(client, user_input, datos, columnas)
                print(json.dumps({
                    "agente": "Lumina",
                    "tipo": "SQL",
                    "sql": sql,
                    "filas": len(datos),
                    "respuesta": respuesta
                }, ensure_ascii=False))
            else:
                respuesta = responder_chat(client, user_input)
                print(json.dumps({
                    "agente": "Lumina",
                    "tipo": "CHAT",
                    "respuesta": respuesta
                }, ensure_ascii=False))
        except Exception as e:
            print(json.dumps({"agente": "Lumina", "error": str(e)}, ensure_ascii=False))
        return

    # Modo interactivo (terminal)
    print("✨ Lumina al habla — ODEM, Universidad EAN")
    print("Cargando esquema de bases de datos...")
    schema = obtener_schema()
    print("Schema cargado. Lista.\n")

    while True:
        user_input = input("Tú: ").strip()
        if user_input.lower() in ("salir", "exit"):
            break
        try:
            tipo = decidir_tipo_pregunta(client, user_input)
            if tipo == "SQL":
                sql = generar_sql(client, user_input, schema)
                print(f"SQL: {sql}")
                datos, columnas = consultar_db(sql)
                respuesta = responder_con_datos(client, user_input, datos, columnas)
            else:
                respuesta = responder_chat(client, user_input)
            print(f"Lumina: {respuesta}\n")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
