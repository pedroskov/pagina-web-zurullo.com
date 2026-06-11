from flask import Flask, render_template, send_file, abort, request, jsonify
import psutil
import os
import sympy
import cv2
import threading
from flask import Response
import time
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_login import current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, emit


app = Flask(__name__)

socketio = SocketIO(app)


@app.template_filter('format_date')
def format_date(timestamp):
    import datetime
    return datetime.datetime.fromtimestamp(timestamp).strftime('%d/%m/%Y %H:%M')

# --- Base de datos ---
app.config['SECRET_KEY'] = 'PedroServerZulo2026RaspBerry#Pi4ModelB'# Esto en Github ni de coña
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////home/pedro/zulo.db'# Aqui poner donde quieres que se guarden las contraseñas y usuarios
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    es_admin = db.Column(db.Boolean, default=False)

class Metrica(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.Integer, nullable=False)
    temp = db.Column(db.Float)
    cpu = db.Column(db.Float)
    ram = db.Column(db.Float)

class Archivo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    autor = db.Column(db.String(100), nullable=False)
    nombre_fichero = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(10), nullable=False)  # 'txt', 'csv', 'py'
    timestamp = db.Column(db.Integer, nullable=False)

def recolectar_metricas():
    with app.app_context():
        db.create_all()
    while True:
        time.sleep(60)
        try:
            with app.app_context():
                stats = get_stats()
                m = Metrica(
                    timestamp=int(time.time()),
                    temp=stats['temp'] if stats['temp'] != 'N/A' else None,
                    cpu=stats['cpu'],
                    ram=stats['ram']
                )
                db.session.add(m)
                db.session.commit()
        except Exception as e:
            print(f'Error guardando métrica: {e}')

hilo_metricas = threading.Thread(target=recolectar_metricas, daemon=True)
hilo_metricas.start()


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

def get_stats():
    """Recoge estadísticas del sistema"""
    # Temperatura CPU
    try:
        with open('/sys/class/thermal/thermal_zone0/temp') as f:
            temp = round(int(f.read()) / 1000, 1)
    except:
        temp = 'N/A'

    return {
        'temp': temp,
        'cpu': psutil.cpu_percent(interval=0.5),
        'ram': psutil.virtual_memory().percent,
        'ram_total': round(psutil.virtual_memory().total / 1024**3, 1),  # GB
        'disco': psutil.disk_usage('/').percent,
        'disco_total': round(psutil.disk_usage('/').total / 1024**3, 1)  # GB
    }

UPLOADS_PATH = '/home/pedro/Desktop/proyectos/zulo/uploads'
os.makedirs(UPLOADS_PATH, exist_ok=True)

# --- Rutas ---

@app.route('/')
def index():
    stats = get_stats()
    return render_template('index.html', stats=stats)

@app.route('/metricas')
def metricas():
    horas = int(request.args.get('horas', 1))
    desde = int(time.time()) - horas * 3600
    datos = Metrica.query.filter(Metrica.timestamp >= desde).order_by(Metrica.timestamp).all()
    return jsonify([{
        'timestamp': m.timestamp,
        'temp': m.temp,
        'cpu': m.cpu,
        'ram': m.ram
    } for m in datos])

@app.route('/datos')
def datos():
    archivos = Archivo.query.order_by(Archivo.timestamp.desc()).all()
    return render_template('datos.html', archivos=archivos)

@app.route('/datos/subir', methods=['POST'])
def datos_subir():
    titulo  = request.form.get('titulo', '').strip()
    autor   = request.form.get('autor', '').strip()
    fichero = request.files.get('fichero')

    if not titulo or not autor or not fichero:
        return jsonify({'error': 'Faltan campos.'}), 400

    ext = fichero.filename.rsplit('.', 1)[-1].lower()
    if ext not in ('txt', 'csv', 'py'):
        return jsonify({'error': 'Formato no permitido. Solo txt, csv y py.'}), 400

    nombre_seguro = f"{int(time.time())}_{fichero.filename.replace(' ', '_')}"
    fichero.save(os.path.join(UPLOADS_PATH, nombre_seguro))

    db.session.add(Archivo(
        titulo=titulo, autor=autor,
        nombre_fichero=nombre_seguro, tipo=ext,
        timestamp=int(time.time())
    ))
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/datos/crear_csv', methods=['POST'])
def datos_crear_csv():
    data    = request.get_json(force=True)
    titulo  = data.get('titulo', '').strip()
    autor   = data.get('autor', '').strip()
    filas   = data.get('filas', [])

    if not titulo or not autor or not filas:
        return jsonify({'error': 'Faltan datos.'}), 400

    import csv, io
    buf = io.StringIO()
    writer = csv.writer(buf)
    for fila in filas:
        writer.writerow(fila)
    contenido = buf.getvalue()

    nombre_seguro = f"{int(time.time())}_{titulo.replace(' ', '_')}.csv"
    with open(os.path.join(UPLOADS_PATH, nombre_seguro), 'w', encoding='utf-8') as f:
        f.write(contenido)

    db.session.add(Archivo(
        titulo=titulo, autor=autor,
        nombre_fichero=nombre_seguro, tipo='csv',
        timestamp=int(time.time())
    ))
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/datos/descargar/<int:archivo_id>')
def datos_descargar(archivo_id):
    archivo = Archivo.query.get_or_404(archivo_id)
    return send_file(
        os.path.join(UPLOADS_PATH, archivo.nombre_fichero),
        as_attachment=True,
        download_name=archivo.nombre_fichero.split('_', 1)[-1]
    )

@app.route('/datos/eliminar/<int:archivo_id>', methods=['POST'])
@login_required
def datos_eliminar(archivo_id):
    if not current_user.es_admin:
        abort(403)
    archivo = Archivo.query.get_or_404(archivo_id)
    ruta = os.path.join(UPLOADS_PATH, archivo.nombre_fichero)
    if os.path.exists(ruta):
        os.remove(ruta)
    db.session.delete(archivo)
    db.session.commit()
    return redirect(url_for('datos'))

@app.route('/notas')
def notas():
    return render_template('notas.html')

@app.route('/calculadoras')
def calculadoras():
    return render_template('calculadoras.html')

@app.route('/calculadoras/propagar', methods=['POST'])
def propagar_errores():
    """
    Recibe JSON:
        {
            "funcion": "x**2 * sin(y)",
            "variables": [
                {"nombre": "x", "valor": "3.0", "incert": true},
                {"nombre": "y", "valor": null,  "incert": false}
            ]
        }

    Devuelve JSON:
        {
            "derivadas": [
                {"var": "x", "latex": "\\frac{\\partial f}{\\partial x} = ..."},
                ...
            ],
            "formula_latex": "\\sigma_f = \\sqrt{...}"
        }
    """
    import sympy as sp
    from sympy.parsing.sympy_parser import (
        parse_expr, standard_transformations, implicit_multiplication_application
    )
    from flask import request, jsonify

    data = request.get_json(force=True)
    funcion_str = data.get('funcion', '').strip()
    variables   = data.get('variables', [])

    if not funcion_str or not variables:
        return jsonify({'error': 'Faltan datos.'}), 400

    try:
        # Construir namespace de símbolos
        simbolos = {v['nombre']: sp.Symbol(v['nombre']) for v in variables}

        transformations = standard_transformations + (implicit_multiplication_application,)
        f = parse_expr(funcion_str, local_dict=simbolos, transformations=transformations)

        # Variables con incertidumbre
        vars_con_incert = [v for v in variables if v['incert']]

        if not vars_con_incert:
            return jsonify({'error': 'Ninguna variable tiene incertidumbre (σ).'}), 400

        derivadas_info = []
        terminos_cuadraticos = []

        for v in vars_con_incert:
            sym   = simbolos[v['nombre']]
            sigma = sp.Symbol(f'sigma_{v["nombre"]}')

            deriv = sp.diff(f, sym)
            deriv_simplif = sp.simplify(deriv)

            # LaTeX de la derivada
            lhs = sp.latex(sp.Symbol(f'partial_f_partial_{v["nombre"]}'))
            latex_deriv = (
                r'\frac{\partial f}{\partial ' + sp.latex(sym) + r'} = '
                + sp.latex(deriv_simplif)
            )
            derivadas_info.append({'var': v['nombre'], 'latex': latex_deriv})

            # Término para la fórmula cuadrática
            terminos_cuadraticos.append((deriv_simplif * sigma) ** 2)

        # Fórmula de propagación
        suma = sp.Add(*terminos_cuadraticos)
        formula = sp.sqrt(sp.simplify(suma))
        formula_latex = r'\sigma_f = ' + sp.latex(formula)
        
        # Evaluación numérica (si hay valores y sigmas)
        valor_numerico_latex = None
        try:
            subs = {}
            for v in variables:
                if v.get('valor'):
                    subs[simbolos[v['nombre']]] = float(v['valor'])
            
            sigmas_subs = {}
            for v in vars_con_incert:
                if v.get('sigma'):
                    sigmas_subs[sp.Symbol(f'sigma_{v["nombre"]}')] = float(v['sigma'])
            
            if subs or sigmas_subs:
                formula_num = formula.subs({**subs, **sigmas_subs})
                formula_num = sp.simplify(formula_num)
                # Si es completamente numérico, evalúa a float
                if formula_num.is_number:
                    valor_float = float(formula_num.evalf(4))
                    valor_numerico_latex = r'\sigma_f = ' + f'{valor_float:.4g}'
                else:
                    # Parcialmente sustituido, sigue siendo simbólico
                    valor_numerico_latex = r'\sigma_f = ' + sp.latex(formula_num)
        except Exception:
            pass  # Si falla la evaluación numérica, simplemente no se muestra
        
        return jsonify({
            'derivadas':            derivadas_info,
            'formula_latex':        formula_latex,
            'valor_numerico_latex': valor_numerico_latex
        })

    except Exception as e:
        return jsonify({'error': f'Error al procesar la función: {str(e)}'}), 400


FISICA_PATH = '/home/pedro/Desktop/FISICA-USC'

@app.route('/fisica')
@app.route('/fisica/<path:subpath>')
def fisica(subpath=''):
    ruta_actual = os.path.join(FISICA_PATH, subpath)

    # Seguridad: evitar que alguien navegue fuera de la carpeta
    if not os.path.abspath(ruta_actual).startswith(os.path.abspath(FISICA_PATH)):
        abort(403)

    if not os.path.exists(ruta_actual):
        abort(404)

    # Si es un directorio → mostrar su contenido
    if os.path.isdir(ruta_actual):
        entradas = os.listdir(ruta_actual)

        carpetas = sorted([e for e in entradas if os.path.isdir(os.path.join(ruta_actual, e))])
        archivos = sorted([e for e in entradas if os.path.isfile(os.path.join(ruta_actual, e))])

        # Construir "migas de pan": Inicio > 1º Curso > Mecánica
        partes = subpath.split('/') if subpath else []
        migas = []
        for i, parte in enumerate(partes):
            migas.append({
                'nombre': parte,
                'url': '/fisica/' + '/'.join(partes[:i+1])
            })

        return render_template('fisica.html',
            carpetas=carpetas,
            archivos=archivos,
            subpath=subpath,
            migas=migas
        )

    # Si es un archivo → servirlo directamente
    return send_file(ruta_actual)


# --- Cámara ---
camara_activa = True
camara_lock = threading.Lock()

def generar_frames():
    cap = cv2.VideoCapture(0)
    while True:
        with camara_lock:
            if not camara_activa:
                break
        ret, frame = cap.read()
        if not ret:
            break
        _, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    cap.release()

@app.route('/video_feed')
def video_feed():
    if not camara_activa:
        return "Cámara desconectada", 503
    return Response(generar_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/camara')
def camara():
    return render_template('camara.html', activa=camara_activa)


# --- Login / Logout ---
from flask import request, redirect, url_for

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        usuario = Usuario.query.filter_by(username=username).first()
        if usuario and check_password_hash(usuario.password, password):
            login_user(usuario)
            if current_user.es_admin:
                return redirect(url_for('admin'))
            return redirect(url_for('perfil'))
        return render_template('login.html', error='Usuario o contraseña incorrectos')
    return render_template('login.html', error=None)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin():
    if not current_user.es_admin:
        abort(403)
    return render_template('admin.html', camara_activa=camara_activa)

@app.route('/admin/toggle_camara', methods=['POST'])
@login_required
def toggle_camara():
    if not current_user.es_admin:
        abort(403)
    global camara_activa
    camara_activa = not camara_activa
    return redirect(url_for('admin'))

@app.route('/admin/logs')
@login_required
def admin_logs():
    if not current_user.es_admin:
        abort(403)
    try:
        resultado = os.popen('journalctl -u zulo -n 100 --no-pager --output=short').read()
    except Exception as e:
        resultado = f'Error al leer logs: {e}'
    return jsonify({'logs': resultado})

# --- Chat ---
usuarios_conectados = {}

@app.route('/chat')
def chat():
    return render_template('chat.html')

@socketio.on('entrar')
def handle_entrar(data):
    usuarios_conectados[request.sid] = {'nombre': data['nombre'], 'color': data['color']}
    emit('mensaje', {'nombre': 'Sistema', 'texto': data['nombre'] + ' ha entrado al chat', 'color': '#8b949e'}, broadcast=True)
    emit('usuarios', list(usuarios_conectados.values()), broadcast=True)

@socketio.on('mensaje')
def handle_mensaje(data):
    emit('mensaje', data, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    usuario = usuarios_conectados.pop(request.sid, None)
    if usuario:
        emit('mensaje', {'nombre': 'Sistema', 'texto': usuario['nombre'] + ' se ha desconectado', 'color': '#8b949e'}, broadcast=True)
        emit('usuarios', list(usuarios_conectados.values()), broadcast=True)


# --- Registro ---
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre    = request.form.get('nombre', '').strip()
        apellidos = request.form.get('apellidos', '').strip()
        username  = request.form.get('username', '').strip()
        password  = request.form.get('password', '').strip()

        if not nombre or not apellidos or not username or not password:
            return render_template('registro.html', error='Rellena todos los campos.')

        if Usuario.query.filter_by(username=username).first():
            return render_template('registro.html', error='Ese nombre de usuario ya existe.')

        nuevo = Usuario(
            nombre=nombre,
            apellidos=apellidos,
            username=username,
            password=generate_password_hash(password),
            es_admin=False
        )
        db.session.add(nuevo)
        db.session.commit()
        login_user(nuevo)
        return redirect(url_for('perfil'))

    return render_template('registro.html', error=None)


# --- Perfil ---
@app.route('/perfil')
@login_required
def perfil():
    return render_template('perfil.html')

@app.route('/perfil/editar', methods=['POST'])
@login_required
def perfil_editar():
    nombre    = request.form.get('nombre', '').strip()
    apellidos = request.form.get('apellidos', '').strip()
    username  = request.form.get('username', '').strip()

    if not nombre or not apellidos or not username:
        return render_template('perfil.html', error_editar='Rellena todos los campos.')

    # Comprobar que el username no lo use otro
    existente = Usuario.query.filter_by(username=username).first()
    if existente and existente.id != current_user.id:
        return render_template('perfil.html', error_editar='Ese nombre de usuario ya está en uso.')

    current_user.nombre    = nombre
    current_user.apellidos = apellidos
    current_user.username  = username
    db.session.commit()
    return render_template('perfil.html', ok_editar='Datos actualizados correctamente.')

@app.route('/perfil/cambiar_password', methods=['POST'])
@login_required
def perfil_cambiar_password():
    actual   = request.form.get('actual', '')
    nueva    = request.form.get('nueva', '').strip()
    repetir  = request.form.get('repetir', '').strip()

    if not check_password_hash(current_user.password, actual):
        return render_template('perfil.html', error_pass='Contraseña actual incorrecta.')
    if len(nueva) < 6:
        return render_template('perfil.html', error_pass='La nueva contraseña debe tener al menos 6 caracteres.')
    if nueva != repetir:
        return render_template('perfil.html', error_pass='Las contraseñas no coinciden.')

    current_user.password = generate_password_hash(nueva)
    db.session.commit()
    return render_template('perfil.html', ok_pass='Contraseña cambiada correctamente.')


# --- Admin: gestión de usuarios ---
@app.route('/admin/usuarios')
@login_required
def admin_usuarios():
    if not current_user.es_admin:
        abort(403)
    usuarios = Usuario.query.filter_by(es_admin=False).order_by(Usuario.id).all()
    return jsonify([{
        'id': u.id,
        'nombre': u.nombre,
        'apellidos': u.apellidos,
        'username': u.username
    } for u in usuarios])

@app.route('/admin/reset_password/<int:user_id>', methods=['POST'])
@login_required
def admin_reset_password(user_id):
    if not current_user.es_admin:
        abort(403)
    usuario = Usuario.query.get_or_404(user_id)
    usuario.password = generate_password_hash('reset1234')
    db.session.commit()
    return jsonify({'ok': True, 'username': usuario.username})

@app.route('/admin/eliminar_usuario/<int:user_id>', methods=['POST'])
@login_required
def admin_eliminar_usuario(user_id):
    if not current_user.es_admin:
        abort(403)
    usuario = Usuario.query.get_or_404(user_id)
    db.session.delete(usuario)
    db.session.commit()
    return jsonify({'ok': True})


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8080, debug=True)