import sqlite3
import os

def actualizar_base_datos():
    db_name = 'porteria.db' 
    conexion = sqlite3.connect(db_name)
    cursor = conexion.cursor()
    
    # Añadimos los campos de auditoría de entrega
    nuevos_campos = [
        "ALTER TABLE recepciones ADD COLUMN receptor TEXT",
        "ALTER TABLE recepciones ADD COLUMN fecha_entrega DATETIME",
        "ALTER TABLE recepciones ADD COLUMN portero_entrega TEXT"
    ]
    
    for sql in nuevos_campos:
        try:
            cursor.execute(sql)
            print(f"✅ Ejecutado: {sql}")
        except sqlite3.OperationalError:
            print(f"ℹ️ El campo ya existía o hubo un error menor.")

    conexion.commit()
    conexion.close()
    print("🎉 Base de datos lista para trazabilidad total.")

if __name__ == '__main__':
    actualizar_base_datos()