from flask import Blueprint, render_template, request, session, redirect, url_for, Response
from werkzeug.security import generate_password_hash
import csv
from io import StringIO
from db import get_db_context

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')
def admin_panel():
    if session.get('rol') != 'administrador': return redirect(url_for('visitas.index'))
    
    with get_db_context() as conexion:
        unidades_db = conexion.execute("SELECT * FROM unidades WHERE nit_conjunto = ?", (session['nit_conjunto'],)).fetchall()
        subunidades_db = conexion.execute("SELECT * FROM subunidades WHERE nit_conjunto = ?", (session['nit_conjunto'],)).fetchall()
        
        estructura = []
        for u in unidades_db:
            subs = [s for s in subunidades_db if s['unidad_id'] == u['id']]
            estructura.append({'id': u['id'], 'nombre': u['nombre'], 'activa': u['activa'], 'subunidades': subs})

        tipos_doc = conexion.execute("SELECT id, sigla, nombre FROM tipos_documento ORDER BY id ASC").fetchall()
        query_usrs = "SELECT u.*, t.sigla as tipo_sigla FROM usuarios u LEFT JOIN tipos_documento t ON u.tipo_identificacion = t.id WHERE u.nit_conjunto = ?"
        usrs = conexion.execute(query_usrs, (session['nit_conjunto'],)).fetchall()
    
    return render_template('admin.html', estructura=estructura, unidades=unidades_db, usuarios=usrs, tipos_doc=tipos_doc, usuario_actual=session['usuario'])

@admin_bp.route('/admin/crear_usuario', methods=['POST'])
def crear_usuario():
    if session.get('rol') != 'administrador': return redirect(url_for('visitas.index'))
    d = request.form
    h = generate_password_hash(d['password'])
    with get_db_context() as conexion:
        conexion.execute('INSERT INTO usuarios (nombres, apellidos, empresa, tipo_identificacion, numero_identificacion, username, password, rol, nit_conjunto) VALUES (?,?,?,?,?,?,?,?,?)', (d['nombres'], d['apellidos'], d['empresa'], d['tipo_identificacion'], d['numero_identificacion'], d['username'], h, d['rol'], session['nit_conjunto']))
        conexion.commit()
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/admin/descargar_historial', methods=['POST'])
def descargar_historial():
    if session.get('rol') != 'administrador': return redirect(url_for('visitas.index'))
    fecha_inicio, fecha_fin = request.form.get('fecha_inicio'), request.form.get('fecha_fin')
    if not fecha_inicio or not fecha_fin: return "Las fechas son requeridas", 400

    try:
        with get_db_context() as conexion:
            query = '''
                SELECT v.fecha_hora, t.sigla as tipo_doc, v.numero_documento, v.nombre_completo, 
                    v.apartamento, v.vehiculo, v.placa, v.acompanantes, v.observaciones, v.portero, v.estado, v.motivo_anulacion
                FROM visitas v LEFT JOIN tipos_documento t ON v.tipo_doc_id = t.id
                WHERE v.nit_conjunto = ? AND v.fecha_hora BETWEEN ? AND ? ORDER BY v.fecha_hora DESC
            '''
            registros = conexion.execute(query, (session['nit_conjunto'], f"{fecha_inicio} 00:00:00", f"{fecha_fin} 23:59:59")).fetchall()

        si = StringIO()
        cw = csv.writer(si, delimiter=';') 
        cw.writerow(['Fecha y Hora', 'Tipo Doc', 'Documento', 'Visitante', 'Destino', 'Vehiculo', 'Placa', 'Acompanantes', 'Observaciones', 'Portero', 'Estado', 'Motivo Anulacion'])
        
        for r in registros:
            cw.writerow([r['fecha_hora'], r['tipo_doc'], r['numero_documento'], r['nombre_completo'], r['apartamento'], "SI" if r['vehiculo'] == 1 else "NO", r['placa'] or '', r['acompanantes'], r['observaciones'] or '', r['portero'], r['estado'], r['motivo_anulacion'] or ''])

        return Response('\ufeff' + si.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename=Reporte_{fecha_inicio}_al_{fecha_fin}.csv"})
    except Exception as e: return f"Error: {e}", 500

@admin_bp.route('/admin/reset_password/<int:id>', methods=['POST'])
def reset_password(id):
    if session.get('rol') != 'administrador': return redirect(url_for('visitas.index'))
    h = generate_password_hash(request.form.get('nueva_password'))
    with get_db_context() as conexion:
        conexion.execute("UPDATE usuarios SET password = ? WHERE id = ? AND nit_conjunto = ?", (h, id, session['nit_conjunto']))
        conexion.commit()
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/admin/crear_unidad', methods=['POST'])
def crear_unidad():
    if session.get('rol') != 'administrador': return redirect(url_for('visitas.index'))
    with get_db_context() as conexion:
        conexion.execute("INSERT INTO unidades (nombre, activa, nit_conjunto) VALUES (?, 1, ?)", (request.form.get('nombre_unidad'), session['nit_conjunto']))
        conexion.commit()
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/admin/crear_subunidad', methods=['POST'])
def crear_subunidad():
    if session.get('rol') != 'administrador': return redirect(url_for('visitas.index'))
    with get_db_context() as conexion:
        conexion.execute("INSERT INTO subunidades (nombre, unidad_id, activa, nit_conjunto) VALUES (?, ?, 1, ?)", (request.form.get('nombre_subunidad'), request.form.get('unidad_id'), session['nit_conjunto']))
        conexion.commit()
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/admin/toggle_usuario/<int:id>', methods=['POST'])
def toggle_usuario(id):
    if session.get('rol') != 'administrador': return redirect(url_for('visitas.index'))
    with get_db_context() as conexion:
        st = 0 if conexion.execute("SELECT activo FROM usuarios WHERE id = ?", (id,)).fetchone()[0] == 1 else 1
        conexion.execute("UPDATE usuarios SET activo = ? WHERE id = ?", (st, id))
        conexion.commit()
    return redirect(url_for('admin.admin_panel'))