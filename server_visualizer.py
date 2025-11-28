# import serial # <-- 1. COMENTAMOS LA LIBRERÍA SERIAL, YA NO LA NECESITAMOS
import threading
import time
from flask import Flask, jsonify, render_template, request
import csv
from datetime import datetime
import glob
import os
import pandas as pd
import random # <-- 2. AÑADIMOS LA LIBRERÍA PARA NÚMEROS ALEATORIOS

# --- 1. CONFIGURACIÓN (El puerto ya no se usa, pero lo dejamos por si se reactiva) ---
SERIAL_PORT = '/dev/ttyUSB0'
SERIAL_RATE = 115200

# --- 2. ALMACENAMIENTO DE DATOS Y ESTADO ---
latest_data = []
data_lock = threading.Lock()
is_session_active = False
session_filename = ""
session_lock = threading.Lock()

# --- 3. NUEVA FUNCIÓN PARA SIMULAR DATOS ---
def simulate_serial_data():
    """
    Esta función reemplaza a read_from_serial.
    Genera 32 valores aleatorios cada segundo y los actualiza en latest_data.
    También guarda los datos si hay una sesión activa.
    """
    global latest_data, is_session_active, session_filename
    print("Iniciando simulación de datos EEG...")
    
    while True:
        # Genera una lista de 32 enteros aleatorios entre 0 y 90
        # (para que no siempre lleguen al máximo del gráfico de 100)
        simulated_values = [random.randint(0, 90) for _ in range(32)]
        
        # Un pequeño truco para hacer los datos más "realistas" y no tan planos:
        # Hacemos que la banda "alpha" (bins 4-6) y "beta" (6-15) sean un poco más altas a veces
        if random.random() > 0.5: # 50% de las veces
            for i in range(4, 15):
                simulated_values[i] = random.randint(30, 95) # Aumentamos los valores en estas bandas

        with data_lock:
            latest_data = simulated_values
        
        with session_lock:
            if is_session_active and session_filename:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                with open(session_filename, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([timestamp] + simulated_values)
        
        # Espera 1 segundo para simular el flujo de datos en tiempo real
        time.sleep(1)


# --- 4. FUNCIÓN ORIGINAL (LA HEMOS COMENTADO PARA DESACTIVARLA) ---
"""
def read_from_serial():
    global latest_data, is_session_active, session_filename
    while True:
        try:
            with serial.Serial(SERIAL_PORT, SERIAL_RATE, timeout=1) as ser:
                print(f"Conectado exitosamente al puerto serie: {SERIAL_PORT}")
                while True:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    
                    if not line:
                        continue

                    try:
                        values_str = line.split(',')
                        if len(values_str) == 32:
                            values = [int(v) for v in values_str]
                            
                            with data_lock:
                                latest_data = values
                            
                            with session_lock:
                                if is_session_active and session_filename:
                                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                                    with open(session_filename, 'a', newline='') as f:
                                        writer = csv.writer(f)
                                        writer.writerow([timestamp] + values)
                    except ValueError:
                        pass
        except serial.SerialException:
            print(f"No se pudo conectar al puerto {SERIAL_PORT}. Reintentando...")
            time.sleep(5)
        except Exception as e:
            print(f"Error en el hilo de lectura: {e}")
            time.sleep(5)
"""

# --- 5. SERVIDOR WEB CON FLASK (Sin cambios aquí) ---
app = Flask(__name__)

@app.route('/')
def index():
    global is_session_active
    with session_lock:
        is_session_active = False
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    with data_lock:
        return jsonify(latest_data[:])

@app.route('/api/start_session', methods=['POST'])
def start_session():
    global is_session_active, session_filename
    try:
        user_data = request.json
        nombre = user_data.get('nombre', 'sin_nombre')
        apellido = user_data.get('apellido', 'sin_apellido')
        actividad = user_data.get('actividad', 'sin_actividad')
        
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"sesion_{nombre}_{apellido}_{actividad}_{timestamp_str}.csv"
        
        with session_lock:
            session_filename = filename
            with open(session_filename, 'w', newline='') as f:
                writer = csv.writer(f)
                headers = ['Timestamp'] + [f'Bin_{i}' for i in range(32)]
                writer.writerow(headers)
            
            is_session_active = True
            print(f"Sesión iniciada. Guardando datos en: {session_filename}")
            return jsonify({"status": "success", "message": "Sesión iniciada", "filename": session_filename})
    except Exception as e:
        print(f"ERROR al iniciar sesión: {e}")
        return jsonify({"status": "error", "message": "No se pudo crear el archivo de sesión"}), 500

@app.route('/api/sessions')
def list_sessions():
    session_files = glob.glob('sesion_*.csv')
    session_files.sort(key=os.path.getmtime, reverse=True)
    return jsonify(session_files)

@app.route('/api/session_data/<path:filename>')
def get_session_data(filename):
    if not (filename.startswith('sesion_') and filename.endswith('.csv') and ".." not in filename):
        return jsonify({"status": "error", "message": "Nombre de archivo no válido"}), 400
    try:
        df = pd.read_csv(filename)
        return df.to_json(orient='split', index=False)
    except FileNotFoundError:
        return jsonify({"status": "error", "message": "Archivo no encontrado"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- 6. INICIO DEL PROGRAMA ---
if __name__ == '__main__':
    # <-- 5. CAMBIAMOS EL TARGET DEL HILO A NUESTRA FUNCIÓN DE SIMULACIÓN
    serial_thread = threading.Thread(target=simulate_serial_data, daemon=True)
    # serial_thread = threading.Thread(target=read_from_serial, daemon=True) # Línea original comentada
    
    serial_thread.start()
    print("Servidor web iniciado en http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)

# --- ¿Cómo Usarlo?

# 1.  **Detén** el servidor `server.py` si lo tienes en ejecución (presionando `Ctrl+C` en la terminal).
# 2.  **Reemplaza** el contenido de tu archivo `server.py` con el código de arriba.
# 3.  **No modifiques** tu `index.html`.
# 4.  **Vuelve a ejecutar** el servidor: `python server.py`.
# 5.  **Abre tu navegador** en `http://127.0.0.1:5000`.

# Ahora, cuando inicies un monitoreo en tiempo real, verás un gráfico de barras que cambia cada segundo con datos generados aleatoriamente, y el "Estado Estimado" también cambiará dinámicamente. Podrás crear y guardar sesiones de prueba, y luego visualizarlas con el gráfico de línea, todo sin necesidad de conectar el hardware.

# Cuando vuelvas a tener tu equipo, solo tienes que revertir los cambios en `server.py`:
# *   Descomenta la función `read_from_serial` y la importación de `serial`.
# *   Comenta la función `simulate_serial_data`.
# *   En la sección `__main__`, vuelve a apuntar el `target` del hilo a `read_from_serial`.