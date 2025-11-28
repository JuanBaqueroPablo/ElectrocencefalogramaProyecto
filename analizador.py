import pandas as pd
import matplotlib.pyplot as plt
import sys
import glob
import os

def visualize(filename):
    """
    Función principal para leer un archivo CSV y generar visualizaciones.
    """
    print(f"\n--- Analizando la sesión: {filename} ---\n")
    
    try:
        data = pd.read_csv(filename, index_col='Timestamp', parse_dates=True)
        
        # Comprueba si el DataFrame está vacío después de cargar
        if data.empty:
            print("************************************************************")
            print("ADVERTENCIA: Este archivo de sesión está vacío (solo cabecera).")
            print("No se pueden generar gráficos.")
            print("************************************************************")
            return

        print(f"Archivo cargado. Contiene {len(data)} lecturas.")

    except FileNotFoundError:
        print(f"ERROR: El archivo '{filename}' no fue encontrado.")
        return
    except pd.errors.EmptyDataError:
        print("************************************************************")
        print("ADVERTENCIA: Este archivo de sesión está completamente vacío.")
        print("No se pueden generar gráficos.")
        print("************************************************************")
        return
    except Exception as e:
        print(f"ERROR al leer el archivo. Puede que esté corrupto. Detalle: {e}")
        return

    # Gráfico 1: Actividad promedio a lo largo del tiempo
    plt.figure(figsize=(15, 6))
    data.mean(axis=1).plot(title=f'Actividad Cerebral Promedio\n({os.path.basename(filename)})')
    plt.xlabel('Tiempo de la Sesión'), plt.ylabel('Amplitud Promedio')
    plt.grid(True), plt.tight_layout(), plt.show()

    # Gráfico 2: Espectrograma
    plt.figure(figsize=(15, 8))
    plt.imshow(data.T, aspect='auto', origin='lower', cmap='viridis')
    plt.colorbar(label='Amplitud'), plt.title(f'Espectrograma\n({os.path.basename(filename)})')
    plt.xlabel('Muestras de Tiempo'), plt.ylabel('Bines de Frecuencia')
    plt.tight_layout(), plt.show()

def interactive_menu():
    """
    Busca archivos de sesión y muestra un menú interactivo.
    """