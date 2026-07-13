import urllib.request
import json
import mysql.connector
import os

# Configuracion de la base de datos de Lumina
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "user": os.getenv("DB_USER", "odemiro"),
    "password": os.getenv("DB_PASS", "odemiro_pass_2026"),
    "database": os.getenv("DB_NAME", "odemiro_db")
}

# API Endpoint de datos.gov.co (Desercion Academica)
API_URL = "https://www.datos.gov.co/resource/3iew-7wpx.json?$limit=50000"

def fetch_data():
    print(f"Descargando datos de {API_URL}...")
    req = urllib.request.Request(API_URL, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            print(f"Se descargaron {len(data)} registros.")
            return data
    except Exception as e:
        print("Error descargando datos:", e)
        return []

def update_database(data):
    if not data:
        return
    
    print("Conectando a la base de datos...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Crear la tabla si no existe
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS desercion_academica (
                id INT AUTO_INCREMENT PRIMARY KEY,
                periodo VARCHAR(255),
                nombre_facultad VARCHAR(255),
                nombre_programa VARCHAR(255),
                jornada VARCHAR(255),
                modalidad VARCHAR(255),
                nombre_sede VARCHAR(255),
                tipo_iden_est VARCHAR(50),
                fecha_nacimiento VARCHAR(255),
                genero VARCHAR(50),
                estrato VARCHAR(255),
                nombre_estado VARCHAR(255),
                origen_geografico VARCHAR(255),
                lugar_expedicion VARCHAR(255)
            )
        ''')
        
        # Vaciar la tabla para poner los datos nuevos (Opcional, pero util para no duplicar)
        cursor.execute('TRUNCATE TABLE desercion_academica')
        
        # Preparar la query de insercion
        insert_query = '''
            INSERT INTO desercion_academica (
                periodo, nombre_facultad, nombre_programa, jornada, modalidad,
                nombre_sede, tipo_iden_est, fecha_nacimiento, genero, estrato,
                nombre_estado, origen_geografico, lugar_expedicion
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''
        
        # Mapear los datos a tuplas
        records = []
        for row in data:
            records.append((
                row.get('periodo'), row.get('nombre_facultad'), row.get('nombre_programa'),
                row.get('jornada'), row.get('modalidad'), row.get('nombre_sede'),
                row.get('tipo_iden_est'), row.get('fecha_nacimiento'), row.get('genero'),
                row.get('estrato'), row.get('nombre_estado'), row.get('origen_geografico'),
                row.get('lugar_expedicion')
            ))
            
        print("Insertando datos...")
        cursor.executemany(insert_query, records)
        conn.commit()
        print(f"Exito: {cursor.rowcount} registros insertados en la tabla 'desercion_academica'.")
        
    except mysql.connector.Error as err:
        print("Error de MySQL:", err)
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    datos = fetch_data()
    update_database(datos)
