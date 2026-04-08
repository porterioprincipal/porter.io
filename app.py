from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime, timedelta
import sqlite3
import re
import os
import pytz
from werkzeug.security import generate_password_hash, check_password_hash
import csv
from io import StringIO
from flask import Response # Asegúrate de que Response esté importado de flask junto con render_template, request, etc.

# --- CONFIGURACIÓN INICIAL ---
app = Flask(__name__)
app.secret_key = 'super_secreta_y_segura_jose_saas_v2'

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
        conexion = sqlite3.connect(DB_PATH)
        conexion.row_factory = sqlite3.Row
        
        query = '''
            SELECT s.*, t.sigla as tipo_sigla 
            FROM superadmins s 
            LEFT JOIN tipos_documento t ON s.tipo_doc_id = t.id 
            WHERE s.username = ?
        '''
        admin_db = conexion.execute(query, (u,)).fetchone()
        conexion.close()
        
        if admin_db and check_password_hash(admin_db['password'], p):
            session['is_superadmin'] = True
            
            # EL FIX: Convertimos la fila de SQLite a un diccionario de Python
            admin_dict = dict(admin_db)
            
            # Ahora usamos el diccionario que sí soporta .get()
            session['admin_nombre'] = admin_dict.get('nombre_completo') or 'Admin' 
            session['admin_doc'] = f"{admin_dict.get('tipo_sigla') or 'CC'} {admin_dict.get('numero_documento') or ''}".strip()
            
            return redirect(url_for('superadmin'))
        
        error = "Credenciales maestras incorrectas."
        
    return f'''<body style="background:#2c3e50;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;"><div style="background:white;padding:40px;border-radius:8px;text-align:center;"><h2>🔒 Acceso SaaS</h2><p style="color:red;">{error}</p><form method="POST"><input type="text" name="usuario" placeholder="Usuario" required style="width:100%;padding:10px;margin-bottom:15px;"><br><input type="password" name="password" placeholder="Clave" required style="width:100%;padding:10px;margin-bottom:15px;"><br><button type="submit" style="background:#e74c3c;color:white;padding:10px;width:100%;cursor:pointer;border:none;">Entrar</button></form></div></body>'''

@app.route('/superadmin')
def superadmin():
    if not session.get('is_superadmin'): return redirect(url_for('login_master'))
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    
    conjuntos = conexion.execute("SELECT * FROM control_pago ORDER BY nombre_cliente ASC").fetchall()
    
    query_usuarios = '''
        SELECT u.*, cp.nombre_cliente, t.sigla as tipo_sigla 
        FROM usuarios u 
        INNER JOIN control_pago cp ON u.nit_conjunto = cp.nit 
        LEFT JOIN tipos_documento t ON u.tipo_identificacion = t.id
        ORDER BY cp.nombre_cliente ASC, u.rol DESC
    '''
    usuarios_globales = conexion.execute(query_usuarios).fetchall()
    
    conexion.close()
    
    # NUEVO: Calculamos la fecha de hoy en formato texto (YYYY-MM-DD) para el HTML
    hoy_str = datetime.now(bogota_tz).strftime('%Y-%m-%d')
    
    # La pasamos a la plantilla
    return render_template('superadmin.html', conjuntos=conjuntos, usuarios_globales=usuarios_globales, hoy=hoy_str)

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
        for t in ['usuarios', 'visitas', 'unidades', 'subunidades']:
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
    # Se inyecta 1 (CC) por defecto para los nuevos admins de conjunto
    conexion.execute("INSERT INTO usuarios (nombres, apellidos, empresa, tipo_identificacion, numero_identificacion, username, password, rol, nit_conjunto) VALUES (?,?,'Admin',1,?,?,?,'administrador',?)", (d['nombres'], d['apellidos'], d['cedula'], d['username'], hash_p, d['nit_conjunto']))
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
        conexion = sqlite3.connect(DB_PATH)
        conexion.row_factory = sqlite3.Row
        
        query_user = '''
            SELECT u.*, t.sigla as tipo_sigla 
            FROM usuarios u 
            LEFT JOIN tipos_documento t ON u.tipo_identificacion = t.id 
            WHERE u.username = ? AND u.activo = 1
        '''
        user_db = conexion.execute(query_user, (u,)).fetchone()
        
        if user_db and check_password_hash(user_db['password'], p):
            nit = user_db['nit_conjunto']
            
            # FIX 1: Le agregamos 'nombre_cliente' a la consulta SQL
            c_db = conexion.execute('SELECT nombre_cliente, nom_bloque, nom_unidad FROM control_pago WHERE nit = ?', (nit,)).fetchone()
            
            # FIX 2: Metemos ese dato en la sesión para que el HTML lo pueda leer
            session.update({
                'usuario': u, 
                'rol': user_db['rol'], 
                'nit_conjunto': nit, 
                'nom_cliente': c_db['nombre_cliente'], # AQUÍ ESTÁ LA MAGIA
                'nom_bloque': c_db['nom_bloque'], 
                'nom_unidad': c_db['nom_unidad'], 
                'turno_guardado': obtener_turno_actual(),
                'nombre_completo': f"{user_db['nombres']} {user_db['apellidos']}",
                'documento_sigla': user_db['tipo_sigla'],
                'numero_identificacion': user_db['numero_identificacion']
            })
            conexion.close()
            return redirect(url_for('index'))
            
        conexion.close()
        error = "Credenciales incorrectas."
        
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    es_maestro = session.get('is_superadmin')
    session.clear()
    return redirect(url_for('login_master' if es_maestro else 'login'))

@app.route('/')
def index():
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    # Mandamos los tipos de documento al index para el formulario manual
    tipos_doc = conexion.execute("SELECT id, sigla, nombre FROM tipos_documento ORDER BY id ASC").fetchall()
    conexion.close()
    return render_template('index.html', usuario_actual=session['usuario'], rol_actual=session['rol'], tipos_doc=tipos_doc)

@app.route('/registrar', methods=['POST'])
def registrar():
    if 'usuario' not in session:
        return jsonify({'error': 'No hay sesión activa'}), 401

    datos = request.json
    subunid = datos.get('apartamento', '')
    vehiculo = datos.get('vehiculo', 0)
    placa = datos.get('placa', '').upper()
    acomp = datos.get('acompanantes', 0)
    observaciones = datos.get('observaciones', '')
    
    # ¿Cómo ingresó el visitante?
    es_manual = datos.get('es_manual', False)

    try:
        if es_manual:
            # ✍️ LÓGICA MANUAL
            numero_doc = datos.get('documento_manual', '').strip()
            nombre = datos.get('nombre_manual', '').strip()
            tipo_doc_id = datos.get('tipo_doc_id', 1)
            
            if not numero_doc or not nombre:
                return jsonify({'error': 'Faltan datos en el ingreso manual'}), 400
        else:
            # 🔫 LÓGICA ESCÁNER
            trama = datos.get('trama', '')
            if "PubDSK" in trama:
                t_u = trama.split("PubDSK")[-1].strip("_") 
                m_c = re.search(r'(\d+)', t_u)
                numero_doc = m_c.group(1).lstrip('0') if m_c else ""
                m_n = re.search(r'([A-ZÑ\s]+?)(?=\d)', t_u[m_c.end():]) if m_c else None
                nombre = " ".join(m_n.group(1).split()).strip() if m_n else "VISITANTE"
            else:
                numero_doc = ''.join(filter(str.isdigit, trama))
                nombre = "VISITANTE"
            
            tipo_doc_id = 1 

        conexion = sqlite3.connect(DB_PATH)
        hora = datetime.now(bogota_tz).strftime('%Y-%m-%d %H:%M:%S')
        
        # 💾 INSERTAMOS DIRECTO SIN VALIDAR SI YA ESTÁ ADENTRO
        conexion.execute('''INSERT INTO visitas 
            (tipo_doc_id, numero_documento, nombre_completo, apartamento, portero, fecha_hora, nit_conjunto, vehiculo, placa, acompanantes, observaciones, estado) 
            VALUES (?,?,?,?,?,?,?,?,?,?,?,'activo')''', 
            (tipo_doc_id, numero_doc, nombre, subunid, session['usuario'], hora, session['nit_conjunto'], vehiculo, placa, acomp, observaciones))
        
        conexion.commit()
        conexion.close()
        
        return jsonify({
            "mensaje": "ok",
            "numero_documento": numero_doc,
            "nombre": nombre,
            "apartamento": subunid,
            "vehiculo": vehiculo,
            "placa": placa,
            "acompanantes": acomp,
            "observaciones": observaciones
        })
    except Exception as e: 
        return jsonify({"error": str(e)}), 400

@app.route('/historial')
def historial():
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row 
    # JOIN para mostrar "CE", "PPT", "CC" en la tabla HTML
    query = """
        SELECT v.*, t.sigla as tipo_sigla
        FROM visitas v
        LEFT JOIN tipos_documento t ON v.tipo_doc_id = t.id
        WHERE v.nit_conjunto = ? AND (v.estado = 'activo' OR v.estado IS NULL) 
        ORDER BY v.fecha_hora DESC
    """
    filas = conexion.execute(query, (session['nit_conjunto'],)).fetchall()
    conexion.close()
    return render_template('historial.html', registros=filas)

@app.route('/anular_visita/<int:id>', methods=['POST'])
def anular_visita(id):
    if session.get('rol') != 'administrador': 
        return redirect(url_for('historial'))
    motivo = request.form.get('motivo', 'Sin justificación')
    conexion = sqlite3.connect(DB_PATH)
    conexion.execute("UPDATE visitas SET estado = 'anulado', motivo_anulacion = ? WHERE id = ? AND nit_conjunto = ?", (motivo, id, session['nit_conjunto']))
    conexion.commit()
    conexion.close()
    return redirect(url_for('historial'))

@app.route('/admin')
def admin_panel():
    if session.get('rol') != 'administrador': return redirect(url_for('index'))
    conexion = sqlite3.connect(DB_PATH); conexion.row_factory = sqlite3.Row
    
    # 1. Buscamos todas las unidades y subunidades del conjunto
    unidades_db = conexion.execute("SELECT * FROM unidades WHERE nit_conjunto = ?", (session['nit_conjunto'],)).fetchall()
    subunidades_db = conexion.execute("SELECT * FROM subunidades WHERE nit_conjunto = ?", (session['nit_conjunto'],)).fetchall()
    
    # 2. Armamos la estructura jerárquica (Unidad -> [Subunidades])
    estructura = []
    for u in unidades_db:
        # Filtramos las subunidades que pertenecen a esta unidad específica
        subs = [s for s in subunidades_db if s['unidad_id'] == u['id']]
        estructura.append({
            'id': u['id'],
            'nombre': u['nombre'],
            'activa': u['activa'],
            'subunidades': subs
        })

    # Mandamos los tipos de documento al admin.html para el select de "Crear Usuario"
    tipos_doc = conexion.execute("SELECT id, sigla, nombre FROM tipos_documento ORDER BY id ASC").fetchall()
    
    # JOIN para mostrar "CE", "PPT" en la lista de porteros
    query_usrs = """
        SELECT u.*, t.sigla as tipo_sigla
        FROM usuarios u
        LEFT JOIN tipos_documento t ON u.tipo_identificacion = t.id
        WHERE u.nit_conjunto = ?
    """
    usrs = conexion.execute(query_usrs, (session['nit_conjunto'],)).fetchall()
    conexion.close()
    
    # IMPORTANTE: Pasamos 'estructura' y también 'unidades_db' (este último para el select del formulario)
    return render_template('admin.html', estructura=estructura, unidades=unidades_db, usuarios=usrs, tipos_doc=tipos_doc, usuario_actual=session['usuario'])

@app.route('/admin/crear_usuario', methods=['POST'])
def crear_usuario():
    if session.get('rol') != 'administrador': return redirect(url_for('index'))
    d = request.form
    conexion = sqlite3.connect(DB_PATH)
    h = generate_password_hash(d['password'])
    # Aquí asumimos que d['tipo_identificacion'] vendrá como el número (ID) desde el <select> en HTML
    conexion.execute('INSERT INTO usuarios (nombres, apellidos, empresa, tipo_identificacion, numero_identificacion, username, password, rol, nit_conjunto) VALUES (?,?,?,?,?,?,?,?,?)', (d['nombres'], d['apellidos'], d['empresa'], d['tipo_identificacion'], d['numero_identificacion'], d['username'], h, d['rol'], session['nit_conjunto']))
    conexion.commit(); conexion.close()
    return redirect(url_for('admin_panel'))

@app.route('/admin/descargar_historial', methods=['POST'])
def descargar_historial():
    # 1. Seguridad: Solo administradores
    if session.get('rol') != 'administrador':
        return redirect(url_for('index'))

    # 2. Recibir las fechas del formulario
    fecha_inicio = request.form.get('fecha_inicio')
    fecha_fin = request.form.get('fecha_fin')

    if not fecha_inicio or not fecha_fin:
        return "Las fechas son requeridas", 400

    # 💡 TRUCO PRO: Añadimos las horas para que abarque los días completos
    # Si piden del 10 al 12, buscamos desde el 10 a las 00:00:00 hasta el 12 a las 23:59:59
    inicio_full = f"{fecha_inicio} 00:00:00"
    fin_full = f"{fecha_fin} 23:59:59"

    try:
        conexion = sqlite3.connect(DB_PATH)
        conexion.row_factory = sqlite3.Row
        
        # 3. Buscamos los registros en ese rango de fechas
        query = '''
            SELECT v.fecha_hora, t.sigla as tipo_doc, v.numero_documento, v.nombre_completo, 
                   v.apartamento, v.vehiculo, v.placa, v.acompanantes, v.observaciones, 
                   v.portero, v.estado, v.motivo_anulacion
            FROM visitas v
            LEFT JOIN tipos_documento t ON v.tipo_doc_id = t.id
            WHERE v.nit_conjunto = ? AND v.fecha_hora BETWEEN ? AND ?
            ORDER BY v.fecha_hora DESC
        '''
        registros = conexion.execute(query, (session['nit_conjunto'], inicio_full, fin_full)).fetchall()
        conexion.close()

        # 4. Fabricar el archivo Excel (CSV) en la memoria RAM
        si = StringIO()
        # Usamos punto y coma (;) porque el Excel en español lo lee mejor que la coma (,)
        cw = csv.writer(si, delimiter=';') 
        
        # Escribimos la fila de los títulos (Cabecera)
        cw.writerow(['Fecha y Hora', 'Tipo Doc', 'Documento', 'Visitante', 'Destino', 'Vehiculo', 'Placa', 'Acompanantes', 'Observaciones', 'Portero', 'Estado', 'Motivo Anulacion'])
        
        # Escribimos los datos de cada visita
        for r in registros:
            vehiculo_str = "SI" if r['vehiculo'] == 1 else "NO"
            cw.writerow([
                r['fecha_hora'], r['tipo_doc'], r['numero_documento'], r['nombre_completo'],
                r['apartamento'], vehiculo_str, r['placa'] or '', r['acompanantes'],
                r['observaciones'] or '', r['portero'], r['estado'], r['motivo_anulacion'] or ''
            ])

        # 5. Empaquetar y enviar el archivo al navegador para que inicie la descarga
        output = si.getvalue()
        
        # Añadir BOM para que Excel lea los tildes y las ñ correctamente
        output_con_utf8_bom = '\ufeff' + output 

        return Response(
            output_con_utf8_bom,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename=Reporte_Visitas_{fecha_inicio}_al_{fecha_fin}.csv"}
        )

    except Exception as e:
        return f"Error generando reporte: {e}", 500

@app.route('/admin/reset_password/<int:id>', methods=['POST'])
def reset_password(id):
    if session.get('rol') != 'administrador': return redirect(url_for('index'))
    n = request.form.get('nueva_password')
    h = generate_password_hash(n)
    conexion = sqlite3.connect(DB_PATH)
    conexion.execute("UPDATE usuarios SET password = ? WHERE id = ? AND nit_conjunto = ?", (h, id, session['nit_conjunto']))
    conexion.commit(); conexion.close()
    return redirect(url_for('admin_panel'))

@app.route('/admin/crear_unidad', methods=['POST'])
def crear_unidad():
    if session.get('rol') != 'administrador': return redirect(url_for('index'))
    n = request.form.get('nombre_unidad')
    conexion = sqlite3.connect(DB_PATH)
    conexion.execute("INSERT INTO unidades (nombre, activa, nit_conjunto) VALUES (?, 1, ?)", (n, session['nit_conjunto']))
    conexion.commit(); conexion.close()
    return redirect(url_for('admin_panel'))

@app.route('/admin/crear_subunidad', methods=['POST'])
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
@app.route('/api/unidades')
def obtener_unidades():
    conexion = sqlite3.connect(DB_PATH); conexion.row_factory = sqlite3.Row
    res = [dict(r) for r in conexion.execute("SELECT id, nombre FROM unidades WHERE activa = 1 AND nit_conjunto = ?", (session['nit_conjunto'],)).fetchall()]
    conexion.close(); return jsonify(res)

@app.route('/api/subunidades/<int:unidad_id>')
def obtener_subunidades(unidad_id):
    conexion = sqlite3.connect(DB_PATH); conexion.row_factory = sqlite3.Row
    res = [dict(r) for r in conexion.execute("SELECT id, nombre FROM subunidades WHERE unidad_id = ? AND activa = 1 AND nit_conjunto = ?", (unidad_id, session['nit_conjunto'])).fetchall()]
    conexion.close(); return jsonify(res)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)