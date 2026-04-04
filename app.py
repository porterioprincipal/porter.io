from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime, timedelta
import sqlite3
import re
import os
import pytz
from werkzeug.security import generate_password_hash, check_password_hash

# --- CONFIGURACIÓN INICIAL ---
app = Flask(__name__)
app.secret_key = 'super_secreta_y_segura_jose_saas'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "porteria.db")
bogota_tz = pytz.timezone('America/Bogota')

def obtener_turno_actual():
    ahora = datetime.now(bogota_tz)
    if 6 <= ahora.hour < 18:
        return f"{ahora.strftime('%Y-%m-%d')}-DIA"
    else:
        fecha_turno = (ahora - timedelta(days=1)).strftime('%Y-%m-%d') if ahora.hour < 6 else ahora.strftime('%Y-%m-%d')
        return f"{fecha_turno}-NOCHE"

@app.before_request
def revision_global():
    rutas_libres = [
        'login', 'logout', 'static', 'login_master', 
        'superadmin', 'agregar_conjunto', 'actualizar_conjunto', 
        'superadmin_crear_admin', 'superadmin_reset_password'
    ]
    if request.endpoint in rutas_libres: return

    if 'usuario' not in session or 'nit_conjunto' not in session:
        return redirect(url_for('login'))

    conexion = sqlite3.connect(DB_PATH); conexion.row_factory = sqlite3.Row
    cliente = conexion.execute("SELECT fecha_vencimiento, bloqueado FROM control_pago WHERE nit = ?", (session['nit_conjunto'],)).fetchone()
    conexion.close()

    if not cliente: return redirect(url_for('login', error="Conjunto no registrado."))
    
    hoy = datetime.now(bogota_tz).date()
    vencimiento = datetime.strptime(cliente['fecha_vencimiento'], '%Y-%m-%d').date()
    
    if cliente['bloqueado'] == 1 or hoy > vencimiento:
        session.clear()
        return redirect(url_for('login', error="Servicio suspendido."))

    if session.get('turno_guardado') != obtener_turno_actual():
        session.clear()
        return redirect(url_for('login', error="Turno finalizado."))

# ==========================================
# RUTAS MAESTRAS (SUPERADMIN)
# ==========================================

@app.route('/login_master', methods=['GET', 'POST'])
def login_master():
    error = ""
    if request.method == 'POST':
        u, p = request.form.get('usuario'), request.form.get('password')
        conexion = sqlite3.connect(DB_PATH); conexion.row_factory = sqlite3.Row
        admin_db = conexion.execute("SELECT * FROM superadmins WHERE username = ?", (u,)).fetchone()
        conexion.close()
        if admin_db and check_password_hash(admin_db['password'], p):
            session['is_superadmin'] = True
            return redirect(url_for('superadmin'))
        error = "Credenciales maestras incorrectas."
    return f'''<body style="background:#2c3e50;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;"><div style="background:white;padding:40px;border-radius:8px;text-align:center;"><h2>🔒 Acceso SaaS</h2><p style="color:red;">{error}</p><form method="POST"><input type="text" name="usuario" placeholder="Usuario" required style="width:100%;padding:10px;margin-bottom:15px;"><br><input type="password" name="password" placeholder="Clave" required style="width:100%;padding:10px;margin-bottom:15px;"><br><button type="submit" style="background:#e74c3c;color:white;padding:10px;width:100%;cursor:pointer;border:none;">Entrar</button></form></div></body>'''

@app.route('/superadmin')
def superadmin():
    if not session.get('is_superadmin'): return redirect(url_for('login_master'))
    conexion = sqlite3.connect(DB_PATH); conexion.row_factory = sqlite3.Row
    conjuntos = conexion.execute("SELECT * FROM control_pago ORDER BY nombre_cliente ASC").fetchall()
    usuarios_globales = conexion.execute('''SELECT u.*, cp.nombre_cliente FROM usuarios u INNER JOIN control_pago cp ON u.nit_conjunto = cp.nit ORDER BY cp.nombre_cliente ASC, u.rol DESC''').fetchall()
    conexion.close()
    return render_template('superadmin.html', conjuntos=conjuntos, usuarios_globales=usuarios_globales)

@app.route('/superadmin/agregar', methods=['POST'])
def agregar_conjunto():
    if not session.get('is_superadmin'): return redirect(url_for('login_master'))
    d = request.form
    conexion = sqlite3.connect(DB_PATH)
    existe = conexion.execute("SELECT id, nombre_cliente FROM control_pago WHERE nit = ?", (d['nit'],)).fetchone()
    if existe:
        conexion.close()
        return f"❌ Error: El NIT {d['nit']} ya pertenece a {existe[1]}."
    conexion.execute("INSERT INTO control_pago (nit, nombre_cliente, fecha_vencimiento, bloqueado, nom_bloque, nom_unidad) VALUES (?,?,?,0,?,?)", (d['nit'], d['nombre'], d['fecha'], d['nom_bloque'], d['nom_unidad']))
    conexion.commit(); conexion.close()
    return redirect(url_for('superadmin'))

@app.route('/superadmin/actualizar/<int:id>', methods=['POST'])
def actualizar_conjunto(id):
    if not session.get('is_superadmin'): return redirect(url_for('login_master'))
    d = request.form
    conexion = sqlite3.connect(DB_PATH)
    conexion.execute("UPDATE control_pago SET nit=?, nombre_cliente=?, fecha_vencimiento=?, bloqueado=?, nom_bloque=?, nom_unidad=? WHERE id=?", (d['nit'], d['nombre'], d['fecha'], d['bloqueado'], d['nom_bloque'], d['nom_unidad'], id))
    nit_viejo = request.form.get('nit_viejo')
    if nit_viejo and nit_viejo != d['nit']:
        for t in ['usuarios', 'visitas', 'unidades', 'subunidades']: # CAMBIADO AQUÍ
            conexion.execute(f"UPDATE {t} SET nit_conjunto=? WHERE nit_conjunto=?", (d['nit'], nit_viejo))
    conexion.commit(); conexion.close()
    return redirect(url_for('superadmin'))

@app.route('/superadmin/reset_password/<int:id>', methods=['POST'])
def superadmin_reset_password(id):
    if not session.get('is_superadmin'): return redirect(url_for('login_master'))
    nueva = request.form.get('nueva_password')
    if nueva:
        h = generate_password_hash(nueva)
        conexion = sqlite3.connect(DB_PATH)
        conexion.execute("UPDATE usuarios SET password = ? WHERE id = ?", (h, id))
        conexion.commit(); conexion.close()
    return redirect(url_for('superadmin'))

@app.route('/superadmin/crear_admin', methods=['POST'])
def superadmin_crear_admin():
    if not session.get('is_superadmin'): return redirect(url_for('login_master'))
    d = request.form
    conexion = sqlite3.connect(DB_PATH)
    hash_p = generate_password_hash(d['password'])
    conexion.execute("INSERT INTO usuarios (nombres, apellidos, empresa, tipo_identificacion, numero_identificacion, username, password, rol, nit_conjunto) VALUES (?,?,'Admin','CC',?,?,?,'administrador',?)", (d['nombres'], d['apellidos'], d['cedula'], d['username'], hash_p, d['nit_conjunto']))
    conexion.commit(); conexion.close()
    return redirect(url_for('superadmin'))

# ==========================================
# RUTAS DE CLIENTES
# ==========================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = request.args.get('error')
    if request.method == 'POST':
        u, p = request.form['usuario'], request.form['password']
        conexion = sqlite3.connect(DB_PATH); conexion.row_factory = sqlite3.Row
        user_db = conexion.execute('SELECT * FROM usuarios WHERE username = ? AND activo = 1', (u,)).fetchone()
        if user_db and check_password_hash(user_db['password'], p):
            nit = user_db['nit_conjunto']
            c_db = conexion.execute('SELECT nom_bloque, nom_unidad FROM control_pago WHERE nit = ?', (nit,)).fetchone()
            session.update({'usuario': u, 'rol': user_db['rol'], 'nit_conjunto': nit, 'nom_bloque': c_db['nom_bloque'], 'nom_unidad': c_db['nom_unidad'], 'turno_guardado': obtener_turno_actual()})
            conexion.close(); return redirect(url_for('index'))
        error = "Credenciales incorrectas."
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    es_maestro = session.get('is_superadmin')
    session.clear()
    return redirect(url_for('login_master' if es_maestro else 'login'))

@app.route('/')
def index():
    return render_template('index.html', usuario_actual=session['usuario'], rol_actual=session['rol'])

@app.route('/registrar', methods=['POST'])
def registrar():
    datos = request.json
    trama, subunid = datos.get('trama', ''), datos.get('apartamento', '')
    vehiculo = datos.get('vehiculo', 0)
    placa = datos.get('placa', '').upper()
    acomp = datos.get('acompanantes')
    observaciones = datos.get('observaciones', '')
    try:
        if "PubDSK" in trama:
            t_u = trama.split("PubDSK")[-1].strip("_") 
            m_c = re.search(r'(\d+)', t_u)
            cedula = m_c.group(1).lstrip('0')
            m_n = re.search(r'([A-ZÑ\s]+?)(?=\d)', t_u[m_c.end():])
            nombre = " ".join(m_n.group(1).split()).strip() if m_n else "Error"
        else: 
            cedula, nombre = trama, "Manual"

        hora = datetime.now(bogota_tz).strftime('%Y-%m-%d %H:%M:%S')
        conexion = sqlite3.connect(DB_PATH)
        
        # INSERT CON OBSERVACIONES
        conexion.execute('''INSERT INTO visitas 
            (cedula, nombre_completo, apartamento, portero, fecha_hora, nit_conjunto, vehiculo, placa, acompanantes, observaciones) 
            VALUES (?,?,?,?,?,?,?,?,?,?)''', 
            (cedula, nombre, subunid, session['usuario'], hora, session['nit_conjunto'], vehiculo, placa, acomp, observaciones))
        
        conexion.commit()
        conexion.close()
        
        # ... (dentro de tu bloque try después del close)
        return jsonify({
    "mensaje": "ok",
    "cedula": cedula,
    "nombre": nombre,
    "apartamento": subunid,
    "vehiculo": vehiculo,
    "placa": placa,
    "acompanantes": acomp, # Enviamos el número real ingresado
    "observaciones": observaciones
})
    except Exception as e: 
        return jsonify({"error": str(e)}), 400

@app.route('/historial')
def historial():
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row 
    # EL CAMBIO: Ahora solo traemos los que tengan estado 'activo' o que el estado sea nulo (por los registros viejos)
    filas = conexion.execute("SELECT * FROM visitas WHERE nit_conjunto = ? AND (estado = 'activo' OR estado IS NULL) ORDER BY fecha_hora DESC", (session['nit_conjunto'],)).fetchall()
    conexion.close()
    return render_template('historial.html', registros=filas)

@app.route('/anular_visita/<int:id>', methods=['POST'])
def anular_visita(id):
    if session.get('rol') != 'administrador': 
        return redirect(url_for('historial'))
    
    # Recibimos el motivo desde el HTML
    motivo = request.form.get('motivo', 'Sin justificación')
    
    conexion = sqlite3.connect(DB_PATH)
    # BORRADO LÓGICO: Solo cambiamos el estado y guardamos el por qué
    conexion.execute("UPDATE visitas SET estado = 'anulado', motivo_anulacion = ? WHERE id = ? AND nit_conjunto = ?", (motivo, id, session['nit_conjunto']))
    conexion.commit()
    conexion.close()
    
    return redirect(url_for('historial'))

@app.route('/admin')
def admin_panel():
    if session.get('rol') != 'administrador': return redirect(url_for('index'))
    conexion = sqlite3.connect(DB_PATH); conexion.row_factory = sqlite3.Row
    unids = conexion.execute("SELECT * FROM unidades WHERE nit_conjunto = ?", (session['nit_conjunto'],)).fetchall() # CAMBIADO
    usrs = conexion.execute("SELECT * FROM usuarios WHERE nit_conjunto = ?", (session['nit_conjunto'],)).fetchall()
    conexion.close()
    return render_template('admin.html', unidades=unids, usuarios=usrs, usuario_actual=session['usuario'])

@app.route('/admin/crear_usuario', methods=['POST'])
def crear_usuario():
    if session.get('rol') != 'administrador': return redirect(url_for('index'))
    d = request.form
    conexion = sqlite3.connect(DB_PATH)
    h = generate_password_hash(d['password'])
    conexion.execute('INSERT INTO usuarios (nombres, apellidos, empresa, tipo_identificacion, numero_identificacion, username, password, rol, nit_conjunto) VALUES (?,?,?,?,?,?,?,?,?)', (d['nombres'], d['apellidos'], d['empresa'], d['tipo_identificacion'], d['numero_identificacion'], d['username'], h, d['rol'], session['nit_conjunto']))
    conexion.commit(); conexion.close()
    return redirect(url_for('admin_panel'))

@app.route('/admin/reset_password/<int:id>', methods=['POST'])
def reset_password(id):
    if session.get('rol') != 'administrador': return redirect(url_for('index'))
    n = request.form.get('nueva_password')
    h = generate_password_hash(n)
    conexion = sqlite3.connect(DB_PATH)
    conexion.execute("UPDATE usuarios SET password = ? WHERE id = ? AND nit_conjunto = ?", (h, id, session['nit_conjunto']))
    conexion.commit(); conexion.close()
    return redirect(url_for('admin_panel'))

@app.route('/admin/crear_unidad', methods=['POST']) # CAMBIADO
def crear_unidad():
    if session.get('rol') != 'administrador': return redirect(url_for('index'))
    n = request.form.get('nombre_unidad')
    conexion = sqlite3.connect(DB_PATH)
    conexion.execute("INSERT INTO unidades (nombre, activa, nit_conjunto) VALUES (?, 1, ?)", (n, session['nit_conjunto']))
    conexion.commit(); conexion.close()
    return redirect(url_for('admin_panel'))

@app.route('/admin/crear_subunidad', methods=['POST']) # CAMBIADO
def crear_subunidad():
    if session.get('rol') != 'administrador': return redirect(url_for('index'))
    u_id = request.form.get('unidad_id')
    n = request.form.get('nombre_subunidad')
    conexion = sqlite3.connect(DB_PATH)
    conexion.execute("INSERT INTO subunidades (nombre, unidad_id, activa, nit_conjunto) VALUES (?, ?, 1, ?)", (n, u_id, session['nit_conjunto']))
    conexion.commit(); conexion.close()
    return redirect(url_for('admin_panel'))

@app.route('/admin/toggle_usuario/<int:id>', methods=['POST'])
def toggle_usuario(id):
    if session.get('rol') != 'administrador': return redirect(url_for('index'))
    conexion = sqlite3.connect(DB_PATH)
    st = 0 if conexion.execute("SELECT activo FROM usuarios WHERE id = ?", (id,)).fetchone()[0] == 1 else 1
    conexion.execute("UPDATE usuarios SET activo = ? WHERE id = ?", (st, id))
    conexion.commit(); conexion.close()
    return redirect(url_for('admin_panel'))

# --- APIs PARA DROPDOWNS ---
@app.route('/api/unidades') # CAMBIADO
def obtener_unidades():
    conexion = sqlite3.connect(DB_PATH); conexion.row_factory = sqlite3.Row
    res = [dict(r) for r in conexion.execute("SELECT id, nombre FROM unidades WHERE activa = 1 AND nit_conjunto = ?", (session['nit_conjunto'],)).fetchall()]
    conexion.close(); return jsonify(res)

@app.route('/api/subunidades/<int:unidad_id>') # CAMBIADO
def obtener_subunidades(unidad_id):
    conexion = sqlite3.connect(DB_PATH); conexion.row_factory = sqlite3.Row
    res = [dict(r) for r in conexion.execute("SELECT id, nombre FROM subunidades WHERE unidad_id = ? AND activa = 1 AND nit_conjunto = ?", (unidad_id, session['nit_conjunto'])).fetchall()]
    conexion.close(); return jsonify(res)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)