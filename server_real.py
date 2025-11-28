import serial
import threading
import time
from flask import Flask, jsonify, render_template, request
import csv
from datetime import datetime
import glob
import os
import pandas as pd
import base64 # Necesario para decodificar la imagen
import re     # Necesario para procesar el string de la imagen

# --- 1. CONFIGURACIÓN ---
SERIAL_PORT = '/dev/ttyUSB0'  # ¡AJUSTA ESTO A TU PUERTO! (Ej. 'COM3' en Windows)
SERIAL_RATE = 115200

# --- 2. ALMACENAMIENTO DE DATOS Y ESTADO ---
latest_data = []
data_lock = threading.Lock()
is_session_active = False
session_filename = ""
session_lock = threading.Lock()

# --- 3. FUNCIÓN PARA LEER DEL ARDUINO ---
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

# --- 4. SERVIDOR WEB CON FLASK ---
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
        # Limpiar caracteres no válidos para nombres de archivo
        nombre_limpio = "".join(c for c in nombre if c.isalnum() or c in (' ', '_')).rstrip()
        apellido_limpio = "".join(c for c in apellido if c.isalnum() or c in (' ', '_')).rstrip()
        actividad_limpia = "".join(c for c in actividad if c.isalnum() or c in (' ', '_')).rstrip()

        filename = f"sesion_{nombre_limpio}_{apellido_limpio}_{actividad_limpia}_{timestamp_str}.csv"
        
        with session_lock:
            session_filename = filename
            with open(session_filename, 'w', newline='') as f:
                writer = csv.writer(f)
                headers = ['Timestamp'] + [f'Bin_{i}' for i in range(32)]
                writer.writerow(headers)
            
            is_session_active = True
            print(f"Sesión iniciada. Guardando datos en: {session_filename}")
            # Devuelve el nombre del archivo para que el cliente pueda usarlo
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

# --- NUEVO ENDPOINT PARA GUARDAR LA IMAGEN DEL GRÁFICO ---
@app.route('/api/save_chart_image', methods=['POST'])
def save_chart_image():
    try:
        data = request.json
        csv_filename = data.get('filename')
        image_data_url = data.get('imageData')

        if not csv_filename or not image_data_url:
            return jsonify({"status": "error", "message": "Faltan datos (filename o imageData)"}), 400

        # Crear el nombre del archivo de imagen a partir del nombre del CSV
        image_filename = os.path.splitext(csv_filename)[0] + '.png'
        
        # El string viene como 'data:image/png;base64,iVBORw0KGgo...'. Hay que quitar la cabecera.
        header, encoded = image_data_url.split(',', 1)
        image_data = base64.b64decode(encoded)
        
        with open(image_filename, 'wb') as f:
            f.write(image_data)
            
        print(f"Gráfico guardado exitosamente como: {image_filename}")
        return jsonify({"status": "success", "message": "Imagen guardada"})
    except Exception as e:
        print(f"ERROR al guardar la imagen del gráfico: {e}")
        return jsonify({"status": "error", "message": "No se pudo guardar la imagen"}), 500

# --- 5. INICIO DEL PROGRAMA ---
if __name__ == '__main__':
    serial_thread = threading.Thread(target=read_from_serial, daemon=True)
    serial_thread.start()
    print("Servidor web iniciado en http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)