import pandas as pd
import json
import os
import asyncio
import base64
import re
import sys
import time
from playwright.async_api import async_playwright
import unicodedata
from docx import Document
from docx.oxml.ns import qn

def normalize_name(text):
    if not isinstance(text, str):
        return ""
    text = text.upper()
    nfd_form = unicodedata.normalize('NFD', text)
    text = "".join([c for c in nfd_form if not unicodedata.combining(c)])
    text = re.sub(r'[^A-Z0-9]', ' ', text)
    return " ".join(text.split())

manual_mappings = {
    "AIDE ANGELICA BARRAGAN VAZQUEZ": "AIDEE ANGELICA BARRAGAN VAZQUEZ",
    "ALEJANDRO ANGEL CALDERON VERGES": "ALEJANDRO ANGEL CALDERON BERGES",
    "ALFONSO MENDEZ ORTIZ": "ALFONSO MENDES ORTIZ",
    "ANTONIO MARQUE RODRIGUEZ": "ANTONIO MARQUEZ RODRIGUEZ",
    "BRENDA GONZALEZ GUADAMARRA": "BRENDA GONZALEZ GUADARRAMA",
    "CARLOS AARON ROSAS GONZALESZ": "CARLOS AARON ROSAS GONZALEZ",
    "CINTHYA AGUILAR MOLINA": "CINTHYA AGUILAR LOPEZ",
    "CLAUDIA NATALIA ESPINOZA MUNIZ": "CLAUDIA NATALIA ESPINOSA MUNIZ",
    "DANIEL GREGORY LOPEZ RODRIGUEZ": "DANIEL GREGOY LOPEZ RODRIGUEZ",
    "EDER MANUEL SEVANTES GALVAN": "EDER MANUEL CERVANTES GALVAN",
    "EDNA MARINA INIGUEZ SANCHEZ": "EDNA INIGUEZ SANCHEZ",
    "ELSA KATHERIN CASTELLANOS": "ELSA KATHERINE CASTELLANOS MERCADO",
    "EMMANUEL CERO SANCHEZ": "EMMANUEL CERON SANCHEZ",
    "FERNANDO DANIEL MENDEZ": "FERNANDO DANIEL MENDEZ REYNOSO",
    "FERNAND ROMERO GUSMAN": "FERNANDO ROMERO GUZMAN",
    "GUILLERMO MUNIZ PONCE LEON": "GUILLERMO MUNIZ PONCE DE LEON",
    "JESUS AYALA VELAZCO": "JESUS AYALA VELASCO",
    "JUAN CARLOS WATKINS VAZQUEZ": "JUAN CARLOS WATKINS VAZQUEZ DEL MERCADO",
    "JULIANA NORMA CARBAJA LEON": "JULIANA NORMA CARBAJAL LEON",
    "JULIA ANA MARCELINO RAMOS": "JULIA ANA MARCELINO",
    "JULIETA LARROSA CALDERON": "JULIETA LARROSA",
    "KAREN SHARON PEREZ MENDOZA": "KEREN SHARON PEREZ MENDOZA",
    "KARLA BELEN GRAJEDA": "KARLA BELEN GRAJEDA PALOMINO",
    "KATIA IVONNE ORDAZ TALAMANTES": "KATIA IVONNE ORDOZ TALAMANTES",
    "LUIS MANUEL MORALES VALDEZ": "LUIS MANUEL MORALES VALDES",
    "MARIA FERNANDA MAGALLANE ALATORRE": "MARIA FERNANDA MAGALLANES ALATORRE",
    "MARIA FERNANDA VICARIO RUIZ": "MARIA FERNANDA VICARIO RUIZ DE SANTIAGO",
    "MONTCERRAT ALVAREZ PATINO": "MONTCERRAT ALVAREZ",
    "NADIA MARCELA RAMIREZ MUNGUIA": "NADIA MARCELA RAMIREZ MUNGIA",
    "NAHUM RODRIGUEZ BASTIDA": "NAHUM RODRIGUEZ",
    "OMAR HUESCA LOPEZ": "OMAR HUESCA GOMEZ",
    "RODRIGO MARTINEZ ESPINOZA": "RODRIGO MARTINEZ ESPINOSA",
    "SANDRA VIVIANA GALVAZ GONZALEZ": "SANDRA VIVIANA GALVAN GONZALEZ"
}

def split_telemed_docx(file_path):
    try:
        doc = Document(file_path)
    except Exception as e:
        print(f"Error cargando archivo docx {file_path}: {e}")
        return [], []
        
    page1_text = []
    page2_text = []
    on_page2 = False
    
    for p in doc.paragraphs:
        has_break = False
        p_element = p._p
        
        brs = p_element.findall('.//' + qn('w:br'))
        for br in brs:
            if br.get(qn('w:type')) == 'page':
                has_break = True
                break
                
        if not has_break:
            lrpbs = p_element.findall('.//' + qn('w:lastRenderedPageBreak'))
            if lrpbs:
                has_break = True
                
        if not has_break:
            sectPr = p_element.find('.//' + qn('w:sectPr'))
            if sectPr is not None:
                has_break = True
                
        if has_break:
            on_page2 = True
            
        text = p.text.strip()
        if text:
            page1_text.append(text)
                
    return page1_text, []

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
        
        # Calculate speed and ETA
        if iteration > 0:
            speed = iteration / elapsed_time if elapsed_time > 0 else 0
            eta_seconds = (self.total - iteration) / speed if speed > 0 else 0
            if eta_seconds > 60:
                eta_str = f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s"
            else:
                eta_str = f"{eta_seconds:.1f}s"
        else:
            eta_str = "calc..."
            
        elapsed_str = f"{int(elapsed_time // 60)}m {int(elapsed_time % 60)}s"
        
        # Clear line and write beautifully (limit patient name to 25 chars to prevent line wraps on narrow screens)
        sys.stdout.write(f"\r{self.prefix} |{bar}| {percent:.1f}% | {iteration}/{self.total} | Tiempo: {elapsed_str} | ETA: {eta_str} | {current_patient[:25]:<25}")
        sys.stdout.flush()
        if iteration == self.total:
            sys.stdout.write("\n")
            sys.stdout.flush()

async def generate_pdf(page, html_content, output_path):
    await page.set_content(html_content, wait_until='load', timeout=60000)
    
    await page.evaluate("""
        async () => {
            const images = Array.from(document.querySelectorAll('img'));
            await Promise.all(images.map(img => {
                if (img.complete) return;
                return new Promise((resolve, reject) => {
                    img.addEventListener('load', resolve);
                    img.addEventListener('error', reject);
                });
            }));
        }
    """)
    
    await page.wait_for_timeout(300)
    
    try:
        await page.pdf(
            path=output_path,
            format="A4",
            print_background=True,
            margin={'top': '0mm', 'right': '0mm', 'bottom': '0mm', 'left': '0mm'}
        )
    except Exception as e:
        print(f"Error guardando {output_path}: {e}")


def get_base64_image(path):
    try:
        if not os.path.exists(path): return None
        with open(path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            ext = path.split('.')[-1].lower()
            mime = "image/jpeg" if ext in ['jpg', 'jpeg'] else "image/png"
            return f"data:{mime};base64,{encoded_string}"
    except Exception as e:
        return None

def clean_chopo_col_name(col):
    if ':' in col:
        return col.split(':', 1)[1].strip()
    return col.replace('CHOPO_', '').strip()

def clean_inbody_col_name(col):
    name = col.replace('INBODY_', '')
    name = re.sub(r'^\d+\.\s*', '', name)
    return name.strip()

def build_patient_data(row, sil_fem_b64, sil_masc_b64, df_chopo_vert=None, telemed_info=None):
    alertas_clinicas = 0
    
    diagnostico_general = "Paciente presenta parámetros metabólicos dentro de rangos esperados. Se recomienda mantener hidratación adecuada y actividad física regular."
    hallazgos_rec = []
    if telemed_info:
        if telemed_info.get("evaluaciones_medicas"):
            diagnostico_general = "\n\n".join(telemed_info["evaluaciones_medicas"])
        hallazgos_rec = telemed_info.get("hallazgos_recomendaciones", [])

    is_male = str(row.get('sexo', '')).lower() in ['m', 'h', 'hombre', 'masculino']
    paciente = {
        "nombre": str(row.get('nombre', 'N/A')),
        "sexo": str(row.get('sexo', 'N/A')).lower(),
        "sexo_display": "Masculino" if is_male else "Femenino",
        "edad": str(row.get('Rango de edad', 'N/A')),
        "id_paciente": str(row.get('id_usuario', 'N/A')),
        "fecha_toma": str(row.get('fechaRegistro', 'N/A')),
        "unidad": str(row.get('Sede', 'Med&Corp Sede Central')),
        "puesto": str(row.get('Puesto', 'Personal Operativo')),
        "folio": str(row.get('CHOPO_Folio', row.get('CHOPO_Orden', 'ORD-2026-9938122'))),
        "medico": "Dr. Damián Guzmán (Céd. 6656442)",
        "estado_civil": str(row.get('Estado civil', 'N/A')),
        "escolaridad": str(row.get('Escolaridad', 'N/A')),
        "actividad_extra": str(row.get('Actividad extralaboral', 'N/A')),
        "compartir": "SÍ" if str(row.get('Compartir', 'NO')).strip().upper().startswith('SI') else "NO",
        "silueta_b64": sil_masc_b64 if is_male else sil_fem_b64,
        "hallazgos_recomendaciones": hallazgos_rec
    }
    
    def clean_val(v, unit):
        if pd.isna(v) or str(v).lower() == 'nan' or str(v).strip() == '': return '-'
        s = str(v).strip()
        s = re.sub(r'(?i)(kgs|kg|mts|m|metros|kilos)', '', s).strip()
        return f"{s} {unit}"

    paciente['peso'] = clean_val(row.get('INBODY_10. Peso', row.get('¿Cuánto pesas sin zapatos?', '-')), 'kg')
    paciente['estatura'] = clean_val(row.get('¿Cuánto mides sin zapatos?', '-'), 'm')

    estudios = []
    
    # ESPIROMETRIA
    if 'ESPIROMETRIA_FVC [L]_Mejor' in row and pd.notna(row['ESPIROMETRIA_FVC [L]_Mejor']):
        espiro = {
            "titulo": "ESPIROMETRÍA (FUNCIÓN PULMONAR)",
            "metodologia": "Espirometría Computarizada ndd",
            "parametros": []
        }
        for name, col_res, col_min, col_max, unit in [
            ("FVC [L]", 'ESPIROMETRIA_FVC [L]_Mejor', 'ESPIROMETRIA_FVC [L]_LLN', 'ESPIROMETRIA_FVC [L]_Pred', "L"),
            ("FEV1 [L]", 'ESPIROMETRIA_FEV1 [L]_Mejor', 'ESPIROMETRIA_FEV1 [L]_LLN', 'ESPIROMETRIA_FEV1 [L]_Pred', "L"),
            ("FEV1/FVC [%]", 'ESPIROMETRIA_FEV1/FVC [%]_Mejor', 'ESPIROMETRIA_FEV1/FVC [%]_LLN', 'ESPIROMETRIA_FEV1/FVC [%]_Pred', "%"),
            ("PEF [L/s]", 'ESPIROMETRIA_PEF [L/s]_Mejor', 'ESPIROMETRIA_PEF [L/s]_LLN', 'ESPIROMETRIA_PEF [L/s]_Pred', "L/s"),
            ("FEF25-75% [L/s]", 'ESPIROMETRIA_FEF25-75% [L/s]_Mejor', 'ESPIROMETRIA_FEF25-75% [L/s]_LLN', 'ESPIROMETRIA_FEF25-75% [L/s]_Pred', "L/s")
        ]:
            val = row.get(col_res, '')
            mi = row.get(col_min, '')
            ma = row.get(col_max, '')
            if pd.notna(val):
                try:
                    fval = float(str(val).replace(',','.'))
                    fmin = float(str(mi).replace(',','.'))
                    fmax = float(str(ma).replace(',','.'))
                    if fval < fmin or fval > fmax: alertas_clinicas += 1
                except: pass
                espiro['parametros'].append({"nombre": name, "resultado": val, "unidad": unit, "min": mi, "max": ma, "formato": "num"})
        estudios.append(espiro)
        
    # CHOPO (Vertical representation if df_chopo_vert is available, fallback to wide format otherwise)
    sanofi_to_chopo_mapping = {
        'JAMA860901': 'MARJ860901', # Julia Ana Marcelino Ramos
        'AAPM891031': 'ALPM891031', # Montcerrat Alvarez Patiño
        'GOXA690613': 'ANSA690613', # Alusio Andrade Sin Apellido
        'ROBN820829': 'ROSN820829', # Nahum Rodriguez Sin Apellido
        'DEVD841129': 'ISDD841129', # David Issac Delgado
        'NMRM760609': 'RAMN760609'  # Nadia Marcela Munguia
    }
    
    chopo_matched = False
    if df_chopo_vert is not None:
        p10_key = str(row.get('p10', '')).strip().upper()
        chopo_key = sanofi_to_chopo_mapping.get(p10_key, p10_key)
        df_pat_chopo = df_chopo_vert[df_chopo_vert['P10'] == chopo_key]
        if not df_pat_chopo.empty:
            params_chopo = []
            for _, ch_row in df_pat_chopo.iterrows():
                # Safety column lookup by index position:
                # 15: Analito, 16: Límite analito, 17: Resultado, 18: Estándar de resultado
                analyte = ch_row.iloc[15] if len(ch_row) > 15 else None
                lim = ch_row.iloc[16] if len(ch_row) > 16 else None
                res = ch_row.iloc[17] if len(ch_row) > 17 else None
                estandar = ch_row.iloc[18] if len(ch_row) > 18 else None
                
                if pd.isna(analyte) or pd.isna(res) or str(res).strip() in ['', '___']:
                    continue
                    
                analyte_str = str(analyte).strip()
                res_str = str(res).strip()
                lim_str = str(lim).strip() if pd.notna(lim) else '-'
                estandar_str = str(estandar).strip().upper() if pd.notna(estandar) else 'NORMAL'
                
                # Exclude any headers/empty rows
                if res_str == '___' or (analyte_str.isupper() and pd.isna(lim)):
                    continue
                
                is_alert = estandar_str not in ['NORMAL', 'NORMAL_TEXT', 'NORMAL_NUM', '']
                if is_alert:
                    alertas_clinicas += 1
                
                params_chopo.append({
                    "nombre": analyte_str,
                    "resultado": res_str,
                    "unidad": "",
                    "min": "-",
                    "max": "-",
                    "formato": "text",
                    "estado": estandar_str,
                    "is_alert": is_alert,
                    "rango_referencia": lim_str
                })
            if params_chopo:
                estudios.append({
                    "titulo": "LABORATORIOS CLÍNICOS (QUÍMICA Y BIOMETRÍA)",
                    "metodologia": "Automatizado / Espectrofotometría",
                    "parametros": params_chopo
                })
                chopo_matched = True

    if not chopo_matched:
        # Fallback to old wide format logic with new prefixes
        groups = {
            "QUÍMICA DE 12 ELEMENTOS": "QUIMICA_",
            "BIOMETRÍA HEMÁTICA": "BH_",
            "ANTÍGENO PROSTÁTICO ESPECÍFICO TOTAL EN SUERO": "PSA_",
            "EXAMEN GENERAL DE ORINA": "EGO_"
        }
        for title, prefix in groups.items():
            cols = [c for c in row.index if c.startswith(prefix) and pd.notna(row[c])]
            exclude = ['Folio', 'Orden', 'Gnero', 'Edad', 'Fecha', 'Nombre']
            cols = [c for c in cols if not any(x in c for x in exclude)]
            
            if cols:
                params_group = []
                for col in cols:
                    val = row[col]
                    name = col.replace(prefix, '').strip()
                    mi, ma, unit = '-', '-', ''
                    uname = name.upper()
                    
                    # Assign limits based on LABS
                    if 'GLUCOSA' in uname: unit, mi, ma = 'mg/dL', 55, 99
                    elif 'UREA' in uname: unit, mi, ma = 'mg/dL', 16.6, 48.5
                    elif 'BUN' in uname or 'NITR' in uname: unit, mi, ma = 'mg/dL', 6, 20
                    elif 'CREATININA' in uname: unit, mi, ma = 'mg/dL', 0.70, 1.2
                    elif 'RICO' in uname: unit, mi, ma = 'mg/dL', 3.4, 7.0
                    elif 'COLESTEROL' in uname: unit, mi, ma = 'mg/dL', 0, 200
                    elif 'TRIGLIC' in uname: unit, mi, ma = 'mg/dL', 0, 150
                    elif 'ALB' in uname: unit, mi, ma = 'g/dL', 3.9, 5.1
                    elif 'BILIRRUBINA' in uname: unit, mi, ma = 'mg/dL', 0, 1.2
                    elif 'AST' in uname or 'TGO' in uname: unit, mi, ma = 'U/L', 0, 40
                    elif 'ALCALINA' in uname: unit, mi, ma = 'U/L', 40, 130
                    elif 'LDH' in uname: unit, mi, ma = 'U/L', 135, 225
                    elif 'CALCIO' in uname: unit, mi, ma = 'mg/dL', 8.6, 10.0
                    elif 'HEMOGLOBINA CORP' in uname: unit, mi, ma = 'pg', 27, 31
                    elif 'HEMOGLOBINA' in uname: unit, mi, ma = 'g/dL', 13.5, 17.5
                    elif 'HEMAT' in uname: unit, mi, ma = '%', 41, 53
                    elif 'LEUCOCITOS' in uname: unit, mi, ma = '10^3/uL', 4.5, 11.0
                    elif 'ERITROCITOS' in uname and 'DISM' not in uname: unit, mi, ma = '10^6/uL', 4.5, 5.9
                    elif 'PLAQUETAS' in uname: unit, mi, ma = '10^3/uL', 150, 400
                    elif 'PROST' in uname: unit, mi, ma = 'ng/mL', 0, 4.0
                    
                    is_alert = False
                    if mi != '-':
                        try:
                            fval = float(str(val).replace('<','').replace('>','').replace(',','.').strip())
                            if fval < float(mi) or fval > float(ma):
                                alertas_clinicas += 1
                                is_alert = True
                        except: pass
                    params_group.append({
                        "nombre": name,
                        "resultado": str(val),
                        "unidad": unit,
                        "min": mi,
                        "max": ma,
                        "formato": "num" if mi != '-' else "text",
                        "is_alert": is_alert
                    })
                estudios.append({
                    "titulo": title,
                    "metodologia": "Química Clínica automatizada" if "QUÍMICA" in title else ("Citometría" if "BIOMETRÍA" in title else "Laboratorio Clínico"),
                    "parametros": params_group
                })

    # INBODY removido a petición del usuario.

    imagenes = {}

    if 'ODONTOGRAMA_Recomendaciones_Dentales' in row and pd.notna(row['ODONTOGRAMA_Recomendaciones_Dentales']):
        imagenes['odontograma_recomendaciones'] = str(row['ODONTOGRAMA_Recomendaciones_Dentales'])

    # Calcular recuento de dientes y padecimientos
    sanos = 0
    atencion = 0
    padecimientos_map = {}
    
    # Columnas de dientes permanentes p11 a p48 para el conteo de semáforo
    tooth_cols = [c for c in row.index if re.match(r'ODONTOGRAMA_p\d{2}', c)]
    for col in tooth_cols:
        val = row[col]
        if pd.notna(val):
            try:
                fval = float(str(val).replace(',','.').strip())
                if fval == 0.0: sanos += 1
                elif fval == 1.0: atencion += 1
            except: pass
            
    # Extraer padecimientos de las columnas de texto
    text_cols = [c for c in row.index if 'ODONTOGRAMA_' in c and ('SUP' in c or 'INF' in c)]
    for col in text_cols:
        val = str(row[col]).upper().strip()
        if val not in ['SANO', 'OBTURACION S/CARIES', 'OBTURADO S/CARIES', 'OBTURACIN S/CARIES', 'NAN', '']:
            # Normalizar nombres comunes
            if 'CARIES' in val: val = 'Caries'
            elif 'CORONA' in val: val = 'Corona'
            elif 'PERDIDO' in val: val = 'Perdido'
            elif 'RADICULAR' in val: val = 'Resto Radicular'
            
            padecimientos_map[val] = padecimientos_map.get(val, 0) + 1
            
    # Formatear detalle: "2 Caries, 1 Corona"
    detalle_str = ""
    if padecimientos_map:
        parts = [f"{count} {name}" for name, count in padecimientos_map.items()]
        detalle_str = "(" + ", ".join(parts) + ")"
    
    imagenes['odontograma_sanos'] = sanos
    imagenes['odontograma_atencion'] = atencion
    imagenes['odontograma_detalle'] = detalle_str

    if 'ODONTOGRAMA_Imagen_Path' in row and pd.notna(row['ODONTOGRAMA_Imagen_Path']) and str(row['ODONTOGRAMA_Imagen_Path']).strip() != '':
        path = str(row['ODONTOGRAMA_Imagen_Path']).strip()
        b64 = get_base64_image(path)
        if b64: imagenes['odontograma'] = b64
        
    if 'ELECTROCARDIOGRAMA_Imagen_Path' in row and pd.notna(row['ELECTROCARDIOGRAMA_Imagen_Path']) and str(row['ELECTROCARDIOGRAMA_Imagen_Path']).strip() != '':
        path = str(row['ELECTROCARDIOGRAMA_Imagen_Path']).strip()
        b64 = get_base64_image(path)
        if b64: imagenes['electrocardiograma'] = b64

    if 'ESPIROMETRIA_Imagen_Path' in row and pd.notna(row['ESPIROMETRIA_Imagen_Path']) and str(row['ESPIROMETRIA_Imagen_Path']).strip() != '':
        path = str(row['ESPIROMETRIA_Imagen_Path']).strip()
        b64 = get_base64_image(path)
        if b64: imagenes['espirometria'] = b64

    return {
        "paciente": paciente,
        "estudios": estudios,
        "imagenes": imagenes,
        "resumen": {
            "estudios_totales": len(estudios),
            "alertas_clinicas": alertas_clinicas,
            "diagnostico_general": diagnostico_general
        }
    }

async def main():
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    master_path = os.path.join(base_dir, "MASTER_CONSOLIDADO_MEDCORP.xlsx")
    out_dir = os.path.join(base_dir, "REPORTES FINALES")
    
    sil_masc_path = os.path.join(os.path.dirname(base_dir), "silueta_masc_cropped.png")
    sil_fem_path = os.path.join(os.path.dirname(base_dir), "silueta_fem_cropped.png")
    
    os.makedirs(out_dir, exist_ok=True)
    
    sil_fem_b64 = get_base64_image(sil_fem_path)
    sil_masc_b64 = get_base64_image(sil_masc_path)
    df = pd.read_excel(master_path)
    
    # Soporte para filtrar pacientes por argumento de línea de comandos (ciclo de feedback rápido)
    filter_name = sys.argv[1].strip() if len(sys.argv) > 1 else None
    if filter_name:
        df = df[df['nombre'].str.contains(filter_name, case=False, na=False)]
        print(f"\n[FILTRO ACTIVO] Generando reportes únicamente para pacientes que coincidan con '{filter_name}'. Encontrados: {len(df)}")

    
    # Cargar concentrado vertical de CHOPO para obtener límites de analito y semaforización
    df_chopo_vert = None
    print("Omitiendo vertical de CHOPO. Usando formato wide desde el MASTER.")
    
    template_path = os.path.join(base_dir, "template_checkup_final.html")
    with open(template_path, 'r', encoding='utf-8') as f:
        html_template = f.read()

    # Cargar datos de valoracion medica si existen
    telemed_dir = os.path.join(base_dir, "ESTUDIOS INDIVIDUALES", "PACIENTES")
    telemed_data = {}
    if os.path.exists(telemed_dir):
        patient_folders = [d for d in os.listdir(telemed_dir) if os.path.isdir(os.path.join(telemed_dir, d))]
        print(f"\n[TELEMEDICINA] Procesando valoraciones médicas para {len(patient_folders)} pacientes...")
        for pf in patient_folders:
            pf_path = os.path.join(telemed_dir, pf)
            for f in os.listdir(pf_path):
                if f.endswith('.docx'):
                    norm_docx = normalize_name(pf)
                    mapped_norm = manual_mappings.get(norm_docx, norm_docx)
                    p1, p2 = split_telemed_docx(os.path.join(pf_path, f))
                    if p1 or p2:
                        telemed_data[mapped_norm] = {
                            "evaluaciones_medicas": p1,
                            "hallazgos_recomendaciones": p2
                        }
        print(f"[TELEMEDICINA] {len(telemed_data)} reportes vinculados con éxito.\n")

    print(f"Iniciando generación de {len(df)} reportes PDF con SILUETAS OFICIALES...")
    pbar = ProgressBar(total=len(df), prefix='Generando PDFs', length=25)
    
    sem = asyncio.Semaphore(5)  # Procesar hasta 5 reportes en paralelo para máxima velocidad y estabilidad
    completed_count = 0
    
    async def process_patient(index, row, browser):
        nonlocal completed_count
        nombre = str(row.get('nombre', f'Paciente_{index}'))
        
        safe_name = "".join(c if c.isalnum() else "_" for c in nombre)
        pdf_filename = f"REPORTE_MEDCORP_{safe_name}_V10.pdf" if filter_name else f"REPORTE_MEDCORP_{safe_name}.pdf"
        pdf_path = os.path.join(out_dir, pdf_filename)
        
        # Verificar consentimiento para compartir
        compartir = str(row.get('Compartir', 'SI')).strip().upper()
        if compartir == 'NO':
            print(f"\n[PRIVACIDAD] Omitiendo generación de reporte para '{nombre}' (Compartir = 'NO')")
            if os.path.exists(pdf_path):
                try:
                    os.remove(pdf_path)
                    print(f"  [LIMPIEZA] Eliminado reporte de privacidad omitida: {pdf_filename}")
                except Exception as e:
                    print(f"  [ERROR] No se pudo eliminar {pdf_filename}: {e}")
            completed_count += 1
            pbar.update(completed_count, f"Confidencial: {nombre}")
            return
            
        norm_paciente = normalize_name(nombre)
        telemed_info = telemed_data.get(norm_paciente, None)
        
        data_json = build_patient_data(row, sil_fem_b64, sil_masc_b64, df_chopo_vert, telemed_info)
        
        # Verificar si el paciente tiene algún tipo de datos clínicos o telemedicina
        estudios = data_json.get('estudios', [])
        imagenes = data_json.get('imagenes', {})
        has_clinical_data = (
            len(estudios) > 0 or
            imagenes.get('electrocardiograma') is not None or
            imagenes.get('electrocardiograma_datos') or
            imagenes.get('odontograma') is not None or
            imagenes.get('odontograma_recomendaciones') or
            telemed_info is not None
        )
        
        if not has_clinical_data:
            print(f"\n[SIN DATOS] Omitiendo generación de reporte para '{nombre}' (No tiene estudios ni telemedicina)")
            if os.path.exists(pdf_path):
                try:
                    os.remove(pdf_path)
                    print(f"  [LIMPIEZA] Eliminado reporte de paciente sin datos: {pdf_filename}")
                except Exception as e:
                    print(f"  [ERROR] No se pudo eliminar {pdf_filename}: {e}")
            completed_count += 1
            pbar.update(completed_count, f"Sin datos: {nombre}")
            return
            
        json_str = json.dumps(data_json)
        script_inject = f"<script>window.INCOMING_DATA = {json_str};</script>"
        html_final = html_template.replace("</head>", f"{script_inject}\n</head>")
        
        async with sem:
            page = await browser.new_page()
            await generate_pdf(page, html_final, pdf_path)
            await page.close()
            
        completed_count += 1
        pbar.update(completed_count, nombre)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--allow-file-access-from-files'])
        tasks = [process_patient(idx, row, browser) for idx, row in df.iterrows()]
        await asyncio.gather(*tasks)
        await browser.close()
        
    pbar.update(len(df), "¡Completado!")
    print("¡Generación Masiva Finalizada!")

    # Limpieza de base de datos final (solo en ejecución completa sin filtros)
    if not filter_name:
        try:
            print("\n[LIMPIEZA DE BASE DE DATOS] Removiendo columnas de soporte local del Excel consolidado final...")
            df_clean = pd.read_excel(master_path)
            cols_to_drop = ['ODONTOGRAMA_Imagen_Path', 'ELECTROCARDIOGRAMA_Imagen_Path', 'ESPIROMETRIA_Imagen_Path']
            existing_cols = [c for c in cols_to_drop if c in df_clean.columns]
            if existing_cols:
                df_clean = df_clean.drop(columns=existing_cols)
                df_clean.to_excel(master_path, index=False)
                print(f"  [ÉXITO] Columnas de soporte local eliminadas: {existing_cols}")
            else:
                print("  [INFO] No se encontraron columnas de soporte local por remover.")
        except Exception as e:
            print(f"  [ERROR] No se pudo limpiar el archivo Excel maestro: {e}")

if __name__ == "__main__":
    asyncio.run(main())
