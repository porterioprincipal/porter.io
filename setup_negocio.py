import sqlite3

def crear_tabla_suscripcion():
    conexion = sqlite3.connect("porteria.db")
    cursor = conexion.cursor()
    
    # Tabla para controlar el acceso del conjunto residencial
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS control_pago (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_cliente TEXT,
            fecha_vencimiento DATE,
            bloqueado INTEGER DEFAULT 0 -- 0: Activo, 1: Suspendido por falta de pago
        )
    ''')
    
    # Insertamos tu primer cliente (Prueba) con vencimiento en un mes
    cursor.execute('''
        INSERT INTO control_pago (nombre_cliente, fecha_vencimiento) 
        VALUES ('Conjunto Residencial El Sol', '2026-04-30')
    ''')
    
    conexion.commit()
    conexion.close()
    print("✅ Sistema de control de pagos configurado.")

if __name__ == "__main__":
    crear_tabla_suscripcion()