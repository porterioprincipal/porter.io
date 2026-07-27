import sqlite3

def agregar_campo_paquete():
    db_name = 'porteria.db' # Verifica que este sea tu nombre real
    conexion = sqlite3.connect(db_name)
    cursor = conexion.cursor()
    
    try:
        cursor.execute("ALTER TABLE recepciones ADD COLUMN detalle_paquete TEXT")
        print("✅ Columna 'detalle_paquete' añadida con éxito.")
    except sqlite3.OperationalError:
        print("ℹ️ La columna ya existe o hubo un error.")
        
    conexion.commit()
    conexion.close()

if __name__ == '__main__':
    agregar_campo_paquete()