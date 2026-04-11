import os
import pytz
from datetime import datetime, timedelta

# Configuración Base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "porteria.db")
SECRET_KEY = 'super_secreta_y_segura_jose_saas_v2'

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