import os
import pytz
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Configuración Base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "porteria.db")
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-default-solo-para-local')

# Zona Horaria
bogota_tz = pytz.timezone('America/Bogota')

# Helpers Globales
def obtener_turno_actual():
    ahora = datetime.now(bogota_tz)
    if 6 <= ahora.hour < 18:
        return f"{ahora.strftime('%Y-%m-%d')}-DIA"
    else:
        fecha_turno = (ahora - timedelta(days=1)).strftime('%Y-%m-%d') if ahora.hour < 6 else ahora.strftime('%Y-%m-%d')
        return f"{fecha_turno}-NOCHE"