import sqlite3
import os

# Ruta a tu base de datos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'porteria.db')

def actualizar_db():
    conexion = sqlite3.connect(DB_PATH)
    try:
        # Agregamos la columna 'acompanantes' como un entero
        # Ponemos DEFAULT 0 para que los registros viejos no queden vacíos
        conexion.execute("ALTER TABLE visitas ADD COLUMN acompanantes INTEGER DEFAULT 0")
        conexion.commit()
        print("✅ Columna 'acompanantes' creada exitosamente.")
    except sqlite3.OperationalError:
        print("⚠️ La columna ya existe, no se realizaron cambios.")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conexion.close()

if __name__ == "__main__":
    actualizar_db()