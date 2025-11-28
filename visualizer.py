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
    print("Buscando archivos de sesión (sesion_*.csv)...")
    session_files = glob.glob('sesion_*.csv')
    
    if not session_files:
        print("\nNo se encontraron archivos de sesión en esta carpeta.")
        return

    session_files.sort(key=os.path.getmtime, reverse=True)
    
    print("\n--- Por favor, elige una sesión para analizar ---")
    for i, filename in enumerate(session_files):
        print(f"  [{i + 1}] {filename}")
    
    while True:
        try:
            choice = input("\nIntroduce el número de la sesión (o 'q' para salir): ")
            if choice.lower() in ['q', 'quit', 'exit']:
                return
            
            choice_index = int(choice) - 1
            if 0 <= choice_index < len(session_files):
                visualize(session_files[choice_index])
                return
            else:
                print("Número fuera de rango. Inténtalo de nuevo.")
        except ValueError:
            print("Entrada no válida. Por favor, introduce un número.")
        except (KeyboardInterrupt, EOFError):
            print("\nSaliendo.")
            return

if __name__ == '__main__':
    if len(sys.argv) > 1:
        # Modo argumento: se pasa el nombre del archivo al ejecutar
        visualize(sys.argv[1])
    else:
        # Modo interactivo: se muestra un menú
        interactive_menu()