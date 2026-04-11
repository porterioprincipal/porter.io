import sqlite3
from config import DB_PATH

def get_db_connection():
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    return conexion