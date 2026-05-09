import os
import sys
import subprocess
import time

def flush_print(msg):
    print(msg)
    sys.stdout.flush()

def run_script(script_name, base_dir):
    script_path = os.path.join(base_dir, script_name)
    flush_print(f"\n" + "="*60)
    flush_print(f"INICIANDO PASO: {script_name}")
    flush_print("="*60 + "\n")
    
    # Execute python script unbuffered and stream output to terminal
    proc = subprocess.Popen(
        [sys.executable, "-u", script_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        bufsize=1
    )
    
    # Read output line by line as it is written
    while True:
        line = proc.stdout.readline()
        if not line and proc.poll() is not None:
            break
        if line:
            print(line.rstrip())
            sys.stdout.flush()
            
    proc.wait()
    if proc.returncode != 0:
        flush_print(f"\n[ERROR] El script {script_name} falló con código de salida {proc.returncode}.")
        return False
        
    flush_print(f"\n[ÉXITO] Paso completado con éxito: {script_name}\n")
    return True

def main():
    base_dir = r"C:\Users\Juan\Dropbox\Proyectos 2026\Med&Corp\CheckUp"
    
    flush_print("="*70)
    flush_print("MED&CORP PIPELINE INTEGRADO DE ALTO RENDIMIENTO")
    flush_print("Iniciando procesamiento masivo para 195 pacientes SANOFI...")
    flush_print("="*70)
    
    start_time = time.time()
    
    # Paso 1: Extracción individual de estudios (resiliente e incremental)
    if not run_script("excel_lab_integrator.py", base_dir):
        flush_print("[ERROR CRÍTICO] La extracción de estudios individuales falló. Deteniendo pipeline.")
        sys.exit(1)
        
    # Paso 2: Integración en el Concentrado Maestro (usando correspondencia p10)
    if not run_script("Integrador_Maestro.py", base_dir):
        flush_print("[ERROR CRÍTICO] La integración del concentrado maestro falló. Deteniendo pipeline.")
        sys.exit(1)
        
    # Paso 3: Generación masiva de reportes PDF de alta fidelidad
    if not run_script("Generador_Reportes_PDF.py", base_dir):
        flush_print("[ERROR CRÍTICO] La generación masiva de PDFs falló.")
        sys.exit(1)
        
    end_time = time.time()
    duration = end_time - start_time
    minutes = int(duration // 60)
    seconds = int(duration % 60)
    
    flush_print("="*70)
    flush_print("🎉 ¡PIPELINE INTEGRADO FINALIZADO CON ÉXITO! 🎉")
    flush_print(f"Tiempo total de procesamiento: {minutes} minutos y {seconds} segundos.")
    flush_print("Los reportes finales se encuentran listos en 'REPORTES FINALES/'.")
    flush_print("="*70)

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    main()
