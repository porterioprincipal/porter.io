import sqlite3
import os
from werkzeug.security import generate_password_hash # ¡NUEVO IMPORT!

def inicializar_bd():
    if os.path.exists("porteria.db"):
        os.remove("porteria.db")

    conexion = sqlite3.connect("porteria.db")
    cursor = conexion.cursor()

    # 1. ACTUALIZADA: Tabla Usuarios con perfil completo
    cursor.execute('''
        CREATE TABLE usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombres TEXT NOT NULL,
            apellidos TEXT NOT NULL,
            empresa TEXT NOT NULL,
            tipo_identificacion TEXT NOT NULL,
            numero_identificacion TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            rol TEXT NOT NULL, 
            activo INTEGER DEFAULT 1
        )
    ''')

    # 2. Tabla Visitas
    cursor.execute('''
        CREATE TABLE visitas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cedula TEXT NOT NULL,
            nombre_completo TEXT,
            apartamento TEXT,
            portero TEXT,
            fecha_hora DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 3. Tabla Manzanas
    cursor.execute('''
        CREATE TABLE manzanas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            activa INTEGER DEFAULT 1
        )
    ''')

    # 4. Tabla Casas con Llave Foránea
    cursor.execute('''
        CREATE TABLE casas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manzana_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            activa INTEGER DEFAULT 1,
            FOREIGN KEY (manzana_id) REFERENCES manzanas(id)
        )
    ''')

    # --- INYECCIÓN DE DATOS ---
    
    # Usuarios por defecto actualizados con los nuevos campos
    usuarios_iniciales = [
        ("José", "Admin", "Administración", "Cédula de Ciudadanía", "1111111111", "admin", generate_password_hash("admin123"), "administrador"),
        ("Carlos", "Gómez", "Seguridad Omega", "Cédula de Ciudadanía", "2222222222", "portero_m1", generate_password_hash("1234"), "portero"),
        ("Luis", "Rojas", "Seguridad Omega", "Permiso de Protección Temporal", "3333333333", "portero_m2", generate_password_hash("5678"), "portero")
    ]
    for u in usuarios_iniciales:
        cursor.execute('''
            INSERT INTO usuarios 
            (nombres, apellidos, empresa, tipo_identificacion, numero_identificacion, username, password, rol) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', u)

    # Manzanas y Casas
    manzanas_validas = [1, 2, 3, 4, 5, 6, 10, 11, 12, 13, 14, 15, 16]
    medias_manzanas = [1, 6, 11, 16] 
    
    for m in manzanas_validas:
        cursor.execute('INSERT INTO manzanas (nombre) VALUES (?)', (f"Manzana {m}",))
        manzana_id = cursor.lastrowid 
        num_casas = 16 if m in medias_manzanas else 35
        for c in range(1, num_casas + 1):
            cursor.execute('INSERT INTO casas (manzana_id, nombre) VALUES (?, ?)', (manzana_id, f"Casa {c}"))

    conexion.commit()
    conexion.close()
    print("✅ BD Relacional lista: Tabla de usuarios actualizada con datos personales completos.")

if __name__ == "__main__":
    inicializar_bd()