from flask import Blueprint, render_template, request, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import generate_csrf
from datetime import datetime
from db import get_db_context
from config import bogota_tz

superadmin_bp = Blueprint('superadmin', __name__)

@superadmin_bp.route('/login_master', methods=['GET', 'POST'])
def login_master():
    error = ""
    if request.method == 'POST':
        u, p = request.form.get('usuario'), request.form.get('password')
        with get_db_context() as conexion:
            query = "SELECT s.*, t.sigla as tipo_sigla FROM superadmins s LEFT JOIN tipos_documento t ON s.tipo_doc_id = t.id WHERE s.username = ?"
            admin_db = conexion.execute(query, (u,)).fetchone()
        
        if admin_db and check_password_hash(admin_db['password'], p):
            session['is_superadmin'] = True
            admin_dict = dict(admin_db)
            session['admin_nombre'] = admin_dict.get('nombre_completo') or 'Admin' 
            session['admin_doc'] = f"{admin_dict.get('tipo_sigla') or 'CC'} {admin_dict.get('numero_documento') or ''}".strip()
            return redirect(url_for('superadmin.superadmin'))
        error = "Credenciales maestras incorrectas."
        
    csrf_token = generate_csrf()
    return f'''<body style="background:#2c3e50;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;"><div style="background:white;padding:40px;border-radius:8px;text-align:center;"><h2>🔒 Acceso SaaS</h2><p style="color:red;">{error}</p><form method="POST"><input type="hidden" name="csrf_token" value="{csrf_token}"/><input type="text" name="usuario" placeholder="Usuario" required style="width:100%;padding:10px;margin-bottom:15px;"><br><input type="password" name="password" placeholder="Clave" required style="width:100%;padding:10px;margin-bottom:15px;"><br><button type="submit" style="background:#e74c3c;color:white;padding:10px;width:100%;cursor:pointer;border:none;">Entrar</button></form></div></body>'''

@superadmin_bp.route('/superadmin')
def superadmin():
    if not session.get('is_superadmin'): return redirect(url_for('superadmin.login_master'))
    with get_db_context() as conexion:
        conjuntos = conexion.execute("SELECT * FROM control_pago ORDER BY nombre_cliente ASC").fetchall()
        query_usuarios = "SELECT u.*, cp.nombre_cliente, t.sigla as tipo_sigla FROM usuarios u INNER JOIN control_pago cp ON u.nit_conjunto = cp.nit LEFT JOIN tipos_documento t ON u.tipo_identificacion = t.id ORDER BY cp.nombre_cliente ASC, u.rol DESC"
        usuarios_globales = conexion.execute(query_usuarios).fetchall()
    
    hoy_str = datetime.now(bogota_tz).strftime('%Y-%m-%d')
    return render_template('superadmin.html', conjuntos=conjuntos, usuarios_globales=usuarios_globales, hoy=hoy_str)

@superadmin_bp.route('/superadmin/agregar', methods=['POST'])
def agregar_conjunto():
    if not session.get('is_superadmin'): return redirect(url_for('superadmin.login_master'))
    d = request.form
    with get_db_context() as conexion:
        existe = conexion.execute("SELECT id, nombre_cliente FROM control_pago WHERE nit = ?", (d['nit'],)).fetchone()
        if existe:
            return f"❌ Error: El NIT ya pertenece a {existe[1]}."
        conexion.execute("INSERT INTO control_pago (nit, nombre_cliente, fecha_vencimiento, bloqueado, nom_bloque, nom_unidad) VALUES (?,?,?,0,?,?)", (d['nit'], d['nombre'], d['fecha'], d['nom_bloque'], d['nom_unidad']))
        conexion.commit()
    return redirect(url_for('superadmin.superadmin'))

@superadmin_bp.route('/superadmin/actualizar/<int:id>', methods=['POST'])
def actualizar_conjunto(id):
    if not session.get('is_superadmin'): return redirect(url_for('superadmin.login_master'))
    d = request.form
    with get_db_context() as conexion:
        conexion.execute("UPDATE control_pago SET nit=?, nombre_cliente=?, fecha_vencimiento=?, bloqueado=?, nom_bloque=?, nom_unidad=? WHERE id=?", (d['nit'], d['nombre'], d['fecha'], d['bloqueado'], d['nom_bloque'], d['nom_unidad'], id))
        nit_viejo = request.form.get('nit_viejo')
        if nit_viejo and nit_viejo != d['nit']:
            for t in ['usuarios', 'visitas', 'unidades', 'subunidades']:
                conexion.execute(f"UPDATE {t} SET nit_conjunto=? WHERE nit_conjunto=?", (d['nit'], nit_viejo))
        conexion.commit()
    return redirect(url_for('superadmin.superadmin'))

@superadmin_bp.route('/superadmin/reset_password/<int:id>', methods=['POST'])
def superadmin_reset_password(id):
    if not session.get('is_superadmin'): return redirect(url_for('superadmin.login_master'))
    nueva = request.form.get('nueva_password')
    if nueva:
        h = generate_password_hash(nueva)
        with get_db_context() as conexion:
            conexion.execute("UPDATE usuarios SET password = ? WHERE id = ?", (h, id))
            conexion.commit()
    return redirect(url_for('superadmin.superadmin'))

@superadmin_bp.route('/superadmin/crear_admin', methods=['POST'])
def superadmin_crear_admin():
    if not session.get('is_superadmin'): return redirect(url_for('superadmin.login_master'))
    d = request.form
    hash_p = generate_password_hash(d['password'])
    with get_db_context() as conexion:
        conexion.execute("INSERT INTO usuarios (nombres, apellidos, empresa, tipo_identificacion, numero_identificacion, username, password, rol, nit_conjunto) VALUES (?,?,'Admin',1,?,?,?,'administrador',?)", (d['nombres'], d['apellidos'], d['cedula'], d['username'], hash_p, d['nit_conjunto']))
        conexion.commit()
    return redirect(url_for('superadmin.superadmin'))