from db import get_db_context

def aplicar_indices():
    indices = [
        # Búsquedas por conjunto y fecha en Visitas (Historial y reportes Excel)
        "CREATE INDEX IF NOT EXISTS idx_visitas_nit_fecha ON visitas (nit_conjunto, fecha_hora DESC);",
        
        # Búsquedas por apartamento en Visitas
        "CREATE INDEX IF NOT EXISTS idx_visitas_nit_apto ON visitas (nit_conjunto, apartamento);",
        
        # Búsquedas por conjunto y fecha en Recepción de Paquetes
        "CREATE INDEX IF NOT EXISTS idx_recepciones_nit_fecha ON recepciones (nit_conjunto, fecha_hora DESC);",
        
        # Búsquedas por apartamento en Paquetes (para el buscador en tiempo real de portería)
        "CREATE INDEX IF NOT EXISTS idx_recepciones_nit_apto ON recepciones (nit_conjunto, apartamento);",
        
        # Aceleración de logins y consultas multitenant de usuarios
        "CREATE INDEX IF NOT EXISTS idx_usuarios_nit_user ON usuarios (nit_conjunto, username);",
        
        # Búsquedas de estructura (Unidades y Subunidades)
        "CREATE INDEX IF NOT EXISTS idx_unidades_nit ON unidades (nit_conjunto);",
        "CREATE INDEX IF NOT EXISTS idx_subunidades_unidad ON subunidades (unidad_id, nit_conjunto);"
    ]

    with get_db_context() as conn:
        cursor = conn.cursor()
        print("⚡ Aplicando índices en la base de datos...")
        for query in indices:
            cursor.execute(query)
        conn.commit()
        print("✅ ¡Índices creados exitosamente!")

if __name__ == '__main__':
    aplicar_indices()