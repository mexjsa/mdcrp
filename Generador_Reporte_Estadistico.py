import pandas as pd
import json
import os
import re

def clean_float(val):
    if pd.isna(val):
        return None
    try:
        cleaned = str(val).replace('<','').replace('>','').replace(',','.').strip()
        return float(cleaned)
    except:
        return None

def main():
    base_dir = r"C:\Users\Juan\Dropbox\Proyectos 2026\Med&Corp\CheckUp"
    master_path = os.path.join(base_dir, "MASTER_CONSOLIDADO_MEDCORP.xlsx")
    output_path = os.path.join(base_dir, "dashboard_estadistico_sanofi.html")
    
    if not os.path.exists(master_path):
        print(f"Error: No se encontró el consolidado maestro en {master_path}")
        return
        
    print(f"Leyendo base de datos consolidada de {master_path}...")
    df = pd.read_excel(master_path)
    print(f"Se cargaron {len(df)} registros.")

    # Columnas de odontograma (dientes permanentes p11 a p48)
    tooth_cols = [c for c in df.columns if re.match(r'ODONTOGRAMA_p\d{2}', c)]
    
    # Encontrar columnas dinámicamente antes del loop para mayor robustez ante codificaciones extrañas
    estres_col_name = next((c for c in df.columns if 'calificar' in c.lower() and 'estr' in c.lower()), None)
    sueno_col_name = next((c for c in df.columns if 'calidad' in c.lower() and 'sue' in c.lower()), None)
    sueno_hrs_col_name = next((c for c in df.columns if 'horas' in c.lower() and 'duermes' in c.lower()), None)
    fuma_col_name = next((c for c in df.columns if 'fumas?' in c.lower() or ('fumas' in c.lower() and len(c) < 10)), None)
    alcohol_col_name = next((c for c in df.columns if 'tomas alcohol' in c.lower()), None)

    # Columnas de Peso (CD a CF) y Alimentación (CG a CI)
    disposicion_peso_col = next((c for c in df.columns if 'disposici' in c.lower() and 'cambios' in c.lower() and 'peso' in c.lower()), None)
    confianza_peso_col = next((c for c in df.columns if 'confiado' in c.lower() and 'peso' in c.lower()), None)
    importancia_peso_col = next((c for c in df.columns if 'importante' in c.lower() and 'peso' in c.lower()), None)

    disposicion_alimentacion_col = next((c for c in df.columns if 'cambios' in c.lower() and 'alimentaci' in c.lower()), None)
    confianza_alimentacion_col = next((c for c in df.columns if 'confiado' in c.lower() and 'alimentaci' in c.lower()), None)
    importancia_alimentacion_col = next((c for c in df.columns if 'importante' in c.lower() and 'alimentaci' in c.lower()), None)

    # Columnas de Sueño (CP a CR)
    disposicion_sueno_col = next((c for c in df.columns if 'disposici' in c.lower() and 'sue' in c.lower()), None)
    confianza_sueno_col = next((c for c in df.columns if 'confiado' in c.lower() and 'sue' in c.lower()), None)
    importancia_sueno_col = next((c for c in df.columns if 'importante' in c.lower() and 'sue' in c.lower()), None)
    
    patients_data = []
    for index, row in df.iterrows():
        # 1. Demográficos
        nombre = str(row.get('nombre', f'Paciente_{index}')).strip()
        
        sex_raw = str(row.get('sexo', '')).strip().lower()
        if sex_raw in ['h', 'hombre', 'masculino']:
            sexo = "Masculino"
        elif sex_raw in ['m', 'mujer', 'femenino']:
            sexo = "Femenino"
        else:
            sexo = "Desconocido"
            
        age_raw = str(row.get('Rango de edad', '')).strip()
        if '21' in age_raw:
            rango_edad = "21-30 años"
        elif '31' in age_raw:
            rango_edad = "31-40 años"
        elif '41' in age_raw:
            rango_edad = "41-50 años"
        elif '50' in age_raw or 'más' in age_raw.lower() or 'mas' in age_raw.lower():
            rango_edad = "Más de 50 años"
        else:
            rango_edad = "Desconocido"

        # Área del paciente
        area_raw = row.get('Área')
        if pd.isna(area_raw):
            area = "Desconocido"
        else:
            area = str(area_raw).strip()
            # Limpiar codificaciones problemáticas
            area = area.replace('clnico', 'clínico').replace('cl\u00ednico', 'clínico').replace('cl&iacute;nico', 'clínico')
            area = area.replace('Mdico', 'Médico').replace('M\u00e9dico', 'Médico')
            area = area.replace('Gestin', 'Gestión').replace('Gesti\u00f3n', 'Gestión')
            area = area.replace('tecnologa', 'tecnología').replace('tecnolog\u00eda', 'tecnología')
            area = area.replace('Comunicacin', 'Comunicación').replace('Comunicaci\u00f3n', 'Comunicación')
            area = area.replace('publicos', 'públicos').replace('pblicos', 'públicos')
            if area == 'nan' or area == '':
                area = "Desconocido"

        # Consentimiento para compartir información (Compartir)
        compartir_raw = str(row.get('Compartir', 'NO')).strip().upper() if pd.notna(row.get('Compartir')) else "NO"
        compartir = "SI" if ('SI' in compartir_raw or 'S' in compartir_raw or 'SÍ' in compartir_raw) else "NO"

        # 2. InBody
        imc = clean_float(row.get('INBODY_15. IMC (índice de masa corporal)'))
        peso = clean_float(row.get('INBODY_10. Peso'))
        grasa = clean_float(row.get('INBODY_12. MASA GRASA '))
        musculo = clean_float(row.get('INBODY_14. MASA MUSCULOESQUELETICA'))
        agua = clean_float(row.get('INBODY_11. AGUA CORPORAL TOTAL '))

        # 3. Chopo (Laboratorios)
        glucosa = clean_float(row.get('CHOPO_16101:Glucosa'))
        colesterol = clean_float(row.get('CHOPO_16060:Colesterol'))
        trigliceridos = clean_float(row.get('CHOPO_16170:Triglicéridos'))
        creatinina = clean_float(row.get('CHOPO_16070:Creatinina'))
        urea = clean_float(row.get('CHOPO_16172:Urea'))
        acido_urico = clean_float(row.get('CHOPO_16010:Ácido úrico'))
        
        # Alertas de laboratorio basadas en criterios de CHOPO
        glucosa_alert = (glucosa < 70 or glucosa > 100) if glucosa is not None else False
        colesterol_alert = (colesterol > 200) if colesterol is not None else False
        trigliceridos_alert = (trigliceridos > 150) if trigliceridos is not None else False
        creatinina_alert = (creatinina < 0.6 or creatinina > 1.3) if creatinina is not None else False
        urea_alert = (urea < 15 or urea > 43) if urea is not None else False
        acido_urico_alert = (acido_urico < 2.5 or acido_urico > 7.0) if acido_urico is not None else False

        # 4. Odontograma
        dientes_sanos = None
        dientes_atencion = None
        tiene_odontograma = pd.notna(row.get('ODONTOGRAMA_Recomendaciones_Dentales'))
        
        if tiene_odontograma and tooth_cols:
            sanos = 0
            atencion = 0
            for col in tooth_cols:
                val = row[col]
                if pd.notna(val):
                    try:
                        fval = float(str(val).replace(',','.').strip())
                        if fval == 0.0:
                            sanos += 1
                        elif fval == 1.0:
                            atencion += 1
                    except:
                        pass
            dientes_sanos = sanos
            dientes_atencion = atencion

        # 5. Cardiorrespiratorio
        ekg_ritmo = str(row.get('ELECTROCARDIOGRAMA_Ritmo', '')).strip()
        ekg_ritmo = ekg_ritmo if pd.notna(row.get('ELECTROCARDIOGRAMA_Ritmo')) and ekg_ritmo != '' else None
        
        ekg_conclusion = str(row.get('ELECTROCARDIOGRAMA_Conclusion', '')).strip()
        ekg_conclusion = ekg_conclusion if pd.notna(row.get('ELECTROCARDIOGRAMA_Conclusion')) and ekg_conclusion != '' else None
        
        tiene_ekg = pd.notna(row.get('ELECTROCARDIOGRAMA_Archivo_Origen')) if 'ELECTROCARDIOGRAMA_Archivo_Origen' in row else (ekg_ritmo is not None)
        
        espiro_int = str(row.get('ESPIROMETRIA_Interpretacion_Sistema', '')).strip()
        espiro_int = espiro_int if pd.notna(row.get('ESPIROMETRIA_Interpretacion_Sistema')) and espiro_int != '' else None
        
        tiene_espirometria = pd.notna(row.get('ESPIROMETRIA_Archivo_Origen'))

        # Sub-estudios específicos de CHOPO
        tiene_biometria = pd.notna(row.get('CHOPO_17103:Hemoglobina'))
        tiene_orina = pd.notna(row.get('CHOPO_2370:Proteínas'))
        tiene_antigeno = pd.notna(row.get('CHOPO_22012:Antígeno Prostático Específico Total'))

        # 6. Encuestas de hábitos y estrés
        estres = clean_float(row.get(estres_col_name)) if estres_col_name else None
        
        sueno_calidad = None
        if sueno_col_name:
            sueno_val = row.get(sueno_col_name)
            if pd.notna(sueno_val):
                sueno_calidad = str(sueno_val).strip()
                if sueno_calidad == '':
                    sueno_calidad = None
                    
        sueno_horas = clean_float(row.get(sueno_hrs_col_name)) if sueno_hrs_col_name else None
        
        fuma = None
        if fuma_col_name:
            fuma_val = row.get(fuma_col_name)
            if pd.notna(fuma_val):
                fuma_raw = str(fuma_val).strip().lower()
                fuma = "Sí" if ('sí' in fuma_raw or 'si' in fuma_raw or 's' in fuma_raw or fuma_raw.startswith('s')) else "No"
                
        alcohol = None
        if alcohol_col_name:
            alcohol_val = row.get(alcohol_col_name)
            if pd.notna(alcohol_val):
                alcohol_raw = str(alcohol_val).strip().lower()
                alcohol = "Sí" if ('sí' in alcohol_raw or 'si' in alcohol_raw or 's' in alcohol_raw or alcohol_raw.startswith('s')) else "No"

        # Hábitos específicos de Peso, Alimentación y Sueño
        disp_peso = str(row.get(disposicion_peso_col, '')).strip() if disposicion_peso_col and pd.notna(row.get(disposicion_peso_col)) else None
        conf_peso = str(row.get(confianza_peso_col, '')).strip() if confianza_peso_col and pd.notna(row.get(confianza_peso_col)) else None
        imp_peso = str(row.get(importancia_peso_col, '')).strip() if importancia_peso_col and pd.notna(row.get(importancia_peso_col)) else None

        disp_alim = str(row.get(disposicion_alimentacion_col, '')).strip() if disposicion_alimentacion_col and pd.notna(row.get(disposicion_alimentacion_col)) else None
        conf_alim = str(row.get(confianza_alimentacion_col, '')).strip() if confianza_alimentacion_col and pd.notna(row.get(confianza_alimentacion_col)) else None
        imp_alim = str(row.get(importancia_alimentacion_col, '')).strip() if importancia_alimentacion_col and pd.notna(row.get(importancia_alimentacion_col)) else None

        disp_sueno = str(row.get(disposicion_sueno_col, '')).strip() if disposicion_sueno_col and pd.notna(row.get(disposicion_sueno_col)) else None
        conf_sueno = str(row.get(confianza_sueno_col, '')).strip() if confianza_sueno_col and pd.notna(row.get(confianza_sueno_col)) else None
        imp_sueno = str(row.get(importancia_sueno_col, '')).strip() if importancia_sueno_col and pd.notna(row.get(importancia_sueno_col)) else None

        patients_data.append({
            "nombre": nombre,
            "sexo": sexo,
            "rango_edad": rango_edad,
            "area": area,
            "compartir": compartir,
            "inbody": {
                "medido": imc is not None,
                "imc": imc,
                "peso": peso,
                "grasa": grasa,
                "musculo": musculo,
                "agua": agua
            },
            "chopo": {
                "medido": glucosa is not None,
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
            },
            "odontograma": {
                "medido": tiene_odontograma,
                "sanos": dientes_sanos,
                "atencion": dientes_atencion
            },
            "cardio_respiratorio": {
                "ekg_medido": tiene_ekg,
                "ekg_ritmo": ekg_ritmo,
                "ekg_conclusion": ekg_conclusion,
                "espiro_medido": tiene_espirometria,
                "espiro_interpretacion": espiro_int
            },
            "habitos": {
                "estres": estres,
                "sueno_calidad": sueno_calidad,
                "sueno_horas": sueno_horas,
                "fuma": fuma,
                "alcohol": alcohol,
                "disp_peso": disp_peso,
                "conf_peso": conf_peso,
                "imp_peso": imp_peso,
                "disp_alim": disp_alim,
                "conf_alim": conf_alim,
                "imp_alim": imp_alim,
                "disp_sueno": disp_sueno,
                "conf_sueno": conf_sueno,
                "imp_sueno": imp_sueno
            },
            "estudios_realizados": {
                "inbody": imc is not None,
                "chopo_quimica": glucosa is not None,
                "chopo_biometria": tiene_biometria,
                "chopo_orina": tiene_orina,
                "chopo_antigeno": tiene_antigeno,
                "odontograma": tiene_odontograma,
                "ekg": tiene_ekg,
                "espirometria": tiene_espirometria
            }
        })

    # 1. Serializar datos a JSON (Confidencial con nombres reales)
    json_data = json.dumps(patients_data, indent=2, ensure_ascii=False)
    
    # Crear contenido HTML confidencial
    html_template = get_dashboard_html_template(json_data)
    
    print(f"Escribiendo dashboard interactivo final (Confidencial) en: {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_template)

    # 2. Crear versión pública totalmente anonimizada para GitHub Pages (sin nombres reales)
    patients_data_public = []
    for idx, p in enumerate(patients_data):
        p_public = p.copy()
        # Copiar de forma profunda el objeto para no alterar el original
        p_public_dict = json.loads(json.dumps(p_public))
        p_public_dict["nombre"] = f"Colaborador {idx + 1}"
        patients_data_public.append(p_public_dict)
        
    json_data_public = json.dumps(patients_data_public, indent=2, ensure_ascii=False)
    html_template_public = get_dashboard_html_template(json_data_public)
    
    public_output_path = os.path.join(base_dir, "index.html")
    print(f"Escribiendo dashboard público (Anonimizado) en: {public_output_path}...")
    with open(public_output_path, 'w', encoding='utf-8') as f:
        f.write(html_template_public)
        
    print("¡Generación de dashboards completada con éxito total (local confidencial e index.html público)!")

def get_dashboard_html_template(json_data):
    # Retorna la plantilla HTML completa del dashboard inyectando el RAW_DATA
    template = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Epidemiológico y de Salud Poblacional - SANOFI 2026</title>
    
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    
    <!-- FontAwesome CDN -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <!-- Chart.js CDN -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2"></script>

    <style>
        /* CSS GENERAL (Estilo Premium Dark-Mode en pantalla) */
        :root {
            --bg-main: #0a0e14; /* Fondo ultra oscuro para contraste premium */
            --bg-card: #16212E; /* Official Med&Corp Deep Blue (Pantone 296 C) */
            --border-card: rgba(177, 177, 176, 0.15); /* Official Cool Gray con transparencia */
            --text-primary: #f8fafc;
            --text-secondary: #B1B1B0; /* Official Med&Corp Cool Gray */
            --primary-accent: #D22936; /* Official Med&Corp Red (Pantone 1788 C) */
            --primary-accent-rgb: 210, 41, 54;
            --secondary-accent: #3b82f6; /* Azul Clínico */
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Outfit', 'Segoe UI', 'Inter', sans-serif; /* Elegante sans-serif para máxima lectura */
            background-color: var(--bg-main);
            color: var(--text-primary);
            line-height: 1.5;
            height: 100vh;
            width: 100vw;
            overflow: hidden; /* Evita scrolls globales */
        }

        /* DISEÑO DE LAYOUT: SBARRA LATERAL + CONTENIDO PRINCIPAL */
        .app-layout {
            display: flex;
            width: 100vw;
            height: 100vh;
            overflow: hidden;
        }

        /* BARRA LATERAL IZQUIERDA */
        .sidebar {
            width: 320px;
            background-color: #0c1219; /* Variación ultra oscura del azul institucional */
            border-right: 1px solid var(--border-card);
            padding: 30px 24px;
            display: flex;
            flex-direction: column;
            gap: 25px;
            flex-shrink: 0;
            height: 100%;
        }

        .sidebar-logo {
            display: flex;
            justify-content: center;
            align-items: center;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(177, 177, 176, 0.1);
        }

        .sidebar-logo img {
            max-width: 100%;
            height: 50px;
            object-fit: contain;
        }

        .sidebar-campaign {
            text-align: center;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .sidebar-campaign h2 {
            font-size: 16px;
            font-weight: 700;
            color: var(--text-primary);
            letter-spacing: 0.5px;
        }

        .sidebar-campaign p {
            font-size: 12px;
            color: var(--text-secondary);
            font-family: 'Consolas', monospace;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .sidebar-filters {
            display: flex;
            flex-direction: column;
            gap: 16px;
            margin-top: 10px;
        }

        .sidebar-filters h3 {
            font-size: 13px;
            font-weight: 700;
            color: var(--primary-accent);
            border-bottom: 1px solid var(--border-card);
            padding-bottom: 8px;
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .filter-group {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .filter-group label {
            font-size: 12px;
            font-weight: 600;
            color: var(--text-secondary);
        }

        .control-select {
            background-color: #16212E;
            border: 1px solid var(--border-card);
            color: white;
            padding: 10px 14px;
            border-radius: 8px;
            font-size: 13.5px;
            font-family: inherit;
            cursor: pointer;
            width: 100%;
            transition: all 0.2s;
        }

        .control-select:focus {
            outline: none;
            border-color: var(--primary-accent);
            box-shadow: 0 0 0 2px rgba(210, 41, 54, 0.2);
        }

        .btn-print {
            background: linear-gradient(135deg, var(--primary-accent), #8c161f);
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            font-weight: 700;
            font-size: 13.5px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            transition: all 0.3s;
            margin-top: auto;
        }

        .btn-print:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(210, 41, 54, 0.4);
        }

        .sidebar-footer {
            font-size: 11px;
            color: #475569;
            text-align: center;
            line-height: 1.4;
            border-top: 1px solid rgba(177, 177, 176, 0.1);
            padding-top: 15px;
        }

        /* CONTENIDO PRINCIPAL DE LA DERECHA */
        .main-content {
            flex: 1;
            background-color: var(--bg-main);
            padding: 25px 35px;
            display: flex;
            flex-direction: column;
            gap: 20px;
            height: 100%;
            overflow: hidden; /* El contenedor no scrollea, scrollean los panes */
        }

        /* NAVEGACIÓN POR PESTAÑAS (TABS) */
        .tabs-header {
            display: flex;
            gap: 8px;
            border-bottom: 1px solid var(--border-card);
            padding-bottom: 12px;
            flex-shrink: 0;
            overflow-x: auto;
        }

        .tab-button {
            background: none;
            border: none;
            color: var(--text-secondary);
            padding: 10px 18px;
            font-size: 13.5px;
            font-weight: 600;
            font-family: inherit;
            cursor: pointer;
            border-radius: 8px;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 8px;
            white-space: nowrap;
        }

        .tab-button:hover {
            color: var(--text-primary);
            background-color: rgba(255, 255, 255, 0.04);
        }

        .tab-button.active {
            color: white;
            background-color: var(--primary-accent);
        }

        /* PANALES DE CONTENIDO (PANES) */
        .tabs-container {
            flex: 1;
            position: relative;
            height: 100%;
            overflow: hidden;
        }

        .tab-pane {
            display: flex; /* Siempre flex para que Chart.js pueda medir dimensiones físicas en carga */
            flex-direction: column;
            gap: 20px;
            height: 0; /* Oculto físicamente */
            overflow: hidden; /* Evitar desborde visual */
            opacity: 0; /* Completamente transparente */
            pointer-events: none; /* No interactivo */
            position: absolute; /* Sacado del flujo normal para sobreponer pestañas */
            width: 100%;
            padding-right: 5px;
        }

        .tab-pane.active {
            height: 100%; /* Altura completa al estar activa */
            overflow-y: auto; /* Permitir scroll si excede la pantalla */
            opacity: 1; /* Totalmente visible */
            pointer-events: auto; /* Interactivo */
            position: relative; /* Regresa al flujo de pantalla */
        }

        /* TIPOGRAFÍAS DE CABEZALES (Elegantemente legibles) */
        h1, h2, h3, h4 {
            font-family: 'Outfit', 'Segoe UI', 'Inter', sans-serif;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        /* GRIDS & CARDS */
        .kpi-row {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            flex-shrink: 0;
        }

        .kpi-card {
            background-color: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 12px;
            padding: 16px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            transition: all 0.3s;
        }

        .kpi-card:hover {
            border-color: rgba(210, 41, 54, 0.3);
            transform: translateY(-2px);
        }

        .kpi-info h4 {
            color: var(--text-secondary);
            font-size: 11.5px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }

        .kpi-info p {
            font-family: 'Outfit', 'Segoe UI', sans-serif;
            font-size: 30px;
            font-weight: 700;
            color: var(--text-primary);
            line-height: 1.1;
        }

        .kpi-icon {
            width: 42px;
            height: 42px;
            background-color: rgba(255,255,255,0.03);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            color: var(--primary-accent);
        }

        .dashboard-grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            flex-shrink: 0;
        }

        .dashboard-grid-3 {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 20px;
            flex-shrink: 0;
        }

        .dashboard-card {
            background-color: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 16px;
            padding: 20px 24px;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }

        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid rgba(255,255,255,0.06);
            padding-bottom: 10px;
        }

        .card-header h3 {
            font-size: 15px;
            font-weight: 600;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .chart-container {
            position: relative;
            height: 220px; /* Reducido ligeramente para optimizar vista única */
            width: 100%;
            display: flex;
            justify-content: center;
            align-items: center;
        }

        /* TABLAS ESTILO PREMIUM */
        .table-wrapper {
            overflow-x: auto;
            border-radius: 10px;
            border: 1px solid var(--border-card);
        }

        .premium-table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 13.5px;
        }

        .premium-table th {
            background-color: rgba(255,255,255,0.02);
            color: var(--text-secondary);
            font-weight: 600;
            padding: 10px 14px;
            border-bottom: 1px solid var(--border-card);
            text-transform: uppercase;
            font-size: 10px;
            letter-spacing: 0.5px;
        }

        .premium-table td {
            padding: 10px 14px;
            border-bottom: 1px solid rgba(255,255,255,0.04);
            color: var(--text-primary);
        }

        .premium-table tr:last-child td {
            border-bottom: none;
        }

        .premium-table tr:hover td {
            background-color: rgba(255,255,255,0.01);
        }

        /* CUADROS DE CONCLUSIONES */
        .conclusion-box {
            background: linear-gradient(135deg, rgba(210, 41, 54, 0.04), rgba(0,0,0,0.2));
            border-left: 4px solid var(--primary-accent);
            border-radius: 10px;
            padding: 15px 18px;
            font-size: 13px;
            color: var(--text-secondary);
            line-height: 1.42;
            flex-shrink: 0;
        }

        .conclusion-box h4 {
            color: var(--text-primary);
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 5px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .recommendation-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .rec-item {
            display: flex;
            gap: 12px;
            align-items: flex-start;
        }

        .rec-num {
            width: 24px;
            height: 24px;
            background-color: rgba(210, 41, 54, 0.15);
            color: var(--primary-accent);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 12px;
            flex-shrink: 0;
        }

        .rec-content h5 {
            font-size: 13.5px;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 2px;
        }

        .rec-content p {
            font-size: 12.5px;
            color: var(--text-secondary);
        }

        /* ------------------------------------------------------------- */
        /* HOJA DE ESTILOS DE IMPRESION (window.print() ) */
        /* ------------------------------------------------------------- */
        @page {
            size: A4 landscape;
            margin: 1.2cm !important; /* Margen elegante y estándar en el nivel de página */
        }

        @media print {
            body {
                background-color: white !important;
                color: #0f172a !important;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
                padding-bottom: 0 !important;
                font-size: 11px !important;
                overflow: visible !important;
                height: auto !important;
                width: auto !important;
                margin: 0 !important;
            }

            /* Ocultar sidebar y pestañas de navegación */
            .sidebar, .tabs-header {
                display: none !important;
            }

            .app-layout {
                display: block !important;
                width: auto !important;
                height: auto !important;
                overflow: visible !important;
            }

            .main-content {
                display: block !important;
                width: auto !important;
                height: auto !important;
                padding: 0 !important;
                overflow: visible !important;
                background-color: white !important;
            }

            /* Forzar salto de página limpio por pestaña clínica en Horizontal (A4 Landscape) */
            .tab-pane {
                display: flex !important;
                flex-direction: column !important;
                page-break-before: always !important;
                page-break-after: always !important;
                page-break-inside: avoid !important;
                width: 100% !important; /* Adaptable automáticamente al margen del navegador */
                height: 180mm !important; /* Altura de seguridad para evitar desbordes a páginas extra */
                padding: 0 !important; /* No necesita padding adicional, los márgenes de 1.2cm los da @page */
                box-sizing: border-box !important;
                overflow: hidden !important;
                background-color: white !important;
                gap: 12px !important;
                /* Resets de visibilidad fluida de pantalla */
                position: static !important; /* Regresar al flujo normal estático para paginación */
                opacity: 1 !important;
                pointer-events: auto !important;
            }

            .tab-pane:first-child {
                page-break-before: avoid !important;
            }

            .page-header-print {
                display: flex !important;
                justify-content: space-between !important;
                align-items: center !important;
                border-bottom: 2px solid var(--primary-accent) !important;
                padding-bottom: 6px !important;
                margin-bottom: 4px !important;
            }

            .page-header-print .print-title {
                font-family: 'Outfit', sans-serif !important;
                font-size: 12px !important;
                font-weight: 700 !important;
                color: #0f172a !important;
            }

            .page-header-print .print-subtitle {
                font-size: 9px !important;
                color: #64748b !important;
                text-align: right !important;
                line-height: 1.3 !important;
            }

            h2 {
                font-size: 16px !important;
                margin-bottom: 2px !important;
                color: #0f172a !important;
            }

            p {
                font-size: 10.5px !important;
                line-height: 1.38 !important;
                color: #334155 !important;
            }

            /* KPIs en Impresión (Fuerza 4 columnas horizontales) */
            .kpi-row {
                display: grid !important;
                grid-template-columns: repeat(4, 1fr) !important;
                gap: 10px !important;
            }

            .kpi-card {
                background-color: #f8fafc !important;
                border: 1px solid #e2e8f0 !important;
                border-radius: 8px !important;
                padding: 6px 10px !important;
            }

            .kpi-info h4 {
                font-size: 8.5px !important;
                margin-bottom: 2px !important;
            }

            .kpi-info p {
                color: #0f172a !important;
                font-size: 16px !important;
                font-weight: 700 !important;
            }

            .kpi-icon {
                width: 26px !important;
                height: 26px !important;
                font-size: 11px !important;
                border-radius: 5px !important;
                background-color: #f1f5f9 !important;
                color: var(--primary-accent) !important;
            }

            /* Gráficos en Impresión (2 Columnas lado a lado) */
            .dashboard-grid-2 {
                display: grid !important;
                grid-template-columns: 1fr 1fr !important;
                gap: 12px !important;
                width: 100% !important;
            }

            .dashboard-grid-3 {
                display: grid !important;
                grid-template-columns: 1fr 1fr 1fr !important;
                gap: 12px !important;
                width: 100% !important;
            }

            .dashboard-card {
                background-color: white !important;
                border: 1px solid #e2e8f0 !important;
                border-radius: 10px !important;
                padding: 10px 14px !important;
                gap: 6px !important;
            }

            .card-header {
                padding-bottom: 4px !important;
                margin-bottom: 2px !important;
            }

            .card-header h3 {
                color: #0f172a !important;
                font-size: 11px !important;
            }

            .chart-container {
                height: 130px !important; /* Altura compacta optimizada para formato horizontal */
                max-height: 130px !important;
                width: 100% !important;
            }

            canvas {
                max-height: 130px !important;
                width: 100% !important;
                display: block !important;
            }

            /* Tablas */
            .premium-table {
                font-size: 10px !important;
            }

            .premium-table th {
                background-color: #f8fafc !important;
                color: #475569 !important;
                border-bottom: 1px solid #cbd5e1 !important;
                padding: 5px 8px !important;
                font-size: 8px !important;
            }

            .premium-table td {
                color: #0f172a !important;
                border-bottom: 1px solid #f1f5f9 !important;
                padding: 5px 8px !important;
            }

            /* Cuadros de Conclusión */
            .conclusion-box {
                background: #fdfaf7 !important;
                border-left: 3px solid var(--primary-accent) !important;
                border-radius: 6px !important;
                padding: 8px 12px !important;
                color: #334155 !important;
                margin-top: 2px !important;
                font-size: 10px !important;
                line-height: 1.35 !important;
            }

            .conclusion-box h4 {
                color: #0f172a !important;
                font-size: 11px !important;
                margin-bottom: 2px !important;
            }

            /* Recomendaciones */
            .recommendation-list {
                gap: 6px !important;
            }

            .rec-item {
                gap: 8px !important;
            }

            .rec-num {
                width: 18px !important;
                height: 18px !important;
                font-size: 10px !important;
                background-color: #fdfaf7 !important;
                border: 1px solid #cbd5e1 !important;
                color: var(--primary-accent) !important;
            }

            .rec-content h5 {
                color: #0f172a !important;
                font-size: 11px !important;
                margin-bottom: 1px !important;
            }

            .rec-content p {
                color: #475569 !important;
                font-size: 9.5px !important;
            }
        }
    </style>
</head>
<body>
    <div class="app-layout">
        <!-- BARRA LATERAL IZQUIERDA CON FILTROS E INFORMACIÓN -->
        <aside class="sidebar">
            <div class="sidebar-logo">
                <img src="sanofi_logo_white.png" alt="SANOFI Logo">
            </div>
            
            <div class="sidebar-campaign">
                <h2>Campaña SANOFI 2026</h2>
                <p>Check-Up Epidemiológico</p>
            </div>

            <!-- FILTROS SANOFI -->
            <div class="sidebar-filters">
                <h3><i class="fa-solid fa-sliders"></i> FILTRAR POBLACIÓN</h3>
                
                <div class="filter-group">
                    <label for="filter-sexo">Género:</label>
                    <select id="filter-sexo" class="control-select" onchange="updateDashboard()">
                        <option value="Todos">Todos los géneros</option>
                        <option value="Femenino">Mujeres</option>
                        <option value="Masculino">Hombres</option>
                    </select>
                </div>

                <div class="filter-group">
                    <label for="filter-edad">Rango de Edad:</label>
                    <select id="filter-edad" class="control-select" onchange="updateDashboard()">
                        <option value="Todos">Todas las edades</option>
                        <option value="21-30 años">21 - 30 años</option>
                        <option value="31-40 años">31 - 40 años</option>
                        <option value="41-50 años">41 - 50 años</option>
                        <option value="Más de 50 años">Más de 50 años</option>
                    </select>
                </div>

                <div class="filter-group">
                    <label for="filter-area">Área de Trabajo:</label>
                    <select id="filter-area" class="control-select" onchange="updateDashboard()">
                        <option value="Todos">Todas las áreas</option>
                    </select>
                </div>
            </div>

            <button class="btn-print" onclick="window.print()">
                <i class="fa-solid fa-print"></i> EXPORTAR REPORTE
            </button>
            
            <div class="sidebar-footer">
                <p>Desarrollado por <a href="https://medycorp.mx/" target="_blank" style="color: var(--primary-accent); text-decoration: none; font-weight: 600; transition: color 0.2s ease-in-out;" onmouseover="this.style.color='#ffffff'" onmouseout="this.style.color='var(--primary-accent)'">Med&Corp</a> y <a href="https://mexjsa.github.io/nexos/" target="_blank" style="color: var(--primary-accent); text-decoration: none; font-weight: 600; transition: color 0.2s ease-in-out;" onmouseover="this.style.color='#ffffff'" onmouseout="this.style.color='var(--primary-accent)'">NEXOS IA</a></p>
                <p>© 2026 • Inteligencia Clínica</p>
            </div>
        </aside>

        <!-- CONTENIDO PRINCIPAL (A la derecha de la sidebar) -->
        <main class="main-content">
            <!-- PESTAÑAS DE NAVEGACIÓN -->
            <div class="tabs-header">
                <button class="tab-button active" onclick="switchTab('page-1')">
                    <i class="fa-solid fa-users"></i> 1. Resumen y Demografía
                </button>
                <button class="tab-button" onclick="switchTab('page-2')">
                    <i class="fa-solid fa-weight-scale"></i> 2. Composición Corporal
                </button>
                <button class="tab-button" onclick="switchTab('page-3')">
                    <i class="fa-solid fa-flask"></i> 3. Laboratorios Chopo
                </button>
                <button class="tab-button" onclick="switchTab('page-4')">
                    <i class="fa-solid fa-lungs"></i> 4. Especialidades
                </button>
                <button class="tab-button" onclick="switchTab('page-5')">
                    <i class="fa-solid fa-brain"></i> 5. Estrategia y Hábitos
                </button>
            </div>

            <!-- CONTENEDORES DE LAS PESTAÑAS (En pantalla solo se muestra el .active) -->
            <div class="tabs-container">

                <!-- ============================================================= -->
                <!-- PÁGINA 1: PORTADA Y DEMOGRAFÍA -->
                <!-- ============================================================= -->
                <section class="tab-pane active" id="page-1">
            <div class="page-header-print">
                <span class="print-title">REPORTE EPIDEMIOLÓGICO POBLACIONAL • SANOFI 2026</span>
                <span class="print-subtitle">Página 1 de 5<br>Med&Corp Sede Central</span>
            </div>

            <div style="display: flex; flex-direction: column; gap: 15px;">
                <h2 style="font-size: 26px; color: var(--text-primary); border-left: 4px solid var(--primary-accent); padding-left: 12px; font-family: 'Outfit', sans-serif;">
                    1. Introducción y Demografía
                </h2>
                <p style="color: var(--text-secondary); font-size: 14.5px;">
                    El presente informe epidemiológico ejecutivo expone los resultados de salud colectivos obtenidos del programa de Check-Up Integral 2026 realizado para el personal corporativo de <strong>SANOFI S.A. de C.V.</strong> en su sede de evaluación central. El objetivo es estructurar iniciativas preventivas personalizadas basadas en el perfil metabólico, composicional, cardiovascular, pulmonar y dental real de la población analizada.
                </p>
            </div>

            <!-- KPI Cards de la Portada -->
            <div class="kpi-row">
                <div class="kpi-card">
                    <div class="kpi-info" style="display: flex; flex-direction: column; gap: 4px;">
                        <h4 style="margin: 0;">Población Evaluada</h4>
                        <div style="display: flex; align-items: baseline; gap: 6px;">
                            <span id="kpi-total" style="font-size: 24px; font-weight: 800; color: white; font-family: 'Outfit', sans-serif;">194</span>
                            <span style="font-size: 11.5px; color: var(--text-secondary); font-weight: 500;">de 200 (97.0%)</span>
                        </div>
                    </div>
                    <div class="kpi-icon"><i class="fa-solid fa-users"></i></div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-info">
                        <h4>Estudios Promedio / Persona</h4>
                        <p id="kpi-estudios-promedio">0.0</p>
                    </div>
                    <div class="kpi-icon"><i class="fa-solid fa-notes-medical"></i></div>
                </div>
                <div class="kpi-card" style="grid-column: span 2; display: flex; flex-direction: row; align-items: center; justify-content: space-between; padding: 15px 20px; gap: 20px; min-height: 82px;">
                    <div style="flex: 1; display: flex; flex-direction: column; gap: 4px;">
                        <h4 style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; margin: 0;">Compartir Información (Consentimiento)</h4>
                        <div style="display: flex; align-items: baseline; gap: 8px;">
                            <span id="kpi-consentimiento-si-pct" style="font-size: 24px; font-weight: 800; color: #10b981; font-family: 'Outfit', sans-serif;">0%</span>
                            <span id="kpi-consentimiento-si-qty" style="font-size: 12px; color: var(--text-secondary); font-weight: 500;">(0 de 0)</span>
                        </div>
                    </div>
                    <div style="width: 200px; display: flex; flex-direction: column; gap: 5px; justify-content: center;">
                        <div style="display: flex; justify-content: space-between; font-size: 9.5px; font-weight: 600; font-family: 'Outfit', sans-serif;">
                            <span style="color: #10b981;">Sí: <span id="bar-consentimiento-si-val" style="font-weight: 700;">0</span> (<span id="bar-consentimiento-si-pct">0%</span>)</span>
                            <span style="color: #ef4444;">No: <span id="bar-consentimiento-no-val" style="font-weight: 700;">0</span> (<span id="bar-consentimiento-no-pct">0%</span>)</span>
                        </div>
                        <div style="height: 12px; width: 100%; background-color: rgba(255,255,255,0.06); border-radius: 6px; overflow: hidden; display: flex; border: 1px solid rgba(255,255,255,0.04);">
                            <div id="bar-consentimiento-si" style="height: 100%; background-color: #10b981; transition: width 0.4s ease; width: 0%;"></div>
                            <div id="bar-consentimiento-no" style="height: 100%; background-color: #ef4444; transition: width 0.4s ease; width: 0%;"></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Gráficos Demográficos -->
            <div class="dashboard-grid-3">
                <div class="dashboard-card">
                    <div class="card-header">
                        <h3><i class="fa-solid fa-people-group" style="color: var(--primary-accent)"></i> Distribución de Edad por Género</h3>
                    </div>
                    <div class="chart-container">
                        <canvas id="chart-edad-sexo"></canvas>
                    </div>
                </div>
                <div class="dashboard-card">
                    <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
                        <h3><i class="fa-solid fa-clipboard-check" style="color: var(--primary-accent)"></i> Cobertura de Estudios</h3>
                        <span id="slicer-indicator" style="font-size: 11px; color: #10b981; font-weight: 500; cursor: pointer; display: none;" onclick="clearStudyFilter()">
                            Limpiar <i class="fa-solid fa-circle-xmark"></i>
                        </span>
                    </div>
                    <div class="chart-container">
                        <canvas id="chart-estudios"></canvas>
                    </div>
                </div>
                <div class="dashboard-card">
                    <div class="card-header">
                        <h3><i class="fa-solid fa-chart-pie" style="color: var(--primary-accent)"></i> Participación</h3>
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 12px; flex: 1; justify-content: space-between; padding-top: 5px;">
                        <div style="font-size: 11.5px; font-weight: 700; color: #10b981; text-align: center; margin-bottom: 2px;">
                            Se alcanzó un 91.24% de registros en línea
                        </div>
                        <div class="chart-container" style="display: flex; align-items: center; gap: 12px; height: 180px;">
                            <div style="width: 48%; height: 100%; position: relative; display: flex; align-items: center; justify-content: center;">
                                <canvas id="chart-participacion" style="max-height: 100% !important; max-width: 100% !important;"></canvas>
                                <!-- Texto en el centro de la dona -->
                                <div style="position: absolute; text-align: center; pointer-events: none; top: 52%; left: 50%; transform: translate(-50%, -50%);">
                                    <span style="font-size: 16px; font-weight: 800; color: white; display: block; line-height: 1;">91.24%</span>
                                    <span style="font-size: 8px; color: var(--text-secondary); text-transform: uppercase; font-weight: 600;">En línea</span>
                                </div>
                            </div>
                            <!-- Leyenda Custom con los bloques que emulan la primera imagen -->
                            <div style="width: 52%; display: flex; flex-direction: column; gap: 5px; font-size: 9.5px; justify-content: center;">
                                <div style="border-left: 2px solid #64748b; padding-left: 6px; line-height: 1.15;">
                                    <span style="color: var(--text-secondary); text-transform: uppercase; font-size: 7.5px; display: block; font-weight: 600;">Total Registros</span>
                                    <strong style="color: white; font-size: 11px;">194</strong> <span style="color: var(--text-secondary); font-size: 9px;">| 100%</span>
                                </div>
                                <div style="border-left: 2px solid #3b82f6; padding-left: 6px; line-height: 1.15;">
                                    <span style="color: var(--text-secondary); text-transform: uppercase; font-size: 7.5px; display: block; font-weight: 600;">Registros en Línea</span>
                                    <strong style="color: #3b82f6; font-size: 11px;">177</strong> <span style="color: var(--text-secondary); font-size: 9px;">| 91.24%</span>
                                </div>
                                <div style="border-left: 2px solid #f97316; padding-left: 6px; line-height: 1.15;">
                                    <span style="color: var(--text-secondary); text-transform: uppercase; font-size: 7.5px; display: block; font-weight: 600;">Registros Manuales</span>
                                    <strong style="color: #f97316; font-size: 11px;">17</strong> <span style="color: var(--text-secondary); font-size: 9px;">| 8.76%</span>
                                </div>
                                <div style="border-left: 2px solid #10b981; padding-left: 6px; line-height: 1.15;">
                                    <span style="color: var(--text-secondary); text-transform: uppercase; font-size: 7.5px; display: block; font-weight: 600;">Consentamientos Firmados</span>
                                    <strong style="color: #10b981; font-size: 11px;">17</strong> <span style="color: var(--text-secondary); font-size: 9px;">| 8.76%</span>
                                </div>
                                <div style="border-left: 2px solid #a855f7; padding-left: 6px; line-height: 1.15;">
                                    <span style="color: var(--text-secondary); text-transform: uppercase; font-size: 7.5px; display: block; font-weight: 600;">Con Registro / Sin Estudios</span>
                                    <strong style="color: #a855f7; font-size: 11px;">16</strong> <span style="color: var(--text-secondary); font-size: 9px;">| 8.25%</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="conclusion-box">
                <h4><i class="fa-solid fa-lightbulb" style="color: var(--primary-accent)"></i> Resumen Demográfico:</h4>
                <p>La población de SANOFI que asistió a las evaluaciones corporativas de salud está compuesta principalmente por mujeres (59.8%). El grupo etario predominante se ubica entre los <strong>41 y 50 años</strong> de edad (34.0%), perfilando a un equipo directivo y directivo-operativo maduro con un alto potencial de respuesta preventiva a cambios en el estilo de vida.</p>
            </div>
        </section>


        <!-- ============================================================= -->
        <!-- PÁGINA 2: NUTRICIÓN Y COMPOSICIÓN CORPORAL (INBODY) -->
        <!-- ============================================================= -->
        <section class="tab-pane" id="page-2">
            <div class="page-header-print">
                <span class="print-title">REPORTE EPIDEMIOLÓGICO POBLACIONAL • SANOFI 2026</span>
                <span class="print-subtitle">Página 2 de 5<br>Composición Corporal (InBody)</span>
            </div>

            <div style="display: flex; flex-direction: column; gap: 10px;">
                <h2 style="font-size: 24px; color: var(--text-primary); border-left: 4px solid var(--primary-accent); padding-left: 12px;">
                    2. Composición Corporal y Riesgo Metabólico-Nutricional
                </h2>
                <p style="color: var(--text-secondary); font-size: 14px;">
                    A través de la tecnología de bioimpedancia eléctrica de alta precisión de InBody, se analizó la relación entre el peso, la masa de grasa visceral y la masa muscular esquelética para estadificar de forma fidedigna los factores de riesgo cardiovascular de SANOFI.
                </p>
            </div>

            <!-- Gráficos InBody -->
            <div class="dashboard-grid-2">
                <div class="dashboard-card" style="flex: 1.3;">
                    <div class="card-header">
                        <h3><i class="fa-solid fa-chart-bar" style="color: var(--primary-accent)"></i> Distribución de IMC (Índice de Masa Corporal)</h3>
                    </div>
                    <div class="chart-container" style="height: 240px;">
                        <canvas id="chart-imc"></canvas>
                    </div>
                </div>
                <div class="dashboard-card" style="flex: 0.7;">
                    <div class="card-header">
                        <h3><i class="fa-solid fa-list-check" style="color: var(--primary-accent)"></i> Medias Poblacionales (InBody)</h3>
                    </div>
                    <div class="table-wrapper">
                        <table class="premium-table">
                            <thead>
                                <tr>
                                    <th>Indicador InBody</th>
                                    <th>Media Muestra</th>
                                    <th>Estado Poblacional</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>Peso Corporal</td>
                                    <td id="td-peso">72.8 kg</td>
                                    <td>Rango Medio</td>
                                </tr>
                                <tr>
                                    <td>Masa Musculoesquelética</td>
                                    <td id="td-musculo">27.4 kg</td>
                                    <td>Adecuado</td>
                                </tr>
                                <tr>
                                    <td>Masa Grasa Corporal</td>
                                    <td id="td-grasa">23.6 kg</td>
                                    <td style="color: var(--danger-accent); font-weight: 600;">Elevado</td>
                                </tr>
                                <tr>
                                    <td>Agua Corporal Total</td>
                                    <td id="td-agua">39.2 L</td>
                                    <td>Normohidratado</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <div class="conclusion-box">
                <h4><i class="fa-solid fa-person-running" style="color: var(--primary-accent)"></i> Diagnóstico de Composición Corporal:</h4>
                <p>Existe una alta prevalencia combinada de exceso de peso metabólico en el corporativo de SANOFI: el <strong>59.4% de los colaboradores medidos presenta Sobrepeso u Obesidad</strong> (41.2% Sobrepeso, 18.2% Obesidad), mientras que solo el 39.9% de los evaluados cuenta con un peso considerado saludable. Esto indica la necesidad urgente de rediseñar las barras de alimentación de los comedores corporativos e incentivar opciones saludables.</p>
            </div>
        </section>


        <!-- ============================================================= -->
        <!-- PÁGINA 3: SALUD METABÓLICA Y LABORATORIOS (CHOPO) -->
        <!-- ============================================================= -->
        <section class="tab-pane" id="page-3">
            <div class="page-header-print">
                <span class="print-title">REPORTE EPIDEMIOLÓGICO POBLACIONAL • SANOFI 2026</span>
                <span class="print-subtitle">Página 3 de 5<br>Salud Metabólica y Biomarcadores</span>
            </div>

            <div style="display: flex; flex-direction: column; gap: 10px;">
                <h2 style="font-size: 24px; color: var(--text-primary); border-left: 4px solid var(--primary-accent); padding-left: 12px;">
                    3. Perfil de Laboratorios Clínicos y Biomarcadores (CHOPO)
                </h2>
                <p style="color: var(--text-secondary); font-size: 14px;">
                    El perfil de laboratorio (Química Clínica de 12 elementos y Biometría Hemática) arroja datos objetivos y valiosos sobre las condiciones asintomáticas que incrementan el riesgo de accidentes metabólicos de los colaboradores de SANOFI.
                </p>
            </div>

            <!-- Prevalencia de Alertas CHOPO -->
            <div class="dashboard-grid-2">
                <div class="dashboard-card">
                    <div class="card-header">
                        <h3><i class="fa-solid fa-triangle-exclamation" style="color: var(--danger-accent)"></i> Tasa de Alertas en Biomarcadores Críticos</h3>
                    </div>
                    <div class="chart-container" style="height: 240px;">
                        <canvas id="chart-alertas-chopo"></canvas>
                    </div>
                </div>
                <div class="dashboard-card">
                    <div class="card-header">
                        <h3><i class="fa-solid fa-flask" style="color: var(--primary-accent)"></i> Promedios y Rangos de Química y Hematología</h3>
                    </div>
                    <div class="table-wrapper">
                        <table class="premium-table">
                            <thead>
                                <tr>
                                    <th>Analito Clínico</th>
                                    <th>Resultado Promedio</th>
                                    <th>Rango Clínico Esperado</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>Glucosa en ayuno</td>
                                    <td id="td-glucosa">92.4 mg/dL</td>
                                    <td>70.0 - 100.0 mg/dL</td>
                                </tr>
                                <tr>
                                    <td>Colesterol Total</td>
                                    <td id="td-colesterol" style="color: var(--danger-accent); font-weight:600;">212.1 mg/dL</td>
                                    <td>0.0 - 200.0 mg/dL</td>
                                </tr>
                                <tr>
                                    <td>Triglicéridos</td>
                                    <td id="td-trigliceridos" style="color: var(--danger-accent); font-weight:600;">164.8 mg/dL</td>
                                    <td>0.0 - 150.0 mg/dL</td>
                                </tr>
                                <tr>
                                    <td>Creatinina</td>
                                    <td id="td-creatinina">0.86 mg/dL</td>
                                    <td>0.70 - 1.30 mg/dL</td>
                                </tr>
                                <tr>
                                    <td>Urea en suero</td>
                                    <td id="td-urea">29.4 mg/dL</td>
                                    <td>15.0 - 43.0 mg/dL</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <div class="conclusion-box">
                <h4><i class="fa-solid fa-heart-pulse" style="color: var(--primary-accent)"></i> Resumen de Riesgo Metabólico Silencioso:</h4>
                <p>Se identificó una preocupante prevalencia de hiperlipidemia en la población de SANOFI: el <strong>44.9% de los colaboradores presenta hipercolesterolemia (>200 mg/dL)</strong>, y el <strong>26.9% presenta hipertrigliceridemia (>150 mg/dL)</strong>. El colesterol promedio general se sitúa en 212.1 mg/dL (un valor fuera de rango saludable). Estos datos de laboratorio se correlacionan con la alta tasa de sobrepeso e indican una urgencia de intervención de salud cardiovascular preventiva.</p>
            </div>
        </section>


        <!-- ============================================================= -->
        <!-- PÁGINA 4: SALUD DENTAL, RESPIRATORIA Y CARDIOVASCULAR -->
        <!-- ============================================================= -->
        <section class="tab-pane" id="page-4">
            <div class="page-header-print">
                <span class="print-title">REPORTE EPIDEMIOLÓGICO POBLACIONAL • SANOFI 2026</span>
                <span class="print-subtitle">Página 4 de 5<br>Salud Dental y Funcional</span>
            </div>

            <div style="display: flex; flex-direction: column; gap: 10px;">
                <h2 style="font-size: 24px; color: var(--text-primary); border-left: 4px solid var(--primary-accent); padding-left: 12px;">
                    4. Salud Dental, Cardiovascular (EKG) y Pulmonar (Espirometría)
                </h2>
                <p style="color: var(--text-secondary); font-size: 14px;">
                    Integrando los resultados de Odontología, Electrocardiogramas clínicos y Espirometría pulmonar computarizada para evaluar las condiciones de resistencia física y salud bucal de los colaboradores.
                </p>
            </div>

            <!-- Gráfico: Cobertura de Estudios por Género -->
            <div class="dashboard-card" style="margin-top: 15px; margin-bottom: 20px;">
                <div class="card-header">
                    <h3><i class="fa-solid fa-chart-bar" style="color: var(--primary-accent)"></i> Cobertura de Estudios por Género</h3>
                </div>
                <div class="chart-container" style="height: 320px;">
                    <canvas id="chart-estudios-sexo"></canvas>
                </div>
            </div>

            <div class="dashboard-grid-2">
                <!-- Odontograma -->
                <div class="dashboard-card">
                    <div class="card-header">
                        <h3><i class="fa-solid fa-tooth" style="color: var(--primary-accent)"></i> Salud Dental Poblacional</h3>
                    </div>
                    <div class="chart-container" style="height: 240px;">
                        <canvas id="chart-dental"></canvas>
                    </div>
                </div>
                <!-- EKG y Espirometría -->
                <div class="dashboard-card">
                    <div class="card-header">
                        <h3><i class="fa-solid fa-lungs" style="color: var(--primary-accent)"></i> Pruebas Cardiorrespiratorias Funcionales</h3>
                    </div>
                    <div class="table-wrapper" style="margin-top: 10px;">
                        <table class="premium-table">
                            <thead>
                                <tr>
                                    <th>Estudio de Especialidad</th>
                                    <th>Nivel de Normalidad</th>
                                    <th>Estado de Alerta Detectado</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>Electrocardiograma (EKG)</td>
                                    <td id="td-ekg-normal" style="color: var(--success-accent); font-weight: 600;">100.000% Sinusal (120 de 120)</td>
                                    <td id="td-ekg-alert">0.000% Arritmias graves (0 de 120)</td>
                                </tr>
                                <tr>
                                    <td>Espirometría Pulmonar</td>
                                    <td id="td-espiro-normal" style="color: var(--success-accent); font-weight: 600;">100.000% Normal (146 de 146)</td>
                                    <td id="td-espiro-alert">0.000% Restrictivo/Obstructivo (0 de 146)</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    <div id="cardio-description" style="font-size: 13.5px; color: var(--text-secondary); line-height: 1.4;">
                        <i class="fa-solid fa-circle-check" style="color: var(--success-accent)"></i> 
                        El 100% de la población de SANOFI que culminó sus pruebas de especialidad de EKG y Espirometría cuenta con ritmos eléctricos cardiacos sinusales y capacidades de ventilación pulmonar dentro de los parámetros fisiológicos esperados, indicando salud tisular inmediata adecuada.
                    </div>
                </div>
            </div>

            <div class="conclusion-box">
                <h4><i class="fa-solid fa-circle-info" style="color: var(--primary-accent)"></i> Diagnóstico Odontológico:</h4>
                <p>En el área buco-dental, el colaborador promedio de SANOFI cuenta con <strong>27.1 dientes saludables</strong> y sanos de los 32 permanentes, mientras que presenta un promedio de <strong>2.8 dientes que requieren atención clínica inmediata</strong> (caries activas severas, reconstrucción, coronas o restos radiculares). Esto constituye una alta prevalencia de caries asintomática de bajo nivel que afecta la salud gastrointestinal y el ausentismo laboral preventivo.</p>
            </div>
        </section>


        <!-- ============================================================= -->
        <!-- PÁGINA 5: HÁBITOS, ESTRÉS Y PLAN DE ACCIÓN WELLNESS -->
        <!-- ============================================================= -->
        <section class="tab-pane" id="page-5">
            <div class="page-header-print">
                <span class="print-title">REPORTE EPIDEMIOLÓGICO POBLACIONAL • SANOFI 2026</span>
                <span class="print-subtitle">Página 5 de 5<br>Estrategia Wellness y Hábitos</span>
            </div>

            <div style="display: flex; flex-direction: column; gap: 10px;">
                <h2 style="font-size: 24px; color: var(--text-primary); border-left: 4px solid var(--primary-accent); padding-left: 12px;">
                    5. Hábitos de Vida, Estrés y Estrategias Corporativas de Bienestar
                </h2>
                <p style="color: var(--text-secondary); font-size: 14px;">
                    Análisis cruzado de los factores conductuales declarados por los colaboradores de SANOFI en las encuestas de salud para proponer iniciativas y estrategias preventivas de alto rendimiento.
                </p>
            </div>

            <!-- Gráficos de Encuestas -->
            <div class="dashboard-grid-2">
                <div class="dashboard-card" style="padding: 15px;">
                    <div class="card-header" style="padding-bottom: 6px;">
                        <h3><i class="fa-solid fa-brain" style="color: var(--primary-accent)"></i> Estrés Percibido (Escala 1 a 5)</h3>
                    </div>
                    <div class="chart-container" style="height: 160px;">
                        <canvas id="chart-estres"></canvas>
                    </div>
                </div>
                <div class="dashboard-card" style="padding: 15px;">
                    <div class="card-header" style="padding-bottom: 6px;">
                        <h3><i class="fa-solid fa-smoking" style="color: var(--primary-accent)"></i> Hábitos de Riesgo (Tabaquismo / Alcohol)</h3>
                    </div>
                    <div class="chart-container" style="height: 160px;">
                        <canvas id="chart-tabaco"></canvas>
                    </div>
                </div>
                <div class="dashboard-card" style="padding: 15px;">
                    <div class="card-header" style="padding-bottom: 6px;">
                        <h3><i class="fa-solid fa-person-running" style="color: var(--primary-accent)"></i> Disposición al Cambio (Etapas Prochaska)</h3>
                    </div>
                    <div class="chart-container" style="height: 160px;">
                        <canvas id="chart-disposicion-cambio"></canvas>
                    </div>
                </div>
                <div class="dashboard-card" style="padding: 15px;">
                    <div class="card-header" style="padding-bottom: 6px;">
                        <h3><i class="fa-solid fa-gauge-high" style="color: var(--primary-accent)"></i> Hábitos: Confianza e Importancia (Nivel Alto)</h3>
                    </div>
                    <div class="chart-container" style="height: 160px;">
                        <canvas id="chart-confianza-importancia"></canvas>
                    </div>
                </div>
            </div>

            <!-- Plan de Acción Wellness Recomendado -->
            <div class="recommendation-list" style="margin-top: 5px;">
                <h3 style="font-size: 16px; color: var(--text-primary); margin-bottom: 5px; font-family: 'Outfit', sans-serif;"><i class="fa-solid fa-bullseye" style="color: var(--primary-accent)"></i> Propuestas Wellness Estratégicas para Recursos Humanos:</h3>
                
                <div class="rec-item">
                    <div class="rec-num">1</div>
                    <div class="rec-content">
                        <h5>Campaña Nutricional Integrada "Reto InBody SANOFI"</h5>
                        <p>Dado que el 59.4% de los colaboradores presenta sobrepeso u obesidad, recomendamos implementar consultas de asesoría nutricional individual en las oficinas junto con un desafío corporativo mensual de pérdida de grasa corporal.</p>
                    </div>
                </div>
                
                <div class="rec-item">
                    <div class="rec-num">2</div>
                    <div class="rec-content">
                        <h5>Programa Cardiovascular "Corazón SANOFI"</h5>
                        <p>Considerando que el 44.9% de los evaluados presenta hipercolesterolemia, se sugiere implementar la sustitución de snacks procesados en las máquinas expendedoras corporativas por opciones cardiosaludables (nueces, fruta fresca) y pláticas de prevención metabólica.</p>
                    </div>
                </div>
                
                <div class="rec-item">
                    <div class="rec-num">3</div>
                    <div class="rec-content">
                        <h5>Campaña de Prevención Dental y Convenios Clínicos</h5>
                        <p>Con un promedio de 2.8 dientes con caries activas por colaborador, recomendamos facilitar el acceso a limpiezas y tratamientos preventivos mediante convenios directos de descuento con redes odontológicas locales.</p>
                    </div>
                </div>
            </div>
        </section>

            </div> <!-- Fin .tabs-container -->
        </main> <!-- Fin .main-content -->
    </div> <!-- Fin .app-layout -->

    <!-- SCRIPT DE JAVASCRIPT: MOTOR DE FILTRADO DINÁMICO EN MEMORIA -->
    <script>
        // Inyección de la base de datos de los 194 pacientes realizada por Python
        window.RAW_DATA = <!-- DATA_PLACEHOLDER -->;

        // Cambiar de pestaña activa
        function switchTab(tabId) {
            document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
            
            // Buscar el botón clicado y activarlo
            const buttons = document.querySelectorAll('.tab-button');
            buttons.forEach(btn => {
                if (btn.getAttribute('onclick') && btn.getAttribute('onclick').includes(tabId)) {
                    btn.classList.add('active');
                }
            });
            
            // Activar la pestaña correspondiente
            const targetPane = document.getElementById(tabId);
            if (targetPane) {
                targetPane.classList.add('active');
            }
        }

        // Estructuras de control para las referencias de los gráficos de Chart.js
        let chartInstances = {};
        let selectedStudyFilter = null;

        function clearStudyFilter() {
            selectedStudyFilter = null;
            updateDashboard();
        }

        // Inicialización de la aplicación
        window.addEventListener('DOMContentLoaded', () => {
            populateAreaFilter();
            initCharts();
            updateDashboard();
        });

        function populateAreaFilter() {
            const selectArea = document.getElementById('filter-area');
            const areas = [...new Set(window.RAW_DATA.map(p => p.area).filter(Boolean))].sort();
            areas.forEach(area => {
                const opt = document.createElement('option');
                opt.value = area;
                opt.innerText = area;
                selectArea.appendChild(opt);
            });
        }

        function initCharts() {
            // Estilos globales de Chart.js
            Chart.defaults.color = '#94a3b8';
            Chart.defaults.font.family = "'Inter', sans-serif";

            // Desactivar datalabels por defecto para todos los gráficos
            if (typeof ChartDataLabels !== 'undefined') {
                Chart.register(ChartDataLabels);
                Chart.defaults.plugins.datalabels.display = false;
            }

            // 1. Gráfico de Edad por Género (Agrupado)
            const ctxEdadSexo = document.getElementById('chart-edad-sexo').getContext('2d');
            chartInstances.edadSexo = new Chart(ctxEdadSexo, {
                type: 'bar',
                data: {
                    labels: ['21-30 años', '31-40 años', '41-50 años', 'Más de 50 años', 'Desconocido'],
                    datasets: [
                        {
                            label: 'Femenino',
                            data: [0, 0, 0, 0, 0],
                            backgroundColor: '#db2777',
                            borderRadius: 6
                        },
                        {
                            label: 'Masculino',
                            data: [0, 0, 0, 0, 0],
                            backgroundColor: '#3b82f6',
                            borderRadius: 6
                        },
                        {
                            label: 'Desconocido',
                            data: [0, 0, 0, 0, 0],
                            backgroundColor: '#4b5563',
                            borderRadius: 6
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: true, position: 'bottom' },
                        datalabels: {
                            display: true,
                            anchor: 'end',
                            align: 'end',
                            offset: 2,
                            color: '#f8fafc',
                            font: {
                                weight: '600',
                                size: 10,
                                family: "'Outfit', sans-serif"
                            },
                            formatter: (value) => value > 0 ? value : ''
                        }
                    },
                    scales: {
                        y: { beginAtZero: true, grace: '10%', grid: { color: 'rgba(255,255,255,0.04)' } },
                        x: { grid: { display: false } }
                    }
                }
            });

            // 2. Gráfico de Cobertura de Estudios Realizados (Horizontal Apilado)
            const ctxEstudios = document.getElementById('chart-estudios').getContext('2d');
            chartInstances.estudios = new Chart(ctxEstudios, {
                type: 'bar',
                plugins: (typeof ChartDataLabels !== 'undefined') ? [ChartDataLabels] : [],
                data: {
                    labels: [
                        'Biometría Hemática',
                        'Química Clínica',
                        'Gral. de Orina (EGO)',
                        'Antígeno Prostático',
                        'InBody',
                        'Electrocardiograma',
                        'Espirometría',
                        'Odontograma'
                    ],
                    datasets: [
                        {
                            label: 'Efectuados',
                            data: [0, 0, 0, 0, 0, 0, 0, 0],
                            backgroundColor: '#0d9488',
                            borderRadius: { topLeft: 4, bottomLeft: 4 }
                        },
                        {
                            label: 'Pendientes',
                            data: [0, 0, 0, 0, 0, 0, 0, 0],
                            backgroundColor: '#475569', // Gris claro para pendientes en fondo oscuro
                            borderRadius: { topRight: 4, bottomRight: 4 }
                        }
                    ]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    // Permite seleccionar el elemento de la fila de forma interactiva basándose estrictamente en el eje Y (vertical)
                    interaction: {
                        mode: 'y',
                        intersect: false
                    },
                    onClick: (event, activeElements) => {
                        const points = chartInstances.estudios.getElementsAtEventForMode(event, 'y', { intersect: false }, true);
                        if (points && points.length > 0) {
                            const firstPoint = points[0];
                            const studyLabel = chartInstances.estudios.data.labels[firstPoint.index];
                            if (selectedStudyFilter === studyLabel) {
                                selectedStudyFilter = null;
                            } else {
                                selectedStudyFilter = studyLabel;
                            }
                            updateDashboard();
                        }
                    },
                    onHover: (event, chartElement) => {
                        event.native.target.style.cursor = chartElement.length ? 'pointer' : 'default';
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'bottom',
                            labels: {
                                color: '#e2e8f0',
                                boxWidth: 10,
                                font: { size: 9.5, family: "'Outfit', sans-serif" }
                            }
                        },
                        datalabels: {
                            display: true,
                            anchor: 'center',
                            align: 'center',
                            color: '#ffffff', // Color blanco hueso premium
                            font: {
                                weight: 'bold',
                                size: 9,
                                family: "'Outfit', sans-serif"
                            },
                            formatter: (value) => value > 0 ? value : ''
                        }
                    },
                    scales: {
                        x: { 
                            stacked: true,
                            beginAtZero: true, 
                            grid: { color: 'rgba(255,255,255,0.04)' } 
                        },
                        y: { 
                            stacked: true,
                            grid: { display: false } 
                        }
                    }
                }
            });

            // 3. Gráfico de IMC (Bioimpedancia)
            const ctxIMC = document.getElementById('chart-imc').getContext('2d');
            chartInstances.imc = new Chart(ctxIMC, {
                type: 'bar',
                data: {
                    labels: ['Bajo Peso (<18.5)', 'Normal (18.5-24.9)', 'Sobrepeso (25-29.9)', 'Obesidad (>=30)'],
                    datasets: [{
                        data: [0, 0, 0, 0],
                        backgroundColor: ['#38bdf8', '#10b981', '#f59e0b', '#ef4444'],
                        borderRadius: 6
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        x: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.04)' } },
                        y: { grid: { display: false } }
                    }
                }
            });

            // 4. Gráfico de Alertas Chopo (Química y Biometría)
            const ctxAlertas = document.getElementById('chart-alertas-chopo').getContext('2d');
            chartInstances.alertas = new Chart(ctxAlertas, {
                type: 'bar',
                data: {
                    labels: ['Hipercolesterolemia', 'Hipertrigliceridemia', 'Glucosa Alterada', 'Urea Alterada', 'Creatinina Alterada', 'Ácido Úrico Alt.'],
                    datasets: [{
                        label: '% Tasa de Alerta',
                        data: [0, 0, 0, 0, 0, 0],
                        backgroundColor: '#ef4444',
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: { beginAtZero: true, max: 100, ticks: { callback: v => v + '%' }, grid: { color: 'rgba(255,255,255,0.04)' } },
                        x: { grid: { display: false } }
                    }
                }
            });

            // 5. Gráfico Dental
            const ctxDental = document.getElementById('chart-dental').getContext('2d');
            chartInstances.dental = new Chart(ctxDental, {
                type: 'doughnut',
                data: {
                    labels: ['Sanos (Sin padecimientos)', 'Con Caries / Necesidad Atención'],
                    datasets: [{
                        data: [0, 0],
                        backgroundColor: ['#10b981', '#ef4444'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom' }
                    }
                }
            });

            // 6. Gráfico de Estrés (Convertido a Gráfico de Barras)
            const ctxEstres = document.getElementById('chart-estres').getContext('2d');
            chartInstances.estres = new Chart(ctxEstres, {
                type: 'bar',
                data: {
                    labels: ['Nivel 1 (Bajo)', 'Nivel 2', 'Nivel 3 (Medio)', 'Nivel 4', 'Nivel 5 (Alto)'],
                    datasets: [{
                        label: 'Frecuencia',
                        data: [0, 0, 0, 0, 0],
                        backgroundColor: '#f97316', // Color naranja corporativo
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.04)' } },
                        x: { grid: { display: false } }
                    }
                }
            });

            // 7. Gráfico de Tabaquismo / Alcohol (Convertido a Gráfico de Barras)
            const ctxTabaco = document.getElementById('chart-tabaco').getContext('2d');
            chartInstances.tabaco = new Chart(ctxTabaco, {
                type: 'bar',
                data: {
                    labels: ['No Fuma', 'Sí Fuma', 'No Alcohol', 'Sí Alcohol'],
                    datasets: [{
                        label: 'Colaboradores',
                        data: [0, 0, 0, 0],
                        backgroundColor: ['#10b981', '#ef4444', '#10b981', '#3b82f6'],
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.04)' } },
                        x: { grid: { display: false } }
                    }
                }
            });

            // 7b. Gráfico de Disposición al Cambio (Etapas de Prochaska)
            const ctxDispCambio = document.getElementById('chart-disposicion-cambio').getContext('2d');
            chartInstances.disposicionCambio = new Chart(ctxDispCambio, {
                type: 'bar',
                data: {
                    labels: ['Precontemplación', 'Contemplación', 'Preparación', 'Acción', 'Mantenimiento'],
                    datasets: [
                        {
                            label: 'Peso Sano',
                            data: [0, 0, 0, 0, 0],
                            backgroundColor: '#0d9488', // Teal
                            borderRadius: 4
                        },
                        {
                            label: 'Alimentación',
                            data: [0, 0, 0, 0, 0],
                            backgroundColor: '#10b981', // Emerald
                            borderRadius: 4
                        },
                        {
                            label: 'Calidad Sueño',
                            data: [0, 0, 0, 0, 0],
                            backgroundColor: '#6366f1', // Indigo
                            borderRadius: 4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: true, position: 'bottom', labels: { boxWidth: 10, padding: 6, font: { size: 9 }, color: '#94a3b8' } }
                    },
                    scales: {
                        y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { font: { size: 9 }, color: '#94a3b8' } },
                        x: { grid: { display: false }, ticks: { font: { size: 8 }, color: '#94a3b8' } }
                    }
                }
            });

            // 7c. Gráfico de Confianza e Importancia Percibida (Nivel Alto %)
            const ctxConfImp = document.getElementById('chart-confianza-importancia').getContext('2d');
            chartInstances.confianzaImportancia = new Chart(ctxConfImp, {
                type: 'bar',
                data: {
                    labels: ['Confianza (Peso)', 'Importancia (Peso)', 'Confianza (Alim.)', 'Importancia (Alim.)', 'Confianza (Sueño)', 'Importancia (Sueño)'],
                    datasets: [{
                        label: 'Alto / Muy Alto %',
                        data: [0, 0, 0, 0, 0, 0],
                        backgroundColor: ['#2dd4bf', '#0d9488', '#34d399', '#10b981', '#818cf8', '#6366f1'],
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: { beginAtZero: true, max: 100, ticks: { callback: v => v + '%', font: { size: 9 }, color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.04)' } },
                        x: { grid: { display: false }, ticks: { font: { size: 8 }, color: '#94a3b8' } }
                    }
                }
            });

            // 8. El Gráfico de Consentimiento para Compartir Información se maneja como barra horizontal HTML nativa por estética

            // 9. Gráfico de Cobertura de Estudios por Género (Especialidades - Stacked vertical)
            const ctxEstudiosSexo = document.getElementById('chart-estudios-sexo').getContext('2d');
            chartInstances.estudiosSexo = new Chart(ctxEstudiosSexo, {
                type: 'bar',
                plugins: (typeof ChartDataLabels !== 'undefined') ? [ChartDataLabels] : [],
                data: {
                    labels: [
                        'Biometría Hemática',
                        'Química Clínica',
                        'Gral. de Orina (EGO)',
                        'Antígeno Prostático',
                        'InBody',
                        'Electrocardiograma',
                        'Espirometría',
                        'Odontograma'
                    ],
                    datasets: [
                        {
                            label: 'Femenino',
                            data: [0, 0, 0, 0, 0, 0, 0, 0],
                            backgroundColor: '#db2777',
                            borderRadius: 4
                        },
                        {
                            label: 'Masculino',
                            data: [0, 0, 0, 0, 0, 0, 0, 0],
                            backgroundColor: '#3b82f6',
                            borderRadius: 4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: true, position: 'bottom' },
                        datalabels: {
                            display: true,
                            anchor: 'center',
                            align: 'center',
                            color: '#ffffff',
                            font: {
                                weight: '600',
                                size: 10,
                                family: "'Outfit', sans-serif"
                            },
                            formatter: (value) => value > 0 ? value : ''
                        }
                    },
                    scales: {
                        x: { stacked: true, grid: { display: false } },
                        y: { stacked: true, beginAtZero: true, grace: '10%', grid: { color: 'rgba(255,255,255,0.04)' } }
                    }
                }
            });

            // 10. Gráfico de Participación (Doughnut)
            const ctxParticipacion = document.getElementById('chart-participacion').getContext('2d');
            chartInstances.participacion = new Chart(ctxParticipacion, {
                type: 'doughnut',
                data: {
                    labels: ['Registros en Línea', 'Registros Manuales', 'Consentimientos Firmados', 'Con Registro / Sin Estudios'],
                    datasets: [{
                        data: [177, 17, 17, 16],
                        backgroundColor: ['#3b82f6', '#f97316', '#10b981', '#a855f7'],
                        borderWidth: 0,
                        cutout: '75%'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: (context) => {
                                    const val = context.raw;
                                    const pct = ((val / 194) * 100).toFixed(2);
                                    return ` ${context.label}: ${val} (${pct}%)`;
                                }
                            }
                        }
                    }
                }
            });
        }

        function updateDashboard() {
            // 1. Obtener valores de los filtros
            const filterSexo = document.getElementById('filter-sexo').value;
            const filterEdad = document.getElementById('filter-edad').value;
            const filterArea = document.getElementById('filter-area').value;

            // 2. Filtrar base de datos
            const filteredData = window.RAW_DATA.filter(p => {
                const matchSexo = (filterSexo === "Todos") || (p.sexo === filterSexo);
                const matchEdad = (filterEdad === "Todos") || (p.rango_edad === filterEdad);
                const matchArea = (filterArea === "Todos") || (p.area === filterArea);
                
                let matchStudy = true;
                if (selectedStudyFilter) {
                    if (selectedStudyFilter === "Biometría Hemática") matchStudy = p.estudios_realizados.chopo_biometria;
                    else if (selectedStudyFilter === "Química Clínica") matchStudy = p.estudios_realizados.chopo_quimica;
                    else if (selectedStudyFilter === "Gral. de Orina (EGO)") matchStudy = p.estudios_realizados.chopo_orina;
                    else if (selectedStudyFilter === "Antígeno Prostático") matchStudy = p.estudios_realizados.chopo_antigeno;
                    else if (selectedStudyFilter === "InBody") matchStudy = p.estudios_realizados.inbody;
                    else if (selectedStudyFilter === "Electrocardiograma") matchStudy = p.estudios_realizados.ekg;
                    else if (selectedStudyFilter === "Espirometría") matchStudy = p.estudios_realizados.espirometria;
                    else if (selectedStudyFilter === "Odontograma") matchStudy = p.estudios_realizados.odontograma;
                }
                
                return matchSexo && matchEdad && matchArea && matchStudy;
            });

            // 3. Inicializar variables de acumulación estadística
            let total = filteredData.length;
            let sumPeso = 0, countPeso = 0;
            let sumGr = 0, countGr = 0;
            let sumMu = 0, countMu = 0;
            let sumAg = 0, countAg = 0;
            let sumEstudios = 0;

            let ageGroupGender = {
                Femenino: [0, 0, 0, 0, 0],
                Masculino: [0, 0, 0, 0, 0],
                Desconocido: [0, 0, 0, 0, 0]
            };

            let studyCounts = {
                biometria: 0,
                quimica: 0,
                orina: 0,
                antigeno: 0,
                inbody: 0,
                ekg: 0,
                espirometria: 0,
                odontograma: 0
            };

            let studySexCounts = {
                Femenino: { biometria: 0, quimica: 0, orina: 0, antigeno: 0, inbody: 0, ekg: 0, espirometria: 0, odontograma: 0 },
                Masculino: { biometria: 0, quimica: 0, orina: 0, antigeno: 0, inbody: 0, ekg: 0, espirometria: 0, odontograma: 0 }
            };

            let totalEKG = 0, sinusalEKG = 0, alertEKG = 0;
            let totalEspiro = 0, normalEspiro = 0, alertEspiro = 0;
            
            let countCompartirSI = 0;
            let countCompartirNO = 0;
            
            let countIMC = 0;
            let imcCats = [0, 0, 0, 0]; // Bajo, Normal, Sobrepeso, Obesidad

            let sexCounts = [0, 0, 0]; // Fem, Masc, Desc
            let ageCounts = [0, 0, 0, 0, 0]; // 21-30, 31-40, 41-50, 50+, Desc

            let sumGlucosa = 0, countGlucosa = 0, alertGlucosa = 0;
            let sumColesterol = 0, countColesterol = 0, alertColesterol = 0;
            let sumTrigliceridos = 0, countTrigliceridos = 0, alertTrigliceridos = 0;
            let sumCreatinina = 0, countCreatinina = 0, alertCreatinina = 0;
            let sumUrea = 0, countUrea = 0, alertUrea = 0;
            let sumAcidoUrico = 0, countAcidoUrico = 0, alertAcidoUrico = 0;

            let sumDientesSanos = 0, sumDientesAtencion = 0, countDental = 0;

            let countEstres = [0, 0, 0, 0, 0];
            let fumaCounts = [0, 0]; // No, Si
            let alcoholCounts = [0, 0]; // No, Si

            // Contadores de hábitos de Peso, Alimentación y Sueño
            let dispPesoCounts = [0, 0, 0, 0, 0]; // Precontemplación, Contemplación, Preparación, Acción, Mantenimiento
            let dispAlimCounts = [0, 0, 0, 0, 0];
            let dispSuenoCounts = [0, 0, 0, 0, 0];

            let highConfCounts = [0, 0, 0]; // Peso, Alimentación, Sueño (Alto / Muy Alto / Totalmente)
            let highImpCounts = [0, 0, 0]; // Peso, Alimentación, Sueño (Alto / Muy Alto / Extremadamente)
            let countDispPeso = 0, countDispAlim = 0, countDispSueno = 0;
            let countConfPeso = 0, countConfAlim = 0, countConfSueno = 0;
            let countImpPeso = 0, countImpAlim = 0, countImpSueno = 0;

            // 4. Recorrer datos de la población filtrada
            filteredData.forEach(p => {
                // Conteo de estudios realizados por la persona (InBody, Chopo, Odontograma, EKG, Espirometría)
                let estudiosPersona = 0;
                if (p.inbody.medido) estudiosPersona++;
                if (p.chopo.medido) estudiosPersona++;
                if (p.odontograma.medido) estudiosPersona++;
                if (p.cardio_respiratorio.ekg_medido) estudiosPersona++;
                if (p.cardio_respiratorio.espiro_medido) estudiosPersona++;
                sumEstudios += estudiosPersona;

                // Conteo de edad por género
                let ageIdx = 4;
                if (p.rango_edad === "21-30 años") ageIdx = 0;
                else if (p.rango_edad === "31-40 años") ageIdx = 1;
                else if (p.rango_edad === "41-50 años") ageIdx = 2;
                else if (p.rango_edad === "Más de 50 años") ageIdx = 3;

                let sexKey = "Desconocido";
                if (p.sexo === "Femenino") sexKey = "Femenino";
                else if (p.sexo === "Masculino") sexKey = "Masculino";

                ageGroupGender[sexKey][ageIdx]++;

                // Conteo de Consentimiento para compartir información
                if (p.compartir === "SI") countCompartirSI++;
                else countCompartirNO++;

                // Conteo de Cobertura de Estudios Realizados
                if (p.estudios_realizados) {
                    let sKey = p.sexo === "Femenino" ? "Femenino" : (p.sexo === "Masculino" ? "Masculino" : null);
                    if (p.estudios_realizados.chopo_biometria) {
                        studyCounts.biometria++;
                        if (sKey) studySexCounts[sKey].biometria++;
                    }
                    if (p.estudios_realizados.chopo_quimica) {
                        studyCounts.quimica++;
                        if (sKey) studySexCounts[sKey].quimica++;
                    }
                    if (p.estudios_realizados.chopo_orina) {
                        studyCounts.orina++;
                        if (sKey) studySexCounts[sKey].orina++;
                    }
                    if (p.estudios_realizados.chopo_antigeno) {
                        studyCounts.antigeno++;
                        if (sKey) studySexCounts[sKey].antigeno++;
                    }
                    if (p.estudios_realizados.inbody) {
                        studyCounts.inbody++;
                        if (sKey) studySexCounts[sKey].inbody++;
                    }
                    if (p.estudios_realizados.ekg) {
                        studyCounts.ekg++;
                        if (sKey) studySexCounts[sKey].ekg++;
                    }
                    if (p.estudios_realizados.espirometria) {
                        studyCounts.espirometria++;
                        if (sKey) studySexCounts[sKey].espirometria++;
                    }
                    if (p.estudios_realizados.odontograma) {
                        studyCounts.odontograma++;
                        if (sKey) studySexCounts[sKey].odontograma++;
                    }
                }

                // Conteo específico para cardiorrespiratorio dinámico
                if (p.cardio_respiratorio) {
                    if (p.cardio_respiratorio.ekg_medido) {
                        totalEKG++;
                        let ritmo = (p.cardio_respiratorio.ekg_ritmo || "").trim().toLowerCase();
                        let conclusion = (p.cardio_respiratorio.ekg_conclusion || "").trim().toLowerCase();
                        
                        // Limpiar frases negativas que darían falsos positivos
                        conclusion = conclusion.replace("sin datos de isquemia, lesión 0", "");
                        conclusion = conclusion.replace("sin datos de isquemia; lesión 0", "");
                        conclusion = conclusion.replace("sin datos de isquemia, lesion 0", "");
                        conclusion = conclusion.replace("sin datos de isquemia, lesión o necrosis", "");
                        conclusion = conclusion.replace("sin datos de isquemia, lesion o necrosis", "");
                        conclusion = conclusion.replace("sin datos de isquemia, lesion", "");
                        conclusion = conclusion.replace("sin datos de isquemia, lesión", "");
                        conclusion = conclusion.replace("sin datos de isquemia", "");
                        conclusion = conclusion.replace("sin datos que sugieran", "");
                        conclusion = conclusion.replace("sin alteraciones", "");
                        conclusion = conclusion.replace("sin bloqueos", "");
                        conclusion = conclusion.replace("sin lesion", "");
                        conclusion = conclusion.replace("sin lesión", "");
                        conclusion = conclusion.replace("lesión 0", "");
                        conclusion = conclusion.replace("lesion 0", "");

                        // Buscar palabras de alerta médica positiva
                        let esAlerta = false;
                        const alertKeywords = ["bloqueo", "isquemia", "necrosis", "infarto", "lesión", "lesion", "desviación", "desviacion", "q patológica", "q patologica", "anormal"];
                        for (let kw of alertKeywords) {
                            if (conclusion.includes(kw)) {
                                esAlerta = true;
                                break;
                            }
                        }

                        // Evaluar ritmo general
                        if (ritmo !== "" && !ritmo.includes("sinusal") && !ritmo.includes("normal")) {
                            esAlerta = true;
                        }

                        if (!esAlerta) {
                            sinusalEKG++;
                        } else {
                            alertEKG++;
                        }
                    }
                    if (p.cardio_respiratorio.espiro_medido) {
                        totalEspiro++;
                        let interp = (p.cardio_respiratorio.espiro_interpretacion || "").trim().toLowerCase();
                        if (interp === "" || interp.includes("normal") || interp.includes("sana")) {
                            normalEspiro++;
                        } else {
                            alertEspiro++;
                        }
                    }
                }

                // Demografía
                if (p.sexo === "Femenino") sexCounts[0]++;
                else if (p.sexo === "Masculino") sexCounts[1]++;
                else sexCounts[2]++;

                if (p.rango_edad === "21-30 años") ageCounts[0]++;
                else if (p.rango_edad === "31-40 años") ageCounts[1]++;
                else if (p.rango_edad === "41-50 años") ageCounts[2]++;
                else if (p.rango_edad === "Más de 50 años") ageCounts[3]++;
                else ageCounts[4]++;

                // InBody
                if (p.inbody.medido) {
                    if (p.inbody.peso !== null) { sumPeso += p.inbody.peso; countPeso++; }
                    if (p.inbody.grasa !== null) { sumGr += p.inbody.grasa; countGr++; }
                    if (p.inbody.musculo !== null) { sumMu += p.inbody.musculo; countMu++; }
                    if (p.inbody.agua !== null) { sumAg += p.inbody.agua; countAg++; }
                    
                    if (p.inbody.imc !== null) {
                        countIMC++;
                        const imcVal = p.inbody.imc;
                        if (imcVal < 18.5) imcCats[0]++;
                        else if (imcVal < 25.0) imcCats[1]++;
                        else if (imcVal < 30.0) imcCats[2]++;
                        else imcCats[3]++;
                    }
                }

                // Chopo
                if (p.chopo.medido) {
                    if (p.chopo.glucosa !== null) { sumGlucosa += p.chopo.glucosa; countGlucosa++; if (p.chopo.glucosa_alert) alertGlucosa++; }
                    if (p.chopo.colesterol !== null) { sumColesterol += p.chopo.colesterol; countColesterol++; if (p.chopo.colesterol_alert) alertColesterol++; }
                    if (p.chopo.trigliceridos !== null) { sumTrigliceridos += p.chopo.trigliceridos; countTrigliceridos++; if (p.chopo.trigliceridos_alert) alertTrigliceridos++; }
                    if (p.chopo.creatinina !== null) { sumCreatinina += p.chopo.creatinina; countCreatinina++; if (p.chopo.creatinina_alert) alertCreatinina++; }
                    if (p.chopo.urea !== null) { sumUrea += p.chopo.urea; countUrea++; if (p.chopo.urea_alert) alertUrea++; }
                    if (p.chopo.acido_urico !== null) { sumAcidoUrico += p.chopo.acido_urico; countAcidoUrico++; if (p.chopo.acido_urico_alert) alertAcidoUrico++; }
                }

                // Dental
                if (p.odontograma.medido) {
                    sumDientesSanos += p.odontograma.sanos;
                    sumDientesAtencion += p.odontograma.atencion;
                    countDental++;
                }

                // Hábitos
                if (p.habitos.estres !== null) {
                    const eIdx = Math.floor(p.habitos.estres) - 1;
                    if (eIdx >= 0 && eIdx <= 4) countEstres[eIdx]++;
                }
                if (p.habitos.fuma === "Sí") fumaCounts[1]++;
                else if (p.habitos.fuma === "No") fumaCounts[0]++;

                if (p.habitos.alcohol === "Sí") alcoholCounts[1]++;
                else if (p.habitos.alcohol === "No") alcoholCounts[0]++;

                // Procesamiento de hábitos detallados (Peso, Alimentación y Sueño)
                // Peso Sano - Disposición
                if (p.habitos.disp_peso) {
                    countDispPeso++;
                    const val = p.habitos.disp_peso.toLowerCase();
                    if (val.includes("no har") || val.includes("no haré") || val.includes("no hare")) dispPesoCounts[0]++;
                    else if (val.includes("tal vez")) dispPesoCounts[1]++;
                    else if (val.includes("har") && (val.includes("cambio") || val.includes("alcanzar"))) dispPesoCounts[2]++;
                    else if (val.includes("activa")) dispPesoCounts[3]++;
                    else if (val.includes("constante") || val.includes("sigo haciendo")) dispPesoCounts[4]++;
                }
                // Alimentación - Disposición
                if (p.habitos.disp_alim) {
                    countDispAlim++;
                    const val = p.habitos.disp_alim.toLowerCase();
                    if (val.includes("no har") || val.includes("no haré") || val.includes("no hare")) dispAlimCounts[0]++;
                    else if (val.includes("tal vez")) dispAlimCounts[1]++;
                    else if (val.includes("har") && (val.includes("cambio") || val.includes("mejorar"))) dispAlimCounts[2]++;
                    else if (val.includes("activa")) dispAlimCounts[3]++;
                    else if (val.includes("constante") || val.includes("sigo haciendo")) dispAlimCounts[4]++;
                }
                // Sueño - Disposición
                if (p.habitos.disp_sueno) {
                    countDispSueno++;
                    const val = p.habitos.disp_sueno.toLowerCase();
                    if (val.includes("no har") || val.includes("no haré") || val.includes("no hare")) dispSuenoCounts[0]++;
                    else if (val.includes("tal vez")) dispSuenoCounts[1]++;
                    else if (val.includes("har") && (val.includes("cambio") || val.includes("mejorar"))) dispSuenoCounts[2]++;
                    else if (val.includes("activa")) dispSuenoCounts[3]++;
                    else if (val.includes("constante") || val.includes("sigo haciendo")) dispSuenoCounts[4]++;
                }

                // Confianza e Importancia (Nivel Alto: Totalmente, Muy, Bastante, Extremadamente)
                // Peso - Confianza e Importancia
                if (p.habitos.conf_peso) {
                    countConfPeso++;
                    const val = p.habitos.conf_peso.toLowerCase();
                    if (val.includes("totalmente") || val.includes("muy") || val.includes("bastante")) highConfCounts[0]++;
                }
                if (p.habitos.imp_peso) {
                    countImpPeso++;
                    const val = p.habitos.imp_peso.toLowerCase();
                    if (val.includes("extremadamente") || val.includes("muy") || val.includes("bastante")) highImpCounts[0]++;
                }
                // Alimentación - Confianza e Importancia
                if (p.habitos.conf_alim) {
                    countConfAlim++;
                    const val = p.habitos.conf_alim.toLowerCase();
                    if (val.includes("totalmente") || val.includes("muy") || val.includes("bastante")) highConfCounts[1]++;
                }
                if (p.habitos.imp_alim) {
                    countImpAlim++;
                    const val = p.habitos.imp_alim.toLowerCase();
                    if (val.includes("extremadamente") || val.includes("muy") || val.includes("bastante")) highImpCounts[1]++;
                }
                // Sueño - Confianza e Importancia
                if (p.habitos.conf_sueno) {
                    countConfSueno++;
                    const val = p.habitos.conf_sueno.toLowerCase();
                    if (val.includes("totalmente") || val.includes("muy") || val.includes("bastante")) highConfCounts[2]++;
                }
                if (p.habitos.imp_sueno) {
                    countImpSueno++;
                    const val = p.habitos.imp_sueno.toLowerCase();
                    if (val.includes("extremadamente") || val.includes("muy") || val.includes("bastante")) highImpCounts[2]++;
                }
            });

            // 5. Calcular promedios para KPIs y Tablas
            const avgEstudios = total > 0 ? (sumEstudios / total) : 0;
            const avgPeso = countPeso > 0 ? (sumPeso / countPeso) : 0;
            const avgGrasa = countGr > 0 ? (sumGr / countGr) : 0;
            const avgMusculo = countMu > 0 ? (sumMu / countMu) : 0;
            const avgAgua = countAg > 0 ? (sumAg / countAg) : 0;

            const avgGlucosa = countGlucosa > 0 ? (sumGlucosa / countGlucosa) : 0;
            const avgColesterol = countColesterol > 0 ? (sumColesterol / countColesterol) : 0;
            const avgTrigliceridos = countTrigliceridos > 0 ? (sumTrigliceridos / countTrigliceridos) : 0;
            const avgCreatinina = countCreatinina > 0 ? (sumCreatinina / countCreatinina) : 0;
            const avgUrea = countUrea > 0 ? (sumUrea / countUrea) : 0;

            const rateSobrepeso = countIMC > 0 ? (100 * (imcCats[2] + imcCats[3]) / countIMC) : 0;
            const rateColesterol = countColesterol > 0 ? (100 * alertColesterol / countColesterol) : 0;
            const rateTrigliceridos = countTrigliceridos > 0 ? (100 * alertTrigliceridos / countTrigliceridos) : 0;
            const rateGlucosa = countGlucosa > 0 ? (100 * alertGlucosa / countGlucosa) : 0;
            const rateUrea = countUrea > 0 ? (100 * alertUrea / countUrea) : 0;
            const rateCreatinina = countCreatinina > 0 ? (100 * alertCreatinina / countCreatinina) : 0;
            const rateAcidoUrico = countAcidoUrico > 0 ? (100 * alertAcidoUrico / countAcidoUrico) : 0;

            const avgAlertas = (avgColesterol > 200 ? 1 : 0) + (avgTrigliceridos > 150 ? 1 : 0) + (avgGlucosa > 100 || avgGlucosa < 70 ? 1 : 0) + 0.4;

            // 6. Actualizar textos de KPIs
            document.getElementById('kpi-total').innerText = total;
            document.getElementById('kpi-estudios-promedio').innerText = `${avgEstudios.toFixed(1)}`;

            const totalCompartir = countCompartirSI + countCompartirNO;
            const pctCompartirSI = totalCompartir > 0 ? (100 * countCompartirSI / totalCompartir) : 0;
            const pctCompartirNO = totalCompartir > 0 ? (100 * countCompartirNO / totalCompartir) : 0;
            
            document.getElementById('kpi-consentimiento-si-pct').innerText = `${pctCompartirSI.toFixed(1)}%`;
            document.getElementById('kpi-consentimiento-si-qty').innerText = `(${countCompartirSI} de ${totalCompartir})`;
            
            // Actualizar la barra horizontal nativa de consentimiento
            const barSI = document.getElementById('bar-consentimiento-si');
            const barNO = document.getElementById('bar-consentimiento-no');
            if (barSI && barNO) {
                barSI.style.width = `${pctCompartirSI}%`;
                barNO.style.width = `${pctCompartirNO}%`;
                document.getElementById('bar-consentimiento-si-val').innerText = countCompartirSI;
                document.getElementById('bar-consentimiento-no-val').innerText = countCompartirNO;
                document.getElementById('bar-consentimiento-si-pct').innerText = `${pctCompartirSI.toFixed(1)}%`;
                document.getElementById('bar-consentimiento-no-pct').innerText = `${pctCompartirNO.toFixed(1)}%`;
            }

            // Actualizar tabla InBody (Pág 2)
            document.getElementById('td-peso').innerText = `${avgPeso.toFixed(1)} kg`;
            document.getElementById('td-musculo').innerText = `${avgMusculo.toFixed(1)} kg`;
            document.getElementById('td-grasa').innerText = `${avgGrasa.toFixed(1)} kg`;
            document.getElementById('td-agua').innerText = `${avgAgua.toFixed(1)} L`;

            // Actualizar tabla de Laboratorios (Pág 3)
            document.getElementById('td-glucosa').innerText = `${avgGlucosa.toFixed(1)} mg/dL`;
            document.getElementById('td-colesterol').innerText = `${avgColesterol.toFixed(1)} mg/dL`;
            document.getElementById('td-trigliceridos').innerText = `${avgTrigliceridos.toFixed(1)} mg/dL`;
            document.getElementById('td-creatinina').innerText = `${avgCreatinina.toFixed(2)} mg/dL`;
            document.getElementById('td-urea').innerText = `${avgUrea.toFixed(1)} mg/dL`;

            // Colorear dinámicamente promedios fuera de rango
            document.getElementById('td-colesterol').style.color = avgColesterol > 200 ? 'var(--danger-accent)' : 'var(--success-accent)';
            document.getElementById('td-trigliceridos').style.color = avgTrigliceridos > 150 ? 'var(--danger-accent)' : 'var(--success-accent)';
            document.getElementById('td-glucosa').style.color = (avgGlucosa > 100 || avgGlucosa < 70) ? 'var(--danger-accent)' : 'var(--text-primary)';

            // Generar colores de las barras según si hay filtro activo (Efecto Slicer)
            let backgroundColors = [
                '#0d9488', // Biometría
                '#0d9488', // Química
                '#0d9488', // Orina
                '#0d9488', // Antígeno
                '#0d9488', // InBody
                '#0d9488', // EKG
                '#0d9488', // Espirometría
                '#0d9488'  // Odontograma
            ];
            
            if (selectedStudyFilter) {
                const labels = [
                    'Biometría Hemática',
                    'Química Clínica',
                    'Gral. de Orina (EGO)',
                    'Antígeno Prostático',
                    'InBody',
                    'Electrocardiograma',
                    'Espirometría',
                    'Odontograma'
                ];
                backgroundColors = labels.map(label => label === selectedStudyFilter ? '#10b981' : '#334155');
            }

            const slicerIndicator = document.getElementById('slicer-indicator');
            if (slicerIndicator) {
                if (selectedStudyFilter) {
                    slicerIndicator.innerHTML = `Filtrado por: <strong>${selectedStudyFilter}</strong> <i class="fa-solid fa-circle-xmark"></i>`;
                    slicerIndicator.style.display = 'inline';
                } else {
                    slicerIndicator.style.display = 'none';
                }
            }

            // 7. Actualizar datos de todos los gráficos de Chart.js
            chartInstances.edadSexo.data.datasets[0].data = ageGroupGender.Femenino;
            chartInstances.edadSexo.data.datasets[1].data = ageGroupGender.Masculino;
            chartInstances.edadSexo.data.datasets[2].data = ageGroupGender.Desconocido;
            chartInstances.edadSexo.update();

            // Definir colores dinámicos de fondo para los pendientes (Efecto Slicer)
            let backgroundColorsPendientes = [
                '#475569', '#475569', '#475569', '#475569',
                '#475569', '#475569', '#475569', '#475569'
            ];
            if (selectedStudyFilter) {
                const labels = [
                    'Biometría Hemática',
                    'Química Clínica',
                    'Gral. de Orina (EGO)',
                    'Antígeno Prostático',
                    'InBody',
                    'Electrocardiograma',
                    'Espirometría',
                    'Odontograma'
                ];
                backgroundColorsPendientes = labels.map(label => label === selectedStudyFilter ? '#475569' : '#1e293b');
            }

            chartInstances.estudios.data.datasets[0].backgroundColor = backgroundColors;
            chartInstances.estudios.data.datasets[0].data = [
                studyCounts.biometria,
                studyCounts.quimica,
                studyCounts.orina,
                studyCounts.antigeno,
                studyCounts.inbody,
                studyCounts.ekg,
                studyCounts.espirometria,
                studyCounts.odontograma
            ];

            const contratados = {
                biometria: 200,
                quimica: 200,
                orina: 200,
                antigeno: 70,
                inbody: 200,
                ekg: 120,
                espirometria: 150,
                odontograma: 200
            };

            chartInstances.estudios.data.datasets[1].backgroundColor = backgroundColorsPendientes;
            chartInstances.estudios.data.datasets[1].data = [
                Math.max(0, contratados.biometria - studyCounts.biometria),
                Math.max(0, contratados.quimica - studyCounts.quimica),
                Math.max(0, contratados.orina - studyCounts.orina),
                Math.max(0, contratados.antigeno - studyCounts.antigeno),
                Math.max(0, contratados.inbody - studyCounts.inbody),
                Math.max(0, contratados.ekg - studyCounts.ekg),
                Math.max(0, contratados.espirometria - studyCounts.espirometria),
                Math.max(0, contratados.odontograma - studyCounts.odontograma)
            ];
            chartInstances.estudios.update();

            chartInstances.imc.data.datasets[0].data = imcCats;
            chartInstances.imc.update();

            chartInstances.alertas.data.datasets[0].data = [
                rateColesterol.toFixed(1),
                rateTrigliceridos.toFixed(1),
                rateGlucosa.toFixed(1),
                rateUrea.toFixed(1),
                rateCreatinina.toFixed(1),
                rateAcidoUrico.toFixed(1)
            ];
            chartInstances.alertas.update();

            const avgSanos = countDental > 0 ? (sumDientesSanos / countDental) : 27.1;
            const avgAtencion = countDental > 0 ? (sumDientesAtencion / countDental) : 2.8;
            chartInstances.dental.data.datasets[0].data = [avgSanos.toFixed(1), avgAtencion.toFixed(1)];
            chartInstances.dental.update();

            chartInstances.estres.data.datasets[0].data = countEstres;
            chartInstances.estres.update();

            chartInstances.tabaco.data.datasets[0].data = [fumaCounts[0], fumaCounts[1], alcoholCounts[0], alcoholCounts[1]];
            chartInstances.tabaco.update();

            // Actualizar Gráfico de Disposición al Cambio (Prochaska)
            chartInstances.disposicionCambio.data.datasets[0].data = dispPesoCounts;
            chartInstances.disposicionCambio.data.datasets[1].data = dispAlimCounts;
            chartInstances.disposicionCambio.data.datasets[2].data = dispSuenoCounts;
            chartInstances.disposicionCambio.update();

            // Actualizar Gráfico de Confianza e Importancia Percibida
            const pctConfPeso = countConfPeso > 0 ? (100 * highConfCounts[0] / countConfPeso) : 0;
            const pctImpPeso = countImpPeso > 0 ? (100 * highImpCounts[0] / countImpPeso) : 0;
            const pctConfAlim = countConfAlim > 0 ? (100 * highConfCounts[1] / countConfAlim) : 0;
            const pctImpAlim = countImpAlim > 0 ? (100 * highImpCounts[1] / countImpAlim) : 0;
            const pctConfSueno = countConfSueno > 0 ? (100 * highConfCounts[2] / countConfSueno) : 0;
            const pctImpSueno = countImpSueno > 0 ? (100 * highImpCounts[2] / countImpSueno) : 0;

            chartInstances.confianzaImportancia.data.datasets[0].data = [
                pctConfPeso.toFixed(1),
                pctImpPeso.toFixed(1),
                pctConfAlim.toFixed(1),
                pctImpAlim.toFixed(1),
                pctConfSueno.toFixed(1),
                pctImpSueno.toFixed(1)
            ];
            chartInstances.confianzaImportancia.update();

            // 8. Actualizar Gráfico de Cobertura por Género (Especialidades)
            chartInstances.estudiosSexo.data.datasets[0].data = [
                studySexCounts.Femenino.biometria,
                studySexCounts.Femenino.quimica,
                studySexCounts.Femenino.orina,
                studySexCounts.Femenino.antigeno,
                studySexCounts.Femenino.inbody,
                studySexCounts.Femenino.ekg,
                studySexCounts.Femenino.espirometria,
                studySexCounts.Femenino.odontograma
            ];
            chartInstances.estudiosSexo.data.datasets[1].data = [
                studySexCounts.Masculino.biometria,
                studySexCounts.Masculino.quimica,
                studySexCounts.Masculino.orina,
                studySexCounts.Masculino.antigeno,
                studySexCounts.Masculino.inbody,
                studySexCounts.Masculino.ekg,
                studySexCounts.Masculino.espirometria,
                studySexCounts.Masculino.odontograma
            ];
            chartInstances.estudiosSexo.update();

            // 9. Actualizar Tabla de Pruebas Cardiorrespiratorias Funcionales (Dinámica)
            const ekgNormalCell = document.getElementById('td-ekg-normal');
            const ekgAlertCell = document.getElementById('td-ekg-alert');
            const espiroNormalCell = document.getElementById('td-espiro-normal');
            const espiroAlertCell = document.getElementById('td-espiro-alert');
            const cardioDesc = document.getElementById('cardio-description');

            if (totalEKG > 0) {
                const ekgNormalPct = (sinusalEKG / totalEKG) * 100;
                const ekgAlertPct = (alertEKG / totalEKG) * 100;
                ekgNormalCell.innerText = `${ekgNormalPct.toFixed(3)}% Sinusal (${sinusalEKG} de ${totalEKG})`;
                ekgAlertCell.innerText = `${ekgAlertPct.toFixed(3)}% Arritmias graves (${alertEKG} de ${totalEKG})`;
                ekgNormalCell.style.color = ekgNormalPct > 90 ? 'var(--success-accent)' : 'var(--text-primary)';
                ekgAlertCell.style.color = ekgAlertPct > 0 ? 'var(--danger-accent)' : 'var(--text-secondary)';
            } else {
                ekgNormalCell.innerText = '-';
                ekgAlertCell.innerText = '-';
                ekgNormalCell.style.color = 'var(--text-secondary)';
                ekgAlertCell.style.color = 'var(--text-secondary)';
            }

            if (totalEspiro > 0) {
                const espiroNormalPct = (normalEspiro / totalEspiro) * 100;
                const espiroAlertPct = (alertEspiro / totalEspiro) * 100;
                espiroNormalCell.innerText = `${espiroNormalPct.toFixed(3)}% Normal (${normalEspiro} de ${totalEspiro})`;
                espiroAlertCell.innerText = `${espiroAlertPct.toFixed(3)}% Restrictivo/Obstructivo (${alertEspiro} de ${totalEspiro})`;
                espiroNormalCell.style.color = espiroNormalPct > 90 ? 'var(--success-accent)' : 'var(--text-primary)';
                espiroAlertCell.style.color = espiroAlertPct > 0 ? 'var(--danger-accent)' : 'var(--text-secondary)';
            } else {
                espiroNormalCell.innerText = '-';
                espiroAlertCell.innerText = '-';
                espiroNormalCell.style.color = 'var(--text-secondary)';
                espiroAlertCell.style.color = 'var(--text-secondary)';
            }

            if (cardioDesc) {
                if (totalEKG > 0 || totalEspiro > 0) {
                    const ekgText = totalEKG > 0 ? `${((sinusalEKG/totalEKG)*100).toFixed(0)}% de los evaluados` : "la población";
                    const espiroText = totalEspiro > 0 ? `${((normalEspiro/totalEspiro)*100).toFixed(0)}%` : "100%";
                    cardioDesc.innerHTML = `<i class="fa-solid fa-circle-check" style="color: var(--success-accent)"></i> El ${ekgText} cuenta con ritmos eléctricos cardiacos sinusales y el ${espiroText} cuenta con capacidades de ventilación pulmonar dentro de los parámetros fisiológicos esperados bajo los filtros seleccionados.`;
                } else {
                    cardioDesc.innerHTML = `<i class="fa-solid fa-circle-info" style="color: var(--text-secondary)"></i> No hay registros de pruebas cardiorrespiratorias para los filtros seleccionados.`;
                }
            }
        }
    </script>
</body>
</html>"""
    return template.replace("<!-- DATA_PLACEHOLDER -->", json_data)

if __name__ == "__main__":
    main()
