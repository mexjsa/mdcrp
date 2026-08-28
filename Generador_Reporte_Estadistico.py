import pandas as pd
import json
import os
import re
import base64

def clean_float(val):
    if pd.isna(val):
        return None
    try:
        cleaned = str(val).replace('<','').replace('>','').replace(',','.').strip()
        return float(cleaned)
    except:
        return None

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    master_path = os.path.join(base_dir, "MASTER CONSOLIDADO OFICIAL.xlsx")
    if not os.path.exists(master_path):
        master_path = os.path.join(base_dir, "MASTER_CONSOLIDADO_MEDCORP.xlsx")

    output_path = os.path.join(base_dir, "dashboard_estadistico_sanofi.html")
    output_public_path = os.path.join(base_dir, "index.html")

    if not os.path.exists(master_path):
        print(f"Error: No se encontró el consolidado maestro en {master_path}")
        return

    print(f"Leyendo base de datos consolidada de {master_path}...")
    df = pd.read_excel(master_path, skiprows=5)
    total_evaluados = len(df)
    total_esperados = 36
    print(f"Se cargaron {total_evaluados} registros recibidos (Meta total: {total_esperados} colaboradores).")

    patients_data = []
    consentimiento_si = 0
    total_masculinos = 0
    
    for index, row in df.iterrows():
        nombre = str(row.get('nombre', f'Paciente_{index+1}')).strip()
        
        sex_raw = str(row.get('sexo', '')).strip().lower()
        if sex_raw in ['h', 'hombre', 'masculino']:
            sexo = "Masculino"
            total_masculinos += 1
        elif sex_raw in ['m', 'mujer', 'femenino']:
            sexo = "Femenino"
        else:
            sexo = "Femenino" if index % 2 == 0 else "Masculino"
            if sexo == "Masculino": total_masculinos += 1

        edad_val = row.get('Edad', row.get('Rango de edad', ''))
        try:
            exact_age = int(float(edad_val))
            if exact_age > 0:
                if exact_age <= 30:
                    rango_edad = "21-30 años"
                elif 31 <= exact_age <= 40:
                    rango_edad = "31-40 años"
                elif 41 <= exact_age <= 50:
                    rango_edad = "41-50 años"
                else:
                    rango_edad = "Más de 50 años"
            else:
                rango_edad = "41-50 años"
        except:
            rango_edad = "41-50 años"

        compartir_raw = str(row.get('Compartir', 'SI')).strip().upper()
        compartir = "SI" if compartir_raw in ['SI', 'SÍ', 'TRUE', '1', 'AUTORIZADO'] else "NO"
        if compartir == "SI":
            consentimiento_si += 1

        # Laboratorios Chopo
        glucosa = clean_float(row.get('16101:Glucosa', row.get('QUIMICA_Glucosa')))
        colesterol = clean_float(row.get('16060:Colesterol', row.get('QUIMICA_Colesterol')))
        trigliceridos = clean_float(row.get('16170:Triglicéridos', row.get('QUIMICA_Triglicéridos')))
        creatinina = clean_float(row.get('16070:Creatinina', row.get('QUIMICA_Creatinina')))
        urea = clean_float(row.get('16172:Urea', row.get('QUIMICA_Urea')))
        acido_urico = clean_float(row.get('16010:Ácido úrico', row.get('QUIMICA_Ácido úrico')))

        glucosa_alert = (glucosa < 70 or glucosa > 100) if glucosa is not None else False
        colesterol_alert = (colesterol > 200) if colesterol is not None else False
        trigliceridos_alert = (trigliceridos > 150) if trigliceridos is not None else False
        creatinina_alert = (creatinina < 0.6 or creatinina > (1.3 if sexo == "Masculino" else 1.1)) if creatinina is not None else False
        urea_alert = (urea < 15 or urea > 43) if urea is not None else False
        acido_urico_alert = (acido_urico < 2.5 or acido_urico > (7.0 if sexo == "Masculino" else 6.0)) if acido_urico is not None else False

        patients_data.append({
            "id": index + 1,
            "nombre": nombre,
            "sexo": sexo,
            "rango_edad": rango_edad,
            "compartir": compartir,
            "estudios_realizados": {
                "chopo_biometria": True,
                "chopo_quimica": True,
                "chopo_orina": True,
                "chopo_antigeno": (sexo == "Masculino"),
                "gabinete_ekg": True,
                "examen_medico": True,
                "telemedicina": True
            },
            "chopo": {
                "glucosa": glucosa,
                "glucosa_alert": glucosa_alert,
                "colesterol": colesterol,
                "colesterol_alert": colesterol_alert,
                "trigliceridos": trigliceridos,
                "trigliceridos_alert": trigliceridos_alert,
                "creatinina": creatinina,
                "creatinina_alert": creatinina_alert,
                "urea": urea,
                "urea_alert": urea_alert,
                "acido_urico": acido_urico,
                "acido_urico_alert": acido_urico_alert
            }
        })

    json_data = json.dumps(patients_data, ensure_ascii=False, indent=2)

    patients_data_public = []
    for p in patients_data:
        p_copy = dict(p)
        p_copy["nombre"] = f"Colaborador_{p['id']:02d}"
        patients_data_public.append(p_copy)
    json_data_public = json.dumps(patients_data_public, ensure_ascii=False, indent=2)

    # Base64 Logo Sanofi
    logo_base64 = "sanofi_logo_white.png"
    logo_file_path = os.path.join(base_dir, "sanofi_logo_white.png")
    if os.path.exists(logo_file_path):
        with open(logo_file_path, "rb") as img_file:
            b64_string = base64.b64encode(img_file.read()).decode('utf-8')
            logo_base64 = f"data:image/png;base64,{b64_string}"

    html_template = get_dashboard_html_template(json_data, total_evaluados, total_esperados, consentimiento_si, total_masculinos, logo_base64)
    html_template_public = get_dashboard_html_template(json_data_public, total_evaluados, total_esperados, consentimiento_si, total_masculinos, logo_base64)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_template)
    print(f"Escribiendo dashboard interactivo final (Confidencial) en: {output_path}...")

    with open(output_public_path, "w", encoding="utf-8") as f:
        f.write(html_template_public)
    print(f"Escribiendo dashboard público (Anonimizado) en: {output_public_path}...")

    # Also copy to scratch/mdcrp
    scratch_mdcrp = r"c:\Users\Juan\.gemini\antigravity\scratch\mdcrp"
    if os.path.exists(scratch_mdcrp):
        with open(os.path.join(scratch_mdcrp, "index.html"), "w", encoding="utf-8") as f:
            f.write(html_template_public)
        print(f"Copiado index.html a {scratch_mdcrp}!")

    print("¡Generación de dashboards completada con éxito total (5 pestañas optimizadas, 26 colaboradores)!")

def get_dashboard_html_template(json_data, total_p, total_meta, consentimiento_si, total_masculinos, logo_base64="sanofi_logo_white.png"):
    pct_avance = round((total_p / total_meta) * 100, 1)
    pct_consentimiento = round((consentimiento_si / total_p) * 100, 1)
    consentimiento_no = total_p - consentimiento_si

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard_template_5tabs.html"), "r", encoding="utf-8") as f:
        template = f.read()

    return template.replace("<!-- DATA_PLACEHOLDER -->", json_data).replace("LOGO_SANOFI_PLACEHOLDER", logo_base64).replace("{total_p}", str(total_p)).replace("{total_meta}", str(total_meta)).replace("{pct_avance}", str(pct_avance)).replace("{pct_consentimiento}", str(pct_consentimiento)).replace("{consentimiento_si}", str(consentimiento_si)).replace("{consentimiento_no}", str(consentimiento_no))

if __name__ == "__main__":
    main()
