import os
import pandas as pd
import json
import asyncio
from playwright.async_api import async_playwright
from docx import Document
import base64
import re
import unicodedata
import sys
import time

def normalize_name(text):
    if not isinstance(text, str): return ""
    text = text.upper()
    nfd = unicodedata.normalize('NFD', text)
    text = "".join([c for c in nfd if not unicodedata.combining(c)])
    return re.sub(r'[^A-Z0-9]', '', text)

def get_base64_image(path):
    if path and os.path.exists(path):
        with open(path, "rb") as f:
            ext = os.path.splitext(path)[1].lower().replace('.', '')
            if ext == 'jpg': ext = 'jpeg'
            return f"data:image/{ext};base64," + base64.b64encode(f.read()).decode('utf-8')
    return None

def parse_docx_paragraphs(docx_path):
    if not os.path.exists(docx_path):
        return []
    try:
        doc = Document(docx_path)
        lines = []
        for p in doc.paragraphs:
            for l in p.text.split('\n'):
                if l.strip(): lines.append(l.strip())
        start_idx = 0
        for i, l in enumerate(lines):
            if len(l) > 150:
                start_idx = i
                break
        return lines[start_idx:]
    except Exception as e:
        print(f"Error reading docx {docx_path}: {e}")
        return []

def chunk_telemed_paras(paras, target_chars=3400):
    pages = []
    current_page = []
    current_len = 0
    
    i = 0
    while i < len(paras):
        p = paras[i]
        p_len = len(p)
        is_heading = (p_len < 80 and (p.isupper() or p.startswith('•') or p.startswith('-') or (':' in p and p_len < 60)))
        
        # Check if heading would be left alone at bottom of page
        if is_heading and i + 1 < len(paras):
            next_len = len(paras[i+1])
            combined_len = p_len + next_len + 50
            if current_len + combined_len > target_chars and current_len > 2200:
                pages.append(current_page)
                current_page = [p, paras[i+1]]
                current_len = combined_len
                i += 2
                continue
                
        # Normal paragraph
        if current_len + p_len > target_chars and current_len > 2200:
            pages.append(current_page)
            current_page = [p]
            current_len = p_len
        else:
            current_page.append(p)
            current_len += p_len + 40
        i += 1
        
    if current_page:
        pages.append(current_page)
        
    return pages

def clean_telemed_content(paras, ekg_png_path):
    cleaned = []
    for p in paras:
        if not ekg_png_path:
            if "Su electrocardiograma se encuentra completamente normal" in p or "El electrocardiograma documenta" in p or "estudio electrocardiogr" in p:
                continue
            
            p = re.sub(r'(?i)nos complace informarle que su coraz.*?(?:electrocard.*?; sin embargo, |electrocard.*?; )', '', p)
            p = re.sub(r'(?i)las cuales abarcan un electrocardiograma, ', 'las cuales abarcan ', p)
            p = re.sub(r'(?i)Nos complace informarle que su salud cardiovascular se encuentra.*?No obstante, ', '', p)
            
            p = p.replace(" y del electrocardiograma digital", "")
            p = p.replace(", electrocardiograma ", " ")
            p = p.replace("electrocardiograma, ", "")
            p = p.replace("un electrocardiograma, ", "")
        cleaned.append(p)
    return cleaned

def build_patient_json(row, sil_masc_b64, sil_fem_b64, telemed_paras, ekg_png_path):
    nombre = str(row.get('nombre', 'Paciente')).strip()
    if "lopez" in nombre or "Lopez" in nombre:
        nombre = nombre.replace("lopez", "López").replace("Lopez", "López")
    sex_raw = str(row.get('sexo', '')).strip().lower()
    es_masc = sex_raw in ['h', 'hombre', 'masculino']
    sexo_str = "Masculino" if es_masc else "Femenino"
    
    silueta_b64 = sil_masc_b64 if es_masc else sil_fem_b64
    
    id_paciente = str(row.get('RFC', row.get('id_usuario', 'SFI-2026'))).strip()
    if pd.isna(id_paciente) or id_paciente == 'nan':
        id_paciente = f"SFI-{row.get('id_usuario', '2026')}"
        
    folio = str(row.get('RFC', f"ORD-{row.get('id_usuario', '001')}")).strip()
    if pd.isna(folio) or folio == 'nan':
        folio = f"ORD-{row.get('id_usuario', '001')}"
        
    fecha_reg = str(row.get('fechaRegistro', '2026-08-04'))[:10]
    
    edad_val = row.get('Edad', row.get('Rango de edad', ''))
    try:
        edad = f"{int(float(edad_val))} Años" if float(edad_val) > 0 else "N/A"
    except:
        edad = "N/A"

    peso_raw = str(row.get('¿Cuánto pesas sin zapatos?', '')).strip()
    peso = re.sub(r'(?i)(kgs|kg|kilos)', '', peso_raw).strip()
    
    estatura_raw = str(row.get('¿Cuánto mides sin zapatos?', '')).strip()
    estatura = re.sub(r'(?i)(mts|m|metros)', '', estatura_raw).strip()
    
    telemed_paras = clean_telemed_content(telemed_paras, ekg_png_path)
    telemed_chunks = chunk_telemed_paras(telemed_paras, target_chars=3400)
    
    estado_civil = str(row.get('¿Cuál es tu estado civil?', 'No especificado')).strip()
    if pd.isna(estado_civil) or estado_civil == 'nan': estado_civil = 'No especificado'
    
    escolaridad = str(row.get('¿Cuál es tu nivel máximo de estudios alcanzado?', 'No especificado')).strip()
    if pd.isna(escolaridad) or escolaridad == 'nan': escolaridad = 'No especificado'
    
    puesto = str(row.get('Puesto a ocupar', row.get('Sede', 'Fuerza de Ventas Foráneos'))).strip()
    if pd.isna(puesto) or puesto == 'nan': puesto = 'Fuerza de Ventas Foráneos'
    
    extralaboral = str(row.get('Actividad Extralaboral', row.get('¿Cómo manejas tu estrés?', 'Actividad física'))).strip()
    if pd.isna(extralaboral) or extralaboral == 'nan': extralaboral = 'Actividad física'

    estudios = []
    alertas_clinicas = 0

    # 1. QUÍMICA DE 12 ELEMENTOS
    quimica_params = []
    quimica_mappings = [
        ("AST (TGO)", "16037:AST (TGO)", "U/L", 10.0, 40.0),
        ("Albúmina", "16012:Albúmina", "g/dL", 3.9, 5.1),
        ("LDH", "16115:LDH", "U/L", 135.0, 225.0),
        ("F. Alcalina total", "16084:F. Alcalina total", "U/L", 40.0, 130.0),
        ("Colesterol", "16060:Colesterol", "mg/dL", 0.0, 200.0),
        ("Urea", "16172:Urea", "mg/dL", 16.6, 48.5),
        ("Triglicéridos", "16170:Triglicéridos", "mg/dL", 0.0, 150.0),
        ("Glucosa", "16101:Glucosa", "mg/dL", 55.0, 99.0),
        ("Ácido úrico", "16010:Ácido úrico", "mg/dL", 3.4, 7.0 if es_masc else 6.0),
        ("Creatinina", "16070:Creatinina", "mg/dL", 0.7, 1.2 if es_masc else 1.1),
        ("Nitrógeno de urea en sangre (BUN)", "16134:Nitrógeno de urea en sangre (BUN)", "mg/dL", 16.6, 48.5),
        ("Calcio", "16050:Calcio", "mg/dL", 8.6, 10.0),
        ("Bilirrubina total", "16044:Bilirrubina total", "mg/dL", 0.0, 1.2)
    ]
    
    for name, col, unit, mn, mx in quimica_mappings:
        val = row.get(col)
        if pd.notna(val) and str(val).strip() not in ['', 'nan', '___']:
            try:
                fval = float(str(val).replace(',','.'))
                is_alert = (fval > mx or (mn > 0 and fval < mn))
                if is_alert: alertas_clinicas += 1
                det = "H-ALERT" if fval > mx else ("L-WARN" if mn > 0 and fval < mn else "NORM")
            except:
                det = "NORM"
            quimica_params.append({
                "nombre": name,
                "resultado": str(val),
                "unidad": unit,
                "min": str(mn),
                "max": str(mx),
                "formato": "num",
                "deteccion": det
            })
            
    if quimica_params:
        estudios.append({
            "titulo": "QUÍMICA DE 12 ELEMENTOS",
            "metodologia": "Química Clínica Automatizada",
            "parametros": quimica_params
        })

    # 2. BIOMETRÍA HEMÁTICA
    bh_params = []
    bh_mappings = [
        ("Ancho de Distrib. de Eritrocitos (SD)", "170022:Ancho de Distrib. de Eritrocitos (SD)", "10^6/uL", 4.5, 5.9),
        ("Conc. Media de Hemoglobina Corp.", "17107:Conc. Media de Hemoglobina Corp.", "pg", 27.0, 31.0),
        ("Ancho de Distrib. de Eritrocitos (CV)", "17108:Ancho de Distrib. de Eritrocitos (CV)", "10^6/uL", 4.5, 5.9),
        ("Linfocitos", "17117:Linfocitos", "-", "-", "-"),
        ("Neutrófilos", "17116:Neutrófilos", "-", "-", "-"),
        ("Leucocitos", "17101:Leucocitos", "10^3/uL", 4.5, 11.0),
        ("Volumen Corp. Medio", "17105:Volumen Corp. Medio", "-", "-", "-"),
        ("Basófilos", "17114:Basófilos", "-", "-", "-"),
        ("Eosinófilos", "17113:Eosinófilos", "-", "-", "-"),
        ("Hemoglobina", "17103:Hemoglobina", "g/dL", 13.5 if es_masc else 12.0, 17.5 if es_masc else 16.0),
        ("Hematócrito", "17104:Hematócrito", "%", 41.0 if es_masc else 37.0, 53.0 if es_masc else 48.0),
        ("Monocitos", "17118:Monocitos", "-", "-", "-"),
        ("Neutrófilos %", "17110:Neutrófilos", "-", "-", "-"),
        ("Linfocitos %", "17111:Linfocitos", "-", "-", "-"),
        ("Basófilos %", "17120:Basófilos", "-", "-", "-"),
        ("Plaquetas", "17109:Plaquetas", "10^3/uL", 150.0, 400.0),
        ("Monocitos %", "17112:Monocitos", "-", "-", "-"),
        ("Eosinófilos %", "17119:Eosinófilos", "-", "-", "-"),
        ("Hemoglobina Corp. Media", "17106:Hemoglobina Corp. Media", "pg", 27.0, 31.0),
        ("Volumen plaquetario medio", "170021:Volumen plaquetario medio", "-", "-", "-"),
        ("Eritrocitos", "17102:Eritrocitos", "10^6/uL", 4.5 if es_masc else 4.0, 5.9 if es_masc else 5.2)
    ]
    
    for name, col, unit, mn, mx in bh_mappings:
        val = row.get(col)
        if pd.notna(val) and str(val).strip() not in ['', 'nan', '___']:
            try:
                fval = float(str(val).replace(',','.'))
                fmn = float(mn) if mn != '-' else -999
                fmx = float(mx) if mx != '-' else 99999
                is_alert = (fval > fmx or (fmn > 0 and fval < fmn))
                if is_alert: alertas_clinicas += 1
                det = "H-ALERT" if fval > fmx else ("L-WARN" if fmn > 0 and fval < fmn else "NORM")
            except:
                det = "NORM"
            bh_params.append({
                "nombre": name,
                "resultado": str(val),
                "unidad": unit,
                "min": str(mn),
                "max": str(mx),
                "formato": "num" if mn != '-' else "text",
                "deteccion": det
            })

    if bh_params:
        if len(bh_params) > 13:
            estudios.append({
                "titulo": "BIOMETRÍA HEMÁTICA (1/2)",
                "metodologia": "Citometría Automatizada",
                "parametros": bh_params[:13]
            })
            estudios.append({
                "titulo": "BIOMETRÍA HEMÁTICA (2/2)",
                "metodologia": "Citometría Automatizada",
                "parametros": bh_params[13:]
            })
        else:
            estudios.append({
                "titulo": "BIOMETRÍA HEMÁTICA",
                "metodologia": "Citometría Automatizada",
                "parametros": bh_params
            })

    # 3. ANTÍGENO PROSTÁTICO (PSA)
    if es_masc and pd.notna(row.get('22012:Antígeno Prostático Específico Total')):
        psa_val = row.get('22012:Antígeno Prostático Específico Total')
        try:
            fpsa = float(str(psa_val).replace(',','.'))
            if fpsa > 4.0: alertas_clinicas += 1
            det = "H-ALERT" if fpsa > 4.0 else "NORM"
        except:
            det = "NORM"
        estudios.append({
            "titulo": "ANTÍGENO PROSTÁTICO ESPECÍFICO TOTAL EN SUERO",
            "metodologia": "Laboratorio Clínico Quimioluminiscencia",
            "parametros": [{
                "nombre": "Antígeno Prostático Específico Total",
                "resultado": str(psa_val),
                "unidad": "ng/mL",
                "min": "0.0",
                "max": "4.0",
                "formato": "num",
                "deteccion": det
            }]
        })

    # 4. EXAMEN GENERAL DE ORINA (EGO)
    ego_params = []
    ego_mappings = [
        ("Eritrocitos dismórficos", "23780:Eritrocitos dismórficos"),
        ("Eritrocitos", "2378:Eritrocitos"),
        ("Cetonas", "2372:Cetonas"),
        ("Células Tubulares Renales", "2384:Células Tubulares Renales"),
        ("Células de transición", "230061:Células de transición"),
        ("Cristales", "2381:Cristales"),
        ("pH", "2367:pH"),
        ("Aspecto", "2363:Aspecto"),
        ("Esterasa leucocitaria", "2368:Esterasa leucocitaria"),
        ("Densidad", "2366:Densidad"),
        ("Redes Mucoides", "2385:Redes Mucoides"),
        ("Color", "2361:Color"),
        ("Bilirrubina", "2373:Bilirrubina"),
        ("Cilindros", "2379:Cilindros"),
        ("Células Pavimentosas", "2383:Células Pavimentosas"),
        ("Glucosa", "2371:Glucosa"),
        ("Nitritos", "2369:Nitritos"),
        ("Proteínas", "2370:Proteínas"),
        ("Hemoglobina", "2375:Hemoglobina"),
        ("Bacterias", "2386:Bacterias"),
        ("Urobilinógeno", "2374:Urobilinógeno"),
        ("Levaduras", "2303219:Levaduras"),
        ("Leucocitos", "2377:Leucocitos")
    ]
    
    for name, col in ego_mappings:
        val = row.get(col)
        if pd.notna(val) and str(val).strip() not in ['', 'nan', '___']:
            val_str = str(val).strip()
            det = "NORM"
            if any(w in val_str.upper() for w in ['MODERAD', 'ABUNDANT', 'POSITIV', 'H-ALERT']) and val_str.upper() != 'NEGATIVO':
                det = "ALERT"
                alertas_clinicas += 1
            ego_params.append({
                "nombre": name,
                "resultado": val_str,
                "unidad": "-",
                "min": "-",
                "max": "-",
                "formato": "text",
                "deteccion": det
            })

    if ego_params:
        if len(ego_params) > 13:
            estudios.append({
                "titulo": "EXAMEN GENERAL DE ORINA (1/2)",
                "metodologia": "Laboratorio Clínico Uroanálisis",
                "parametros": ego_params[:13]
            })
            estudios.append({
                "titulo": "EXAMEN GENERAL DE ORINA (2/2)",
                "metodologia": "Laboratorio Clínico Uroanálisis",
                "parametros": ego_params[13:]
            })
        else:
            estudios.append({
                "titulo": "EXAMEN GENERAL DE ORINA",
                "metodologia": "Laboratorio Clínico Uroanálisis",
                "parametros": ego_params
            })

    # Images & EKG
    imagenes = {}
    ekg_b64 = get_base64_image(ekg_png_path)
    if ekg_b64:
        imagenes["electrocardiograma"] = ekg_b64

    paciente_obj = {
        "nombre": nombre,
        "sexo": sexo_str,
        "sexo_display": sexo_str,
        "edad": edad,
        "id_paciente": id_paciente,
        "folio": folio,
        "medico": "Dr. Damián Guzmán (Céd. 6656442)",
        "unidad": "Med&Corp Sede Central",
        "fecha_toma": fecha_reg,
        "fecha_proc": fecha_reg,
        "peso": f"{peso} kg" if peso else "N/A",
        "estatura": f"{estatura} m" if estatura else "N/A",
        "compartir": str(row.get('Compartir', 'SI')).strip().upper(),
        "estado_civil": estado_civil,
        "escolaridad": escolaridad,
        "puesto": puesto,
        "actividad_extralaboral": extralaboral,
        "silueta_b64": silueta_b64,
        "telemedicina_chunks": telemed_chunks
    }

    return {
        "paciente": paciente_obj,
        "estudios": estudios,
        "imagenes": imagenes,
        "resumen": {
            "estudios_totales": len(estudios),
            "alertas_clinicas": alertas_clinicas,
            "diagnostico_general": "Favorable"
        }
    }

class ProgressBar:
    def __init__(self, total, prefix='', length=30, fill='=', print_end="\r"):
        self.total = total
        self.prefix = prefix
        self.length = length
        self.fill = fill
        self.print_end = print_end
        self.start_time = time.time()

    def update(self, iteration, current_patient=''):
        elapsed_time = time.time() - self.start_time
        percent = 100 * (iteration / float(self.total))
        filled_length = int(self.length * iteration // self.total)
        bar = self.fill * filled_length + '.' * (self.length - filled_length)
        if iteration > 0:
            speed = iteration / elapsed_time if elapsed_time > 0 else 0
            eta_seconds = (self.total - iteration) / speed if speed > 0 else 0
            eta_str = f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s" if eta_seconds > 60 else f"{eta_seconds:.1f}s"
        else:
            eta_str = "calc..."
        elapsed_str = f"{int(elapsed_time // 60)}m {int(elapsed_time % 60)}s"
        sys.stdout.write(f"\r{self.prefix} |{bar}| {percent:.1f}% | {iteration}/{self.total} | Tiempo: {elapsed_str} | ETA: {eta_str} | {current_patient[:25]:<25}")
        sys.stdout.flush()
        if iteration == self.total:
            sys.stdout.write("\n")
            sys.stdout.flush()

async def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    master_path = os.path.join(base_dir, "MASTER CONSOLIDADO OFICIAL.xlsx")
    pacientes_dir = os.path.join(base_dir, "ESTUDIOS INDIVIDUALES", "PACIENTES")
    telemed_dir = os.path.join(base_dir, "ESTUDIOS INDIVIDUALES", "TELEMEDICINA")
    template_path = os.path.join(base_dir, "template_checkup_final.html")
    out_dir = os.path.join(base_dir, "REPORTES FINALES")
    os.makedirs(out_dir, exist_ok=True)

    sil_masc_b64 = get_base64_image(os.path.join(base_dir, "silueta_masculina.png"))
    if not sil_masc_b64:
        sil_masc_b64 = get_base64_image(os.path.join(base_dir, "silueta_masc_cropped.png"))
        
    sil_fem_b64 = get_base64_image(os.path.join(base_dir, "silueta_femenina.png"))
    if not sil_fem_b64:
        sil_fem_b64 = get_base64_image(os.path.join(base_dir, "silueta_fem_cropped.png"))

    df = pd.read_excel(master_path, skiprows=5)
    print(f"Iniciando generación de reportes para {len(df)} pacientes del consolidado oficial...")

    with open(template_path, 'r', encoding='utf-8') as f:
        html_template = f.read()

    p_folders = {normalize_name(f): f for f in os.listdir(pacientes_dir) if os.path.isdir(os.path.join(pacientes_dir, f))}
    tele_files = os.listdir(telemed_dir) if os.path.exists(telemed_dir) else []

    filter_name = sys.argv[1].strip() if len(sys.argv) > 1 else None
    if filter_name:
        df = df[df['nombre'].str.contains(filter_name, case=False, na=False)]
        print(f"[FILTRO ACTIVO] Filtrado por '{filter_name}'. Pacientes a procesar: {len(df)}")

    pbar = ProgressBar(total=len(df), prefix='Generando PDFs', length=25)
    sem = asyncio.Semaphore(5)
    completed_count = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch()

        async def process_patient(index, row):
            nonlocal completed_count
            nombre = str(row.get('nombre', f'Paciente_{index}')).strip()
            norm_name = normalize_name(nombre)
            safe_name = "".join(c if c.isalnum() else "_" for c in nombre)
            pdf_filename = f"REPORTE_MEDCORP_{safe_name}.pdf"
            pdf_path = os.path.join(out_dir, pdf_filename)
            html_path = os.path.join(out_dir, f"REPORTE_MEDCORP_{safe_name}.html")

            matched_folder = p_folders.get(norm_name, None)
            if not matched_folder:
                for k, v in p_folders.items():
                    if norm_name in k or k in norm_name:
                        matched_folder = v
                        break

            docx_path = None
            ekg_png_path = None

            if matched_folder:
                f_dir = os.path.join(pacientes_dir, matched_folder)
                for f in os.listdir(f_dir):
                    if f.endswith('.docx'): docx_path = os.path.join(f_dir, f)
                    if '_EKG.png' in f: ekg_png_path = os.path.join(f_dir, f)

            if not docx_path:
                rfc = str(row.get('RFC', '')).strip()
                for f in tele_files:
                    if f.endswith('.docx') and (rfc in f or any(w in normalize_name(f) for w in norm_name.split() if len(w) > 4)):
                        docx_path = os.path.join(telemed_dir, f)
                        break

            telemed_paras = parse_docx_paragraphs(docx_path) if docx_path else []
            data_json = build_patient_json(row, sil_masc_b64, sil_fem_b64, telemed_paras, ekg_png_path)

            json_str = json.dumps(data_json, ensure_ascii=False, indent=2)
            html_injected = html_template.replace("const INCOMING_DATA = window.INCOMING_DATA || { paciente: {}, estudios: [], imagenes: {}, resumen: {} };", f"const INCOMING_DATA = {json_str};")

            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_injected)

            async with sem:
                page = await browser.new_page()
                await page.goto(f"file:///{html_path}", wait_until="load")
                await page.pdf(
                    path=pdf_path,
                    format="A4",
                    print_background=True,
                    margin={"top": "0mm", "bottom": "0mm", "left": "0mm", "right": "0mm"}
                )
                await page.close()

            completed_count += 1
            pbar.update(completed_count, nombre)

        tasks = [process_patient(i, row) for i, row in df.iterrows()]
        await asyncio.gather(*tasks)
        await browser.close()

    print("\n¡Proceso de generación de reportes PDF finalizado con éxito total!")

if __name__ == "__main__":
    asyncio.run(main())
