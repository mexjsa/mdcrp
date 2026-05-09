import os
import re
import fitz  # PyMuPDF
import PyPDF2
from PIL import Image
import io
import numpy as np

# Lazy load easyocr
reader = None

def get_easyocr_reader():
    global reader
    if reader is None:
        import easyocr
        import sys
        # Evitar problemas de encoding en la consola de Windows
        sys.stdout.reconfigure(encoding='utf-8')
        reader = easyocr.Reader(['es'], verbose=False)
    return reader

def extract_ekg_data(pdf_path):
    extracted_data = {}
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=200)
    img_data = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_data))
    img_np = np.array(img)
    
    ocr_reader = get_easyocr_reader()
    result = ocr_reader.readtext(img_np)
    
    texts = [t[1].strip() for t in result if t[2] > 0.3]
    
    # Unimos todo el texto para búsqueda general
    full_text = " ".join(texts)
    
    if "ELECTROCARDIOGRAMA" not in full_text.upper():
        return None # No es un electro
        
    extracted_data['Tipo_Estudio'] = "ELECTROCARDIOGRAMA"
    extracted_data['CURP_ID'] = ""
    
    # Lógica de extracción (key: next values)
    keys_to_find = {
        "PACIENTE:": "Paciente_Nombre",
        "FECHA:": "Fecha_Estudio",
        "EDAD:": "Edad",
        "SEXO:": "Sexo",
        "Ritmo:": "Ritmo",
        "Frecuencia:": "Frecuencia",
        "Eje QRS:": "Eje_QRS",
        "Onda P:": "Onda_P",
        "Intervalo PR:": "Intervalo_PR",
        "Complejo QRS:": "Complejo_QRS",
        "Segmento ST:": "Segmento_ST",
        "Onda T:": "Onda_T",
        "Intervalo QTc:": "Intervalo_QTc",
        "Precordiales:": "Precordiales",
        "Observaciones:": "Observaciones",
        "Conclusión:": "Conclusion",
        "Conclusion:": "Conclusion"
    }
    
    # Heurística simple: buscar la etiqueta en un item, y tomar el texto de los siguientes items
    # hasta que encontremos otra etiqueta o lleguemos al final (max 3 items para valores cortos, más para conclusiones)
    
    for i, text in enumerate(texts):
        for key, field_name in keys_to_find.items():
            if text.upper().startswith(key.upper()):
                # Encontramos la etiqueta.
                # A veces el valor está en la misma línea: "PACIENTE: Juan Perez"
                val = text[len(key):].strip()
                if val:
                    extracted_data[field_name] = val
                    continue
                
                # Si no, buscar en los siguientes items
                val_parts = []
                for j in range(i+1, min(len(texts), i+6)): # Mirar hasta 5 items adelante
                    # Si el siguiente texto es otra etiqueta conocida, paramos
                    is_next_key = any(texts[j].upper().startswith(k.upper()) for k in keys_to_find.keys())
                    if is_next_key:
                        break
                    # Si llegamos a texto basura del final, paramos
                    if "ATENTAMENTE" in texts[j].upper() or "DIAGNÓSTICO" in texts[j].upper():
                        break
                    val_parts.append(texts[j])
                
                if val_parts:
                    extracted_data[field_name] = " ".join(val_parts)
    
    return extracted_data

def extract_data_from_pdf(pdf_path):
    """
    Lee un PDF y extrae parámetros clínicos. 
    Soporta Laboratorios, Odontogramas, Espirometrías y EKG Med&Corp.
    """
    extracted_data = {}
    filename = os.path.basename(pdf_path)
    extracted_data['Archivo_Origen'] = filename
    
    try:
        # --- 1. INTENTAR EXTRACCIÓN DE FORMULARIO (ODONTOGRAMAS) ---
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            fields = reader.get_fields()
            if fields:
                form_data = {k: v.get('/V') for k, v in fields.items() if v.get('/V') is not None}
                if 'dp18' in form_data or 'SUP DERECHO 10SCENTRAL 1' in form_data:
                    extracted_data['CURP_ID'] = "" 
                    extracted_data['Tipo_Estudio'] = "ODONTOGRAMA"
                    mappings = {
                        'Nombre completo': 'Paciente_Nombre',
                        'Fecha1_af_date': 'Fecha_Estudio',
                        'Recomendaciones OdontológicasRow1': 'Recomendaciones_Dentales'
                    }
                    for k, v in form_data.items():
                        val = v.replace('\r', ' ').strip() if isinstance(v, str) else v
                        extracted_data[mappings.get(k, k)] = val
                    return extracted_data

        # --- 2. EXTRACCIÓN DE TEXTO (LABS Y ESPIROMETRÍA) ---
        doc = fitz.open(pdf_path)
        full_text = ""
        pages_text = []
        for page in doc:
            t = page.get_text("text")
            full_text += t + "\n"
            pages_text.append(t)
        doc.close()
        
        # Si no hay texto, probablemente sea un EKG u otro estudio escaneado
        if not full_text.strip():
            ekg_data = extract_ekg_data(pdf_path)
            if ekg_data:
                ekg_data['Archivo_Origen'] = filename
                return ekg_data
            else:
                return extracted_data

        norm_text = re.sub(r'\s+', ' ', full_text)
        
        # --- DETECCION ESPIROMETRÍA ---
        is_espirometria = "ndd Medizintechnik" in norm_text or "Espirometría" in norm_text
        
        if is_espirometria:
            extracted_data['Tipo_Estudio'] = "ESPIROMETRIA"
            extracted_data['CURP_ID'] = ""
            
            # Extraer Nombre e ID
            id_match = re.search(r'ID:\s*(\d+)', full_text)
            if id_match: extracted_data['ID_Paciente'] = id_match.group(1)
            
            lines = [l.strip() for l in full_text.split('\n') if l.strip()]
            for i, line in enumerate(lines):
                if "ID:" in line and "Edad:" in line:
                    if i+1 < len(lines):
                        extracted_data['Paciente_Nombre'] = lines[i+1]
                
                # En este formato ndd, el valor suele estar 2 líneas ARRIBA de la etiqueta
                if "Interpretación del sistema" in line:
                    if i-2 >= 0 and "Normal" in lines[i-2]:
                         extracted_data['Interpretacion_Sistema'] = lines[i-2]
                
                if "Calidad de la sesión" in line:
                    if i-1 >= 0:
                        extracted_data['Calidad_Sesion'] = lines[i-1]

            # Parámetros numéricos (Reverse search)
            params = ["FVC [L]", "FEV1 [L]", "FEV1/FVC [%]", "PEF [L/s]", "FEF25-75% [L/s]"]
            for p in params:
                p_idx = -1
                for i, line in enumerate(lines):
                    if p in line:
                        p_idx = i
                        break
                if p_idx != -1:
                    # Estructura: Z(-7), Mejor(-6), P2(-5), P3(-4), P4(-3), LLN(-2), Pred(-1)
                    try:
                        extracted_data[f"{p}_Mejor"] = lines[p_idx-6]
                        extracted_data[f"{p}_Pred"] = lines[p_idx-1]
                        extracted_data[f"{p}_LLN"] = lines[p_idx-2]
                    except:
                        pass
            
            if 'Interpretacion_Sistema' not in extracted_data:
                if "Espirometría Normal" in full_text:
                    extracted_data['Interpretacion_Sistema'] = "Espirometría Normal"

        else:
            # --- LOGICA LABORATORIO TRADICIONAL ---
            curp = filename.split('_')[0] if '_' in filename else filename[:18]
            extracted_data['CURP_ID'] = curp
            extracted_data['Tipo_Estudio'] = "LABORATORIO"
            pattern = re.compile(r'^([a-zA-ZáéíóúÁÉÍÓÚñÑ\.\s\(\)]+?)\s+(\d+\.?\d*)\s+.*$')
            skip_words = ['Fecha', 'Edad', 'Paciente', 'Sexo', 'Hoja', 'Orden', 'ID Paciente', 'Prueba Bajo', 'Límites', 'Semanas', 'Muestra']
            for line in full_text.split('\n'):
                line = line.strip()
                if any(line.startswith(w) for w in skip_words) or len(line) < 5:
                    continue
                match = pattern.match(line)
                if match:
                    param_name = match.group(1).strip()
                    val_str = match.group(2).strip()
                    if len(param_name) > 3:
                        try:
                            extracted_data[param_name] = float(val_str) if '.' in val_str else int(val_str)
                        except:
                            extracted_data[param_name] = val_str

    except Exception as e:
        print(f"Error procesando {pdf_path}: {e}")
        
    return extracted_data

if __name__ == "__main__":
    import sys
    import json
    if len(sys.argv) > 1:
        res = extract_data_from_pdf(sys.argv[1])
        print(json.dumps(res, indent=2, ensure_ascii=False))
