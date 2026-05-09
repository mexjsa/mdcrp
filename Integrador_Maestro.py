import pandas as pd
import glob
import os
import re
import unicodedata

def normalize_name(name):
    if pd.isna(name): return ""
    name = str(name).strip().upper()
    # Remove accents
    name = ''.join(c for c in unicodedata.normalize('NFD', name) if unicodedata.category(c) != 'Mn')
    # Remove special chars and extra spaces
    name = re.sub(r'[^A-Z0-9\s]', '', name)
    name = re.sub(r'\s+', ' ', name)
    
    # Sort name parts alphabetically to match regardless of First Last vs Last First order
    parts = sorted(name.split())
    return ' '.join(parts)

base_dir = r"C:\Users\Juan\Dropbox\Proyectos 2026\Med&Corp\CheckUp"

# 1. Load Master
master_files = glob.glob(os.path.join(base_dir, "PERSONAL SANOFI", "check_up_med&corp*.xlsx"))
if not master_files:
    raise FileNotFoundError("No se encontró ningún archivo de Check-Up en PERSONAL SANOFI")
# Exclude temporary files starting with ~$
master_files = [f for f in master_files if not os.path.basename(f).startswith("~$")]
master_path = max(master_files, key=os.path.getmtime)
print(f"Cargando archivo maestro: {master_path}")
df_master = pd.read_excel(master_path, sheet_name=0)

# Normalize and keep master p10 values as official RFC keys (to match InBody and SANOFI lists)
if 'p10' not in df_master.columns and 'RFC' in df_master.columns:
    df_master['p10'] = df_master['RFC']
df_master['p10_orig'] = df_master['p10'].dropna().astype(str).str.strip().str.upper()
df_master['p10'] = df_master['p10_orig'].str[:10]

# Eliminar filas duplicadas por p10 en el master, conservando la que tiene más columnas llenas
if df_master['p10'].duplicated().any():
    print("  [Depuración SANOFI] Detectados duplicados en el listado maestro de SANOFI. Resolviendo...")
    df_master['non_null_count'] = df_master.notna().sum(axis=1)
    df_master = df_master.sort_values(by=['p10', 'non_null_count'], ascending=[True, False])
    df_master = df_master.drop_duplicates(subset=['p10'], keep='first')
    df_master = df_master.drop(columns=['non_null_count'])
    print(f"  [Depuración SANOFI] Listado maestro depurado. Total de registros SANOFI únicos: {len(df_master)}")

# 2. Load Chopo (Wide Format)
chopo_files = glob.glob(os.path.join(base_dir, "ESTUDIOS AGREGADOS", "ESTUDIOS CHOPO", "*.xlsx"))
chopo_files = [f for f in chopo_files if not os.path.basename(f).startswith("~$")]
wide_chopo_files = []
for f in chopo_files:
    try:
        df_head = pd.read_excel(f, header=3, nrows=2)
        if 'Examen' not in df_head.columns and 'Exámen' not in df_head.columns and 'Exmen' not in df_head.columns:
            wide_chopo_files.append(f)
    except Exception as e:
        pass

if wide_chopo_files:
    latest_chopo = max(wide_chopo_files, key=os.path.getmtime)
    print(f"Cargando archivo CHOPO: {latest_chopo}")
    df_chopo = pd.read_excel(latest_chopo, header=3)
    
    chopo_col = 'P10' if 'P10' in df_chopo.columns else 'p10'
    
    # Pre-calcular nombres normalizados en el listado maestro SANOFI
    df_master['norm_name'] = df_master['nombre'].apply(normalize_name)
    master_p10_set = set(df_master['p10'].str.upper())
    
    # Mapeo manual para casos extremos de CHOPO donde el nombre varía considerablemente
    chopo_manual_mapping = {
        'MARJ860901': 'JAMA860901', # Julia Ana Marcelino Ramos
        'ALPM891031': 'AAPM891031', # Montcerrat Alvarez Patiño
        'ANSA690613': 'GOXA690613', # Alusio Andrade Sin Apellido
        'ROSN820829': 'ROBN820829', # Nahum Rodriguez Sin Apellido
        'ISDD841129': 'DEVD841129', # David Issac Delgado
        'RAMN760609': 'NMRM760609'  # Nadia Marcela Ramirez Mungia (Mungia vs Munguia)
    }
    
    # Crear un mapeo dinámico basado en nombres para corregir errores de dedo en RFC de CHOPO
    chopo_key_mapping = chopo_manual_mapping.copy()
    for idx, row in df_chopo.iterrows():
        raw_p10 = str(row.get(chopo_col, '')).strip().upper()
        if raw_p10 in master_p10_set or raw_p10 in chopo_key_mapping:
            continue  # Coincidencia perfecta de RFC o ya mapeado manualmente
            
        first = str(row.get("Nombre", "")).strip()
        p_last = str(row.get("Apellido paterno", "")).strip()
        m_last = str(row.get("Apellido materno", "")).strip()
        chopo_name = normalize_name(f"{first} {p_last} {m_last}")
        
        parts = [p for p in chopo_name.split() if len(p) > 2]
        if not parts:
            continue
            
        # Buscar en SANOFI un nombre que contenga todas las partes
        match = df_master[df_master['norm_name'].apply(lambda x: all(p in x for p in parts))]
        if not match.empty:
            matched_p10 = match.iloc[0]['p10']
            chopo_key_mapping[raw_p10] = matched_p10
            print(f"  [Auto-Corrección CHOPO] Mapeando {raw_p10} a {matched_p10} por coincidencia de nombre: '{first} {p_last} {m_last}'")
            
    # Aplicar el mapeo dinámico a CHOPO
    df_chopo['p10_key'] = df_chopo[chopo_col].astype(str).str.strip().str.upper()
    df_chopo['p10_key_mapped'] = df_chopo['p10_key'].map(chopo_key_mapping).fillna(df_chopo['p10_key'])
    
    # Eliminar columnas que no necesitamos y que causarían conflictos
    cols_to_drop = [c for c in ['Nombre', 'Apellido paterno', 'Apellido materno', 'Edad', 'Gnero', 'Gero', 'Gényero', 'Fecha de nacimiento', 'p10', 'P10', 'ao', 'mes', 'dia', 'ao'] if c in df_chopo.columns]
    df_chopo = df_chopo.drop(columns=cols_to_drop)
    
    df_chopo = df_chopo.add_prefix('CHOPO_')
    df_chopo['p10'] = df_chopo['CHOPO_p10_key_mapped']
    df_chopo = df_chopo.drop(columns=['CHOPO_p10_key', 'CHOPO_p10_key_mapped'])
    
    df_chopo = df_chopo.groupby('p10', as_index=False).first()
    df_master = pd.merge(df_master, df_chopo, on='p10', how='left')
    
    # Limpiar columnas auxiliares del master
    if 'norm_name' in df_master.columns:
        df_master = df_master.drop(columns=['norm_name'])

# 3. Load InBody (Concentrado)
inbody_path = os.path.join(base_dir, "ESTUDIOS AGREGADOS", "IN BODY", "Concentrado INBODY 27 AL 30 ABRIL 2026.xlsm")
if os.path.exists(inbody_path):
    print(f"Cargando archivo INBODY: {inbody_path}")
    df_inbody = pd.read_excel(inbody_path)
    
    ib_col = 'P10' if 'P10' in df_inbody.columns else 'p10'
    df_inbody['p10_key'] = df_inbody[ib_col].astype(str).str.strip().str.upper()
    
    # Drop unneeded columns
    cols_to_drop = [c for c in ['1. Nombre', '2. ID', '3. Nmero de telfono mvil', '4. Edad', '5. Sexo', '6. Altura', '7. Correo electrnico', '9. Fecha / Hora de la prueba', 'p10', 'P10'] if c in df_inbody.columns]
    df_inbody = df_inbody.drop(columns=cols_to_drop)
    
    df_inbody = df_inbody.add_prefix('INBODY_')
    df_inbody['p10'] = df_inbody['INBODY_p10_key']
    df_inbody = df_inbody.drop(columns=['INBODY_p10_key'])
    
    df_inbody = df_inbody.drop_duplicates(subset=['p10'])
    df_master = pd.merge(df_master, df_inbody, on='p10', how='left')

# 4. Load Individuales
individual_folders = ["ELECTROCARDIOGRAMA", "ESPIROMETRIA", "ODONTOGRAMA"]
for folder in individual_folders:
    files = glob.glob(os.path.join(base_dir, "ESTUDIOS INDIVIDUALES", folder, "*.xlsx"))
    if files:
        latest_file = max(files, key=os.path.getmtime)
        print(f"Cargando consolidado {folder}: {latest_file}")
        df_ind = pd.read_excel(latest_file)
        
        if 'Archivo_Origen' in df_ind.columns:
            df_ind['p10_key'] = df_ind['Archivo_Origen'].astype(str).str.replace(r'\.pdf$', '', regex=True, flags=re.IGNORECASE).str.strip().str.upper()
            
            # Mapear claves de archivos individuales de regreso a los RFCs oficiales de SANOFI
            individual_key_mapping = {
                'RAMN760609': 'NMRM760609', # Nadia Marcela Ramirez Mungia
                'VAMA850616': 'AVME850616', # Abigail Vallejo Medina
                'RORD90082': 'RORD900824',  # Diana Lizette Rodriguez Rodriguez
                'RORD900824': 'RORD900824',
                'VIGO781201': 'VIXG781201', # Gonzalo Javier Viton
                'VIXG781201': 'VIXG781201',
                'MOTD81102': 'MOTD81102M'   # Daniela Molina Torres
            }
            df_ind['p10_key'] = df_ind['p10_key'].map(individual_key_mapping).fillna(df_ind['p10_key'])
            
            cols_to_drop = [c for c in ['Paciente_Nombre', 'CURP_ID', 'Tipo_Estudio', 'Edad', 'Sexo', 'Norm_Name', 'Cleaned_Name'] if c in df_ind.columns]
            df_ind = df_ind.drop(columns=cols_to_drop)
            
            df_ind = df_ind.add_prefix(f'{folder}_')
            df_ind['p10'] = df_ind[f'{folder}_p10_key']
            df_ind = df_ind.drop(columns=[f'{folder}_p10_key'])
            
            df_ind = df_ind.drop_duplicates(subset=['p10'])
            df_master = pd.merge(df_master, df_ind, on='p10', how='left')

# 5. Add Image paths for Odonto and EKG
df_master['ODONTOGRAMA_Imagen_Path'] = ''
df_master['ELECTROCARDIOGRAMA_Imagen_Path'] = ''

# Search for images in ODONTOGRAMA
individual_key_mapping = {
    'RAMN760609': 'NMRM760609', # Nadia Marcela Ramirez Mungia
    'VAMA850616': 'AVME850616', # Abigail Vallejo Medina
    'RORD90082': 'RORD900824',  # Diana Lizette Rodriguez Rodriguez
    'RORD900824': 'RORD900824',
    'VIGO781201': 'VIXG781201', # Gonzalo Javier Viton
    'VIXG781201': 'VIXG781201',
    'MOTD81102': 'MOTD81102M'   # Daniela Molina Torres
}
odonto_imgs = glob.glob(os.path.join(base_dir, "ESTUDIOS INDIVIDUALES", "ODONTOGRAMA", "*.png"))
for img in odonto_imgs:
    basename = os.path.basename(img).replace(".png", "")
    p10_img = basename.strip().upper()
    p10_img_mapped = individual_key_mapping.get(p10_img, p10_img)
    idx = df_master[df_master['p10'] == p10_img_mapped].index
    if len(idx) > 0:
        df_master.loc[idx, 'ODONTOGRAMA_Imagen_Path'] = img

# Search for images in ELECTROCARDIOGRAMA
ekg_imgs = glob.glob(os.path.join(base_dir, "ESTUDIOS INDIVIDUALES", "ELECTROCARDIOGRAMA", "*.jpg"))
for img in ekg_imgs:
    basename = os.path.basename(img).replace(".jpg", "")
    p10_img = basename.strip().upper()
    p10_img_mapped = individual_key_mapping.get(p10_img, p10_img)
    idx = df_master[df_master['p10'] == p10_img_mapped].index
    if len(idx) > 0:
        df_master.loc[idx, 'ELECTROCARDIOGRAMA_Imagen_Path'] = img

# Restore original p10 values if needed, or drop temp columns
df_master = df_master.drop(columns=['p10_orig'])

output_path = os.path.join(base_dir, "MASTER_CONSOLIDADO_MEDCORP.xlsx")
df_master.to_excel(output_path, index=False)

# Validation print
matched_chopo = df_master['CHOPO_Folio'].notna().sum()
matched_inbody = df_master['INBODY_10. Peso'].notna().sum() if 'INBODY_10. Peso' in df_master.columns else 0
matched_ekg = df_master['ELECTROCARDIOGRAMA_Ritmo'].notna().sum() if 'ELECTROCARDIOGRAMA_Ritmo' in df_master.columns else 0
matched_espiro = df_master['ESPIROMETRIA_FVC [L]_Mejor'].notna().sum() if 'ESPIROMETRIA_FVC [L]_Mejor' in df_master.columns else 0
matched_odonto = df_master['ODONTOGRAMA_Fecha_Estudio'].notna().sum() if 'ODONTOGRAMA_Fecha_Estudio' in df_master.columns else 0

print(f"Master consolidado creado exitosamente en: {output_path}")
print(f"Total registros en SANOFI: {len(df_master)}")
print(f"Matches CHOPO: {matched_chopo}")
print(f"Matches INBODY: {matched_inbody}")
print(f"Matches EKG: {matched_ekg}")
print(f"Matches ESPIROMETRIA: {matched_espiro}")
print(f"Matches ODONTOGRAMA: {matched_odonto}")

img_ekg_count = (df_master['ELECTROCARDIOGRAMA_Imagen_Path'] != '').sum()
img_odonto_count = (df_master['ODONTOGRAMA_Imagen_Path'] != '').sum()
print(f"Rutas de imagen EKG insertadas: {img_ekg_count}")
print(f"Rutas de imagen ODONTO insertadas: {img_odonto_count}")

