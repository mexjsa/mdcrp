import os
import glob
import pandas as pd
import json
import sys
from datetime import datetime
from lab_extractor_native import extract_data_from_pdf
from odontogram_drawer import generate_marked_odontogram
import fitz
from PIL import Image

def flush_print(msg):
    print(msg)
    sys.stdout.flush()

def get_timestamp():
    """Genera marca de tiempo YYYYMMDD_HHmm"""
    return datetime.now().strftime("%Y%m%d_%H%M")

def process_all_studies(base_dir):
    """
    Escanea las subcarpetas dentro de ESTUDIOS INDIVIDUALES.
    Procesa todos los PDF de cada carpeta de forma secuencial y unbuffered, 
    guardando el progreso incrementalmente en un JSON para tolerar interrupciones de red o de proceso.
    """
    estudios_dir = os.path.join(base_dir, "ESTUDIOS INDIVIDUALES")
    base_img_path = os.path.join(base_dir, "odontogram_base.png")
    
    if not os.path.exists(estudios_dir):
        flush_print(f"Error: No se encontró el directorio {estudios_dir}")
        return

    for study_folder in os.listdir(estudios_dir):
        study_path = os.path.join(estudios_dir, study_folder)
        
        if os.path.isdir(study_path):
            flush_print(f"\n--- Procesando carpeta de estudio: {study_folder} ---")
            
            pdf_files = glob.glob(os.path.join(study_path, "*.pdf"))
            if not pdf_files:
                flush_print(f"No se encontraron PDFs en {study_folder}. Saltando...")
                continue
                
            progress_file = os.path.join(study_path, f"{study_folder.replace(' ', '_')}_progress_v5.json")
            all_records = []
            processed_files = set()
            
            # Cargar progreso anterior para reanudación instantánea
            if os.path.exists(progress_file):
                try:
                    with open(progress_file, 'r', encoding='utf-8') as f:
                        all_records = json.load(f)
                    processed_files = {r['Archivo_Origen'] for r in all_records}
                    flush_print(f"¡Progreso de sesión encontrado! Cargados {len(all_records)} registros ya procesados. Continuando...")
                except Exception as e:
                    flush_print(f"No se pudo cargar progreso anterior: {e}. Iniciando de cero...")
                    all_records = []
                    processed_files = set()

            total_files = len(pdf_files)
            for idx, pdf_file in enumerate(pdf_files, 1):
                filename = os.path.basename(pdf_file)
                
                if filename in processed_files:
                    flush_print(f"  [{idx}/{total_files}] Saltando (ya en caché): {filename}")
                    continue
                    
                flush_print(f"  [{idx}/{total_files}] Procesando: {filename}")
                record = extract_data_from_pdf(pdf_file)
                
                if record:
                    all_records.append(record)
                    processed_files.add(filename)
                    
                    # --- GENERACION DE IMAGEN PARA ODONTOGRAMAS ---
                    if record.get('Tipo_Estudio') == "ODONTOGRAMA":
                        img_name = os.path.splitext(filename)[0] + ".png"
                        img_output_path = os.path.join(study_path, img_name)
                        # Siempre regenerar para evitar odontogramas en blanco por caché
                        flush_print(f"    [IMG] Generando gráfico odontograma: {img_name}")
                        generate_marked_odontogram(record, img_output_path, base_img_path)
                    
                    # --- GENERACION DE IMAGEN PARA ELECTROCARDIOGRAMA ---
                    if record.get('Tipo_Estudio') == "ELECTROCARDIOGRAMA":
                        img_name = os.path.splitext(filename)[0] + ".jpg"
                        img_output_path = os.path.join(study_path, img_name)
                        if not os.path.exists(img_output_path):
                            flush_print(f"    [IMG] Uniendo hojas 2 y 3 para: {img_name}")
                            try:
                                doc = fitz.open(pdf_file)
                                if len(doc) >= 3:
                                    pix2 = doc[1].get_pixmap(dpi=200)
                                    img2 = Image.frombytes("RGB", [pix2.width, pix2.height], pix2.samples)
                                    pix3 = doc[2].get_pixmap(dpi=200)
                                    img3 = Image.frombytes("RGB", [pix3.width, pix3.height], pix3.samples)
                                    
                                    total_width = img2.width + img3.width
                                    max_height = max(img2.height, img3.height)
                                    
                                    final_img = Image.new('RGB', (total_width, max_height), (255, 255, 255))
                                    final_img.paste(img2, (0, 0))
                                    final_img.paste(img3, (img2.width, 0))
                                    
                                    final_img.save(img_output_path, "JPEG", quality=85)
                                doc.close()
                            except Exception as e:
                                flush_print(f"    [ERROR] No se pudo unir las imágenes del EKG para {filename}: {e}")
                    
                    # Guardar progreso incrementalmente
                    try:
                        with open(progress_file, 'w', encoding='utf-8') as f:
                            json.dump(all_records, f, indent=2, ensure_ascii=False)
                    except Exception as e:
                        pass
            
            if len(all_records) > 0:
                df = pd.DataFrame(all_records)
                cols = df.columns.tolist()
                clave_cols = ['CURP_ID', 'Paciente_Nombre', 'Tipo_Estudio', 'Archivo_Origen']
                existing_clave_cols = [c for c in clave_cols if c in cols]
                for c in existing_clave_cols:
                    cols.remove(c)
                cols = existing_clave_cols + cols
                df = df[cols]
                
                timestamp = get_timestamp()
                excel_filename = f"{timestamp}_{study_folder.replace(' ', '_')}.xlsx"
                excel_path = os.path.join(study_path, excel_filename)
                
                df.to_excel(excel_path, index=False)
                flush_print(f"[EXITO] -> Consolidado generado con {len(all_records)} registros: {excel_path}")
                
                if os.path.exists(progress_file):
                    try:
                        os.remove(progress_file)
                    except:
                        pass
                flush_print("")

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    if getattr(sys, 'frozen', False):
        base_checkup_dir = os.path.dirname(sys.executable)
    else:
        base_checkup_dir = os.path.dirname(os.path.abspath(__file__))
        
    flush_print(f"Iniciando Motor Med&Corp Resiliente (v5 - Reanudación Incremental y Unbuffered)...\nDirectorio Base: {base_checkup_dir}\n")
    try:
        process_all_studies(base_checkup_dir)
    except Exception as e:
        flush_print(f"Error critico: {e}")
    flush_print("\nProceso finalizado.")
