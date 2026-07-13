import mysql.connector
import os

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "user": os.getenv("DB_USER", "odemiro"),
    "password": os.getenv("DB_PASS", "odemiro_pass_2026"),
    "database": os.getenv("DB_NAME", "odemiro_db")
}

def clean_database():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("Iniciando limpieza de datos en la base de datos 'odemiro_db'...")
        
        # 1. Limpieza de tabla: desercion_academica
        print("\n--- Limpiando tabla: desercion_academica ---")
        
        # Trim y mayusculas para estandarizar
        columnas_texto = [
            'periodo', 'nombre_facultad', 'nombre_programa', 'jornada', 
            'modalidad', 'nombre_sede', 'tipo_iden_est', 'genero', 
            'estrato', 'nombre_estado', 'origen_geografico', 'lugar_expedicion'
        ]
        
        for col in columnas_texto:
            cursor.execute(f"UPDATE desercion_academica SET {col} = UPPER(TRIM({col})) WHERE {col} IS NOT NULL")
        print(f"✅ Textos estandarizados (Mayúsculas y sin espacios extra) para {len(columnas_texto)} columnas.")
        
        # Manejo de nulos / vacios
        for col in columnas_texto:
            cursor.execute(f"UPDATE desercion_academica SET {col} = 'SIN INFORMACION' WHERE {col} = '' OR {col} IS NULL")
        print("✅ Valores nulos o vacíos reemplazados por 'SIN INFORMACION'.")

        # Eliminar duplicados exactos (basado en todas las columnas excepto id)
        query_duplicates = """
            DELETE t1 FROM desercion_academica t1
            INNER JOIN desercion_academica t2 
            WHERE 
                t1.id > t2.id AND 
                t1.periodo = t2.periodo AND 
                t1.nombre_programa = t2.nombre_programa AND 
                t1.tipo_iden_est = t2.tipo_iden_est AND
                t1.fecha_nacimiento = t2.fecha_nacimiento
        """
        cursor.execute(query_duplicates)
        duplicados_eliminados = cursor.rowcount
        print(f"✅ {duplicados_eliminados} registros duplicados eliminados en desercion_academica.")
        
        conn.commit()
        print("\n¡Limpieza de datos completada con éxito!")
        
    except mysql.connector.Error as err:
        print("Error de MySQL:", err)
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    clean_database()
