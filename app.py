from flask import Flask, request, session, redirect, url_for
from datetime import datetime
from flask_wtf.csrf import CSRFProtect
from config import SECRET_KEY, bogota_tz, obtener_turno_actual
from db import get_db_context

# Importamos los Blueprints
from routes.auth import auth_bp
from routes.superadmin import superadmin_bp
from routes.admin import admin_bp
from routes.visitas import visitas_bp
from routes.api import api_bp

app = Flask(__name__)
app.secret_key = SECRET_KEY

app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

# Configuración de Seguridad en Cookies de Sesión
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
# En desarrollo local (HTTP) va False, en producción con HTTPS cambiará a True via env
app.config['SESSION_COOKIE_SECURE'] = False

csrf = CSRFProtect(app)

# Registramos los módulos
app.register_blueprint(auth_bp)
app.register_blueprint(superadmin_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(visitas_bp)
app.register_blueprint(api_bp)

@app.before_request
def revision_global():
    rutas_libres = [
        'auth.login', 'auth.logout', 'static', 'superadmin.login_master', 
        'superadmin.superadmin', 'superadmin.agregar_conjunto', 'superadmin.actualizar_conjunto', 
        'superadmin.superadmin_crear_admin', 'superadmin.superadmin_reset_password'
    ]
    if request.endpoint in rutas_libres: return

    if 'usuario' not in session or 'nit_conjunto' not in session:
        return redirect(url_for('auth.login'))

    with get_db_context() as conexion:
        cliente = conexion.execute("SELECT fecha_vencimiento, bloqueado FROM control_pago WHERE nit = ?", (session['nit_conjunto'],)).fetchone()

    if not cliente: return redirect(url_for('auth.login', error="Conjunto no registrado."))
    
    hoy = datetime.now(bogota_tz).date()
    vencimiento = datetime.strptime(cliente['fecha_vencimiento'], '%Y-%m-%d').date()
    
    if cliente['bloqueado'] == 1 or hoy > vencimiento:
        session.clear()
        return redirect(url_for('auth.login', error="Servicio suspendido."))

    if session.get('turno_guardado') != obtener_turno_actual():
        session.clear()
        return redirect(url_for('auth.login', error="Turno finalizado."))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)