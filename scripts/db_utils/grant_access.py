import mysql.connector

DB_CONFIG = {
    "host": "localhost",
    "user": "odemiro",
    "password": "***",
    "database": "mysql"
}

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("CREATE USER IF NOT EXISTS 'odemiro'@'%' IDENTIFIED BY '***';")
    cursor.execute("GRANT ALL PRIVILEGES ON *.* TO 'odemiro'@'%';")
    cursor.execute("FLUSH PRIVILEGES;")
    print("Permisos concedidos correctamente para conexiones externas.")
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals() and conn.is_connected():
        cursor.close()
        conn.close()
