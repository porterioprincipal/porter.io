import sqlite3

def actualizar_bd():
    conexion = sqlite3.connect("porteria.db")
    cursor = conexion.cursor()
    
    try:
        # Agregamos la columna estado (por defecto todos los actuales serán 'activo')
        cursor.execute("ALTER TABLE visitas ADD COLUMN estado TEXT DEFAULT 'activo'")
        # Agregamos la columna para guardar la justificación del administrador
        cursor.execute("ALTER TABLE visitas ADD COLUMN motivo_anulacion TEXT")
        
        conexion.commit()
        print("✅ Base de datos actualizada: Soporte para borrado lógico implementado.")
    except Exception as e:
        print(f"⚠️ Nota: {e} (Es posible que las columnas ya existan).")
    finally:
        conexion.close()

if __name__ == "__main__":
    actualizar_bd()