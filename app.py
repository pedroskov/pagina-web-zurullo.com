from flask import Flask, render_template, send_file, abort, request, jsonify
import psutil
import os
import sympy

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)