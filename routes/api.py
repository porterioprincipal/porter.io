from flask import Blueprint, jsonify, session
from db import get_db_context

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/unidades')
def obtener_unidades():
    with get_db_context() as conexion:
        res = [dict(r) for r in conexion.execute("SELECT id, nombre FROM unidades WHERE activa = 1 AND nit_conjunto = ?", (session['nit_conjunto'],)).fetchall()]
    return jsonify(res)

@api_bp.route('/api/subunidades/<int:unidad_id>')
def obtener_subunidades(unidad_id):
    with get_db_context() as conexion:
        res = [dict(r) for r in conexion.execute("SELECT id, nombre FROM subunidades WHERE unidad_id = ? AND activa = 1 AND nit_conjunto = ?", (unidad_id, session['nit_conjunto'])).fetchall()]
    return jsonify(res)