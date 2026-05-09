import pandas as pd
import json
import os
import asyncio
import base64
import re
import sys
import time
from playwright.async_api import async_playwright

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
    await page.set_content(html_content, wait_until='networkidle')
    
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

def build_patient_data(row, silhouette_b64, df_chopo_vert=None):
    alertas_clinicas = 0
    
    paciente = {
        "nombre": str(row.get('nombre', 'N/A')),
        "sexo": str(row.get('sexo', 'N/A')).lower(),
        "sexo_display": "Masculino" if str(row.get('sexo', '')).lower() in ['h', 'hombre', 'masculino'] else "Femenino",
        "edad": str(row.get('Rango de edad', 'N/A')),
        "id_paciente": str(row.get('id_usuario', 'N/A')),
        "fecha_toma": str(row.get('fechaRegistro', 'N/A')),
        "unidad": str(row.get('Sede', 'Med&Corp Sede Central')),
        "puesto": str(row.get('Puesto', 'Personal Operativo')),
        "folio": str(row.get('CHOPO_Folio', row.get('CHOPO_Orden', 'ORD-2026-9938122'))),
        "medico": "Dr. Damián Guzmán (Céd. 6656442)",
        "compartir": "SÍ" if str(row.get('Compartir', 'NO')).strip().upper().startswith('SI') else "NO",
        "silueta_b64": silhouette_b64
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
        # Fallback to old wide format logic if vertical df is not provided or patient wasn't found
        chopo_cols = [c for c in row.index if c.startswith('CHOPO_') and pd.notna(row[c])]
        exclude = ['CHOPO_Folio', 'CHOPO_Orden', 'CHOPO_Gnero', 'CHOPO_Edad', 'CHOPO_Fecha de nacimiento', 'CHOPO_Nombre']
        chopo_cols = [c for c in chopo_cols if not any(x in c for x in exclude)]
        
        if chopo_cols:
            params_chopo = []
            for col in chopo_cols:
                val = row[col]
                name = clean_chopo_col_name(col)
                mi, ma, unit = '-', '-', ''
                if 'Glucosa' in name: unit, mi, ma = 'mg/dL', 70, 100
                elif 'Colesterol' in name: unit, mi, ma = 'mg/dL', 0, 200
                elif 'Triglic' in name: unit, mi, ma = 'mg/dL', 0, 150
                elif 'rico' in name: unit, mi, ma = 'mg/dL', 3.4, 7.0
                elif 'Creatinina' in name: unit, mi, ma = 'mg/dL', 0.7, 1.3
                is_alert = False
                if mi != '-':
                    try:
                        fval = float(str(val).replace('<','').replace('>','').replace(',','.').strip())
                        if fval < float(mi) or fval > float(ma):
                            alertas_clinicas += 1
                            is_alert = True
                    except: pass
                params_chopo.append({
                    "nombre": name,
                    "resultado": str(val),
                    "unidad": unit,
                    "min": mi,
                    "max": ma,
                    "formato": "num" if mi != '-' else "text",
                    "is_alert": is_alert
                })
            estudios.append({
                "titulo": "LABORATORIOS CLÍNICOS (QUÍMICA Y BIOMETRÍA)",
                "metodologia": "Automatizado / Espectrofotometría",
                "parametros": params_chopo
            })

    # INBODY
    inbody_cols = [c for c in row.index if c.startswith('INBODY_') and pd.notna(row[c])]
    exclude_ib = ['Fecha', 'Correo', 'ID', 'Tel', 'Celular', 'Gnero', 'Edad']
    inbody_cols = [c for c in inbody_cols if not any(x in c for x in exclude_ib)]
    if inbody_cols:
        params_inbody = []
        for col in inbody_cols:
            val = row[col]
            name = clean_inbody_col_name(col)
            unit = 'kg' if 'MASA' in name.upper() or 'PESO' in name.upper() else ''
            params_inbody.append({ "nombre": name, "resultado": str(val), "unidad": unit, "min": "-", "max": "-", "formato": "text" })
        estudios.append({
            "titulo": "ANÁLISIS DE COMPOSICIÓN CORPORAL (INBODY)",
            "metodologia": "Bioimpedancia Eléctrica",
            "parametros": params_inbody
        })

    imagenes = {}
    if 'ELECTROCARDIOGRAMA_Ritmo' in row and pd.notna(row['ELECTROCARDIOGRAMA_Ritmo']):
        ekg_data = []
        priority = ['Ritmo', 'Frecuencia', 'Eje_QRS', 'Onda_P', 'Intervalo_PR', 'Complejo_QRS', 'Segmento_ST', 'Onda_T', 'Intervalo_QTc', 'Precordiales']
        for key in priority:
            col = f'ELECTROCARDIOGRAMA_{key}'
            if col in row and pd.notna(row[col]):
                val = str(row[col])
                name = key.replace('_', ' ')
                unit = 'lpm' if 'Frecuencia' in key else 'grados' if 'Eje' in key else 'ms' if 'Intervalo' in key else ''
                if unit.lower() in val.lower(): unit = ''
                ekg_data.append({ "nombre": name, "resultado": val, "unidad": unit })
        imagenes['electrocardiograma_datos'] = ekg_data
        imagenes['electrocardiograma_conclusion'] = str(row.get('ELECTROCARDIOGRAMA_Conclusion', ''))
        imagenes['electrocardiograma_observaciones'] = str(row.get('ELECTROCARDIOGRAMA_Observaciones', ''))

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

    return {
        "paciente": paciente,
        "estudios": estudios,
        "imagenes": imagenes,
        "resumen": {
            "estudios_totales": len(estudios),
            "alertas_clinicas": alertas_clinicas,
            "diagnostico_general": "Paciente presenta parámetros metabólicos dentro de rangos esperados. Se recomienda mantener hidratación adecuada y actividad física regular."
        }
    }

async def main():
    base_dir = r"C:\Users\Juan\Dropbox\Proyectos 2026\Med&Corp\CheckUp"
    master_path = os.path.join(base_dir, "MASTER_CONSOLIDADO_MEDCORP.xlsx")
    out_dir = os.path.join(base_dir, "REPORTES FINALES")
    silhouette_path = r"C:\Users\Juan\Dropbox\Proyectos 2026\Med&Corp\Gemini_Generated_Image_x43khqx43khqx43k.png"
    os.makedirs(out_dir, exist_ok=True)
    
    silhouette_b64 = get_base64_image(silhouette_path)
    df = pd.read_excel(master_path)
    
    # Soporte para filtrar pacientes por argumento de línea de comandos (ciclo de feedback rápido)
    filter_name = sys.argv[1].strip() if len(sys.argv) > 1 else None
    if filter_name:
        df = df[df['nombre'].str.contains(filter_name, case=False, na=False)]
        print(f"\n[FILTRO ACTIVO] Generando reportes únicamente para pacientes que coincidan con '{filter_name}'. Encontrados: {len(df)}")

    
    # Cargar concentrado vertical de CHOPO para obtener límites de analito y semaforización
    chopo_vertical_path = os.path.join(base_dir, "ESTUDIOS AGREGADOS", "ESTUDIOS CHOPO", "ConcentradoResultados06052026_132057_18046_1_13775_060420AL060520.xlsx")
    print(f"Cargando límites y semáforos verticales de CHOPO desde: {os.path.basename(chopo_vertical_path)}")
    df_chopo_vert = pd.read_excel(chopo_vertical_path, header=3)
    
    template_path = os.path.join(base_dir, "template_checkup_final.html")
    with open(template_path, 'r', encoding='utf-8') as f:
        html_template = f.read()

    print(f"Iniciando generación de {len(df)} reportes PDF con SILUETAS OFICIALES...")
    pbar = ProgressBar(total=len(df), prefix='Generando PDFs', length=25)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--allow-file-access-from-files'])
        
        for index, row in df.iterrows():
            nombre = str(row.get('nombre', f'Paciente_{index}'))
            pbar.update(index, nombre)
            data_json = build_patient_data(row, silhouette_b64, df_chopo_vert)
            json_str = json.dumps(data_json)
            script_inject = f"<script>window.INCOMING_DATA = {json_str};</script>"
            html_final = html_template.replace("</head>", f"{script_inject}\n</head>")
            safe_name = "".join(c if c.isalnum() else "_" for c in nombre)
            pdf_filename = f"REPORTE_MEDCORP_{safe_name}_V2.pdf" if filter_name else f"REPORTE_MEDCORP_{safe_name}.pdf"
            pdf_path = os.path.join(out_dir, pdf_filename)
            
            page = await browser.new_page()
            await generate_pdf(page, html_final, pdf_path)
            await page.close()
            
        await browser.close()
        
    pbar.update(len(df), "¡Completado!")
    print("¡Generación Masiva Finalizada!")

if __name__ == "__main__":
    asyncio.run(main())
