import mysql.connector
import csv
import os

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "user": os.getenv("DB_USER", "odemiro"),
    "password": os.getenv("DB_PASS", "odemiro_pass_2026"),
    "database": os.getenv("DB_NAME", "odemiro_db")
}

def export_table(table_name):
    print(f"Exportando {table_name}...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        limit = "LIMIT 10000" if table_name == "snies_matriculados" else ""
        cursor.execute(f"SELECT * FROM {table_name} {limit}")
        
        rows = cursor.fetchall()
        columns = [i[0] for i in cursor.description]
        
        # Guardar en la carpeta data del proyecto
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
        os.makedirs(base_dir, exist_ok=True)
        file_path = os.path.join(base_dir, f"{table_name}_muestra.csv")
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(rows)
            
        print(f"✅ Exportado a {file_path}")
        return file_path
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    export_table("desercion_academica")
    export_table("modelado_aptitudes")
