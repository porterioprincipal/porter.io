import sqlite3
from contextlib import contextmanager
from config import DB_PATH

def dict_factory(cursor, row):
    """
    Convierte las filas de la base de datos en diccionarios
    para acceder a los campos por nombre: fila['nombre']
    """
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

@contextmanager
def get_db_context():
    """
    Administrador de contexto para la conexión a SQLite.
    Asegura que la conexión siempre se cierre al finalizar o si hay error.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
    try:
        yield conn
    finally:
        conn.close()

# Mantenemos esta función para compatibilidad previa si se requiere
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
    return conn