import mysql.connector
import os
conn = mysql.connector.connect(
    host=os.getenv("DB_HOST", "127.0.0.1"), 
    user=os.getenv("DB_USER", "odemiro"), 
    password=os.getenv("DB_PASS", "odemiro_pass_2026"), 
    database=os.getenv("DB_NAME", "odemiro_db")
)
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM snies_matriculados")
print("SNIES rows:", cursor.fetchone()[0])
try:
    cursor.execute("SELECT COUNT(*) FROM desercion_academica")
    print("Desercion rows:", cursor.fetchone()[0])
except:
    print("Desercion table missing")
cursor.close()
conn.close()
