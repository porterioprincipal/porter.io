from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime
import re
from db import get_db_connection
from config import bogota_tz

visitas_bp = Blueprint('visitas', __name__)

@visitas_bp.route('/')
def index():
    conexion = get_db_connection()
    tipos_doc = conexion.execute("SELECT id, sigla, nombre FROM tipos_documento ORDER BY id ASC").fetchall()
    conexion.close()
    return render_template('index.html', usuario_actual=session['usuario'], rol_actual=session['rol'], tipos_doc=tipos_doc)

@visitas_bp.route('/registrar', methods=['POST'])
def registrar():
    if 'usuario' not in session:
        return jsonify({'error': 'No hay sesión activa'}), 401

    datos = request.json
    subunid = datos.get('apartamento', '')
    vehiculo = datos.get('vehiculo', 0)
    placa = datos.get('placa', '').upper()
    acomp = datos.get('acompanantes', 0)
    observaciones = datos.get('observaciones', '')
    es_manual = datos.get('es_manual', False)

    try:
        if es_manual:
            numero_doc = datos.get('documento_manual', '').strip()
            nombre = datos.get('nombre_manual', '').strip()
            tipo_doc_id = datos.get('tipo_doc_id', 1)
            if not numero_doc or not nombre: return jsonify({'error': 'Faltan datos'}), 400
        else:
            trama = datos.get('trama', '')
            match_nom = re.search(r'([A-ZÑ\s]{12,})', trama) 
            
            if match_nom:
                nombre_crudo = match_nom.group(1).strip()
                nombre = re.sub(r'\s+', ' ', nombre_crudo) 
                
                punto_donde_empieza = match_nom.start()
                texto_antes = trama[:punto_donde_empieza]
                
                match_doc = re.search(r'(\d{8,10})$', texto_antes.strip())
                if match_doc:
                    numero_doc = match_doc.group(1).lstrip("0")
                else:
                    match_doc_alt = re.search(r'(\d+)\s*$', texto_antes.strip())
                    numero_doc = match_doc_alt.group(1).lstrip("0") if match_doc_alt else "000"
            else:
                match_fallback = re.search(r'(\d{8,10})', trama)
                numero_doc = match_fallback.group(1).lstrip("0") if match_fallback else "000"
                nombre = "VISITANTE"

            tipo_doc_id = 1 

        conexion = get_db_connection()
        hora = datetime.now(bogota_tz).strftime('%Y-%m-%d %H:%M:%S')
        conexion.execute('''INSERT INTO visitas 
            (tipo_doc_id, numero_documento, nombre_completo, apartamento, portero, fecha_hora, nit_conjunto, vehiculo, placa, acompanantes, observaciones, estado) 
            VALUES (?,?,?,?,?,?,?,?,?,?,?,'activo')''', 
            (tipo_doc_id, numero_doc, nombre, subunid, session['usuario'], hora, session['nit_conjunto'], vehiculo, placa, acomp, observaciones))
        conexion.commit()
        conexion.close()
        
        return jsonify({"mensaje": "ok", "numero_documento": numero_doc, "nombre": nombre, "apartamento": subunid, "vehiculo": vehiculo, "placa": placa, "acompanantes": acomp, "observaciones": observaciones})
    except Exception as e: 
        return jsonify({"error": str(e)}), 400

@visitas_bp.route('/historial')
def historial():
    conexion = get_db_connection()
    query = """
        SELECT v.*, t.sigla as tipo_sigla
        FROM visitas v LEFT JOIN tipos_documento t ON v.tipo_doc_id = t.id
        WHERE v.nit_conjunto = ? AND (v.estado = 'activo' OR v.estado IS NULL) 
        ORDER BY v.fecha_hora DESC
    """
    filas = conexion.execute(query, (session['nit_conjunto'],)).fetchall()
    conexion.close()
    return render_template('historial.html', registros=filas)

@visitas_bp.route('/anular_visita/<int:id>', methods=['POST'])
def anular_visita(id):
    if session.get('rol') != 'administrador': return redirect(url_for('visitas.historial'))
    motivo = request.form.get('motivo', 'Sin justificación')
    conexion = get_db_connection()
    conexion.execute("UPDATE visitas SET estado = 'anulado', motivo_anulacion = ? WHERE id = ? AND nit_conjunto = ?", (motivo, id, session['nit_conjunto']))
    conexion.commit()
    conexion.close()
    return redirect(url_for('visitas.historial'))