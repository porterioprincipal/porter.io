import sqlite3

def añadir_nit():
    try:
        conexion = sqlite3.connect("porteria.db")
        cursor = conexion.cursor()
        
        # El comando mágico para añadir una columna sin romper la tabla
        cursor.execute("ALTER TABLE control_pago ADD COLUMN nit TEXT")
        
        conexion.commit()
        print("✅ Columna 'nit' añadida con éxito a control_pago.")
    except sqlite3.OperationalError:
        print("⚠️ La columna 'nit' ya existe o hubo un error de acceso.")
    finally:
        conexion.close()

if __name__ == "__main__":
    añadir_nit()