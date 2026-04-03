import sqlite3
from werkzeug.security import generate_password_hash

def configurar_superadmin():
    conexion = sqlite3.connect("porteria.db")
    cursor = conexion.cursor()
    
    # 1. Creamos la tabla exclusiva para los dueños de la plataforma
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS superadmins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')
    
    # 2. Verificamos si tu usuario ya existe para no duplicarlo
    cursor.execute("SELECT * FROM superadmins WHERE username = 'jose_ceo'")
    if not cursor.fetchone():
        # 3. Encriptamos tu clave maestra de forma irreversible
        hash_pass = generate_password_hash("SaaS_Bogota_2026*")
        cursor.execute("INSERT INTO superadmins (username, password) VALUES (?, ?)", ('jose_ceo', hash_pass))
        print("✅ ¡Éxito! Bóveda creada. Superadmin 'jose_ceo' registrado con clave encriptada.")
    else:
        print("⚠️ El superadmin ya existe en la base de datos. No se hicieron cambios.")
        
    conexion.commit()
    conexion.close()

if __name__ == "__main__":
    configurar_superadmin()