from flask import Flask, render_template, send_file, abort
import psutil
import os

app = Flask(__name__)

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

# --- Rutas ---

@app.route('/')
def index():
    stats = get_stats()
    return render_template('index.html', stats=stats)

@app.route('/chat')
def chat():
    return render_template('chat.html')

@app.route('/datos')
def datos():
    return render_template('datos.html')

@app.route('/notas')
def notas():
    return render_template('notas.html')

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)