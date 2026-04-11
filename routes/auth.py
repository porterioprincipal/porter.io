from flask import Blueprint, render_template, request, session, redirect, url_for
from werkzeug.security import check_password_hash
from db import get_db_connection
from config import obtener_turno_actual

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    error = request.args.get('error')
    if request.method == 'POST':
        u, p = request.form['usuario'], request.form['password']
        conexion = get_db_connection()
        
        query_user = '''
            SELECT u.*, t.sigla as tipo_sigla 
            FROM usuarios u 
            LEFT JOIN tipos_documento t ON u.tipo_identificacion = t.id 
            WHERE u.username = ? AND u.activo = 1
        '''
        user_db = conexion.execute(query_user, (u,)).fetchone()
        
        if user_db and check_password_hash(user_db['password'], p):
            nit = user_db['nit_conjunto']
            c_db = conexion.execute('SELECT nombre_cliente, nom_bloque, nom_unidad FROM control_pago WHERE nit = ?', (nit,)).fetchone()
            
            session.update({
                'usuario': u, 
                'rol': user_db['rol'], 
                'nit_conjunto': nit, 
                'nom_cliente': c_db['nombre_cliente'], 
                'nom_bloque': c_db['nom_bloque'], 
                'nom_unidad': c_db['nom_unidad'], 
                'turno_guardado': obtener_turno_actual(),
                'nombre_completo': f"{user_db['nombres']} {user_db['apellidos']}",
                'documento_sigla': user_db['tipo_sigla'],
                'numero_identificacion': user_db['numero_identificacion']
            })
            conexion.close()
            return redirect(url_for('visitas.index'))
            
        conexion.close()
        error = "Credenciales incorrectas."
        
    return render_template('login.html', error=error)

@auth_bp.route('/logout')
def logout():
    es_maestro = session.get('is_superadmin')
    session.clear()
    return redirect(url_for('superadmin.login_master' if es_maestro else 'auth.login'))