import os
import base64
import uuid
import re
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from db import get_db_context
from config import bogota_tz

visitas_bp = Blueprint('visitas', __name__)

UPLOAD_FOLDER = os.path.join('static', 'uploads', 'paquetes')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@visitas_bp.route('/')
def index():
    with get_db_context() as conexion:
        tipos_doc = conexion.execute("SELECT id, sigla, nombre FROM tipos_documento ORDER BY id ASC").fetchall()
    return render_template('index.html', usuario_actual=session['usuario'], rol_actual=session['rol'], tipos_doc=tipos_doc)

@visitas_bp.route('/registrar', methods=['POST'])
def registrar():
    if 'usuario' not in session: return jsonify({'error': 'No hay sesión activa'}), 401
    datos = request.json
    tipo_visita = datos.get('tipo_visita', 'Social')
    try:
        if datos.get('es_manual'):
            numero_doc = datos.get('documento_manual', '').strip()
            nombre = datos.get('nombre_manual', '').strip()
            tipo_doc_id = datos.get('tipo_doc_id', 1)
        else:
            trama = datos.get('trama', '')
            
            # 1. Extraer el Nombre
            match_nom = re.search(r'([A-ZÑ\s]{12,})', trama)
            nombre = re.sub(r'\s+', ' ', match_nom.group(1).strip()) if match_nom else "VISITANTE"
            
            # 2. Extraer la Cédula (Lógica oficial PDF417 Colombia)
            match_doc = re.search(r'(\d+)(?=[A-ZÑ]{5,})', trama)
            
            if match_doc:
                bloque_numeros = match_doc.group(1)
                numero_doc = bloque_numeros[-10:].lstrip('0')
            else:
                solo_numeros = "".join(re.findall(r'\d+', trama))
                numero_doc = solo_numeros.lstrip('0')[:10] if solo_numeros else "000"
                
            tipo_doc_id = 1
        
        hora = datetime.now(bogota_tz).strftime('%Y-%m-%d %H:%M:%S')
        with get_db_context() as conexion:
            conexion.execute('''INSERT INTO visitas 
                (tipo_doc_id, numero_documento, nombre_completo, apartamento, portero, fecha_hora, nit_conjunto, vehiculo, placa, acompanantes, observaciones, estado, tipo_visita) 
                VALUES (?,?,?,?,?,?,?,?,?,?,?,'activo',?)''', 
                (tipo_doc_id, numero_doc, nombre, datos.get('apartamento'), session['usuario'], hora, session['nit_conjunto'], datos.get('vehiculo'), datos.get('placa'), datos.get('acompanantes'), datos.get('observaciones'), tipo_visita))
            conexion.commit()
        
        return jsonify({
            "mensaje": "ok", 
            "nombre": nombre, 
            "apartamento": datos.get('apartamento'),
            "vehiculo": datos.get('vehiculo', 0),
            "placa": datos.get('placa', '')
        })
        
    except Exception as e: return jsonify({"error": str(e)}), 400

@visitas_bp.route('/registrar_paquete', methods=['POST'])
def registrar_paquete():
    if 'usuario' not in session: return jsonify({'error': 'No autorizado'}), 401
    
    d = request.json
    foto_base64 = d.get('foto', '')
    detalle_paq = d.get('detalle', '')
    nombre_foto = ""
    
    if foto_base64:
        nombre_foto = f"pkg_{uuid.uuid4().hex}.jpg"
        with open(os.path.join(UPLOAD_FOLDER, nombre_foto), "wb") as fh:
            fh.write(base64.b64decode(foto_base64.split(',')[1] if ',' in foto_base64 else foto_base64))
    
    hora = datetime.now(bogota_tz).strftime('%Y-%m-%d %H:%M:%S')
    
    with get_db_context() as conexion:
        conexion.execute('''INSERT INTO recepciones 
            (fecha_hora, nit_conjunto, portero, apartamento, empresa_envio, repartidor, detalle_paquete, foto_path, estado) 
            VALUES (?,?,?,?,?,?,?,?,'En Portería')''', 
            (hora, session['nit_conjunto'], session['usuario'], d['apartamento'], d['empresa'], d['repartidor'], detalle_paq, nombre_foto))
        conexion.commit()
    
    return jsonify({
            "mensaje": "ok", 
            "empresa": d.get('empresa', ''), 
            "apartamento": d.get('apartamento', '')
        })

@visitas_bp.route('/entregar_paquete/<int:id>', methods=['POST'])
def entregar_paquete(id):
    if 'usuario' not in session: return redirect(url_for('auth.login'))
    
    receptor = request.form.get('quien_reclama', 'Residente').upper()
    fecha_hoy = datetime.now(bogota_tz).strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        with get_db_context() as conexion:
            conexion.execute('''
                UPDATE recepciones 
                SET estado = 'Entregado', 
                    receptor = ?, 
                    fecha_entrega = ?, 
                    portero_entrega = ? 
                WHERE id = ? AND nit_conjunto = ?
            ''', (receptor, fecha_hoy, session['usuario'], id, session['nit_conjunto']))
            conexion.commit()
        return redirect(url_for('visitas.historial'))
    except Exception as e:
        return f"Error: {str(e)}", 400

@visitas_bp.route('/historial')
def historial():
    if 'usuario' not in session: return redirect(url_for('auth.login'))
    
    with get_db_context() as conexion:
        visitas = conexion.execute('''
            SELECT v.*, t.sigla as tipo_sigla 
            FROM visitas v 
            LEFT JOIN tipos_documento t ON v.tipo_doc_id = t.id 
            WHERE v.nit_conjunto = ? 
            ORDER BY v.fecha_hora DESC
        ''', (session['nit_conjunto'],)).fetchall()
        
        paquetes = conexion.execute('''
            SELECT * FROM recepciones 
            WHERE nit_conjunto = ? 
            ORDER BY fecha_hora DESC
        ''', (session['nit_conjunto'],)).fetchall()
    
    return render_template('historial.html', registros_visitas=visitas, registros_paquetes=paquetes)