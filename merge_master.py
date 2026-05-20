"""
merge_master.py
---------------
Actualiza MASTER_CONSOLIDADO_MEDCORP.xlsx con los datos correctos del archivo
de referencia (20260512 MASTER_CONSOLIDADO_MEDCORP v0.xlsx).

Columnas que se sincronizan (fuente: primeras columnas del archivo de referencia,
NO del INBODY):
  - id_usuario
  - CURP
  - sexo
  - Telefono
  - correo
  - ELECTROCARDIOGRAMA_Observaciones
  - ELECTROCARDIOGRAMA_Conclusion

Llave de unión: columna p10 (RFC del paciente, primeros 10 chars, mayúsculas).

Solo se procesan los 165 pacientes del archivo de referencia (que son los que
dieron consentimiento). El resto permanece igual en el maestro.
"""

import pandas as pd
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
MASTER = os.path.join(BASE, "MASTER_CONSOLIDADO_MEDCORP.xlsx")
REF    = os.path.join(BASE, "20260512 MASTER_CONSOLIDADO_MEDCORP v0.xlsx")
OUT    = MASTER  # Sobreescribimos el mismo archivo

print("=" * 65)
print("  MED&CORP - Merge de datos demograficos y clinicos")
print("=" * 65)

# -- Cargar archivos ----------------------------------------------
print(f"Cargando maestro actual:    {os.path.basename(MASTER)}")
df_master = pd.read_excel(MASTER)
print(f"  {len(df_master)} filas, {len(df_master.columns)} columnas")

print(f"\nCargando archivo referencia: {os.path.basename(REF)}")
df_ref = pd.read_excel(REF)
print(f"  {len(df_ref)} filas, {len(df_ref.columns)} columnas")

# -- Normalizar llave de union (p10 / RFC) -----------------------
def norm_rfc(val):
    if pd.isna(val):
        return ""
    return str(val).strip().upper()[:10]

# Maestro usa columna 'p10', referencia usa columna 'RFC'
master_key_col = 'p10' if 'p10' in df_master.columns else 'RFC'
ref_key_col    = 'RFC' if 'RFC' in df_ref.columns else 'p10'
print(f"\nLlave en maestro: '{master_key_col}' | Llave en referencia: '{ref_key_col}'")
df_master['_key'] = df_master[master_key_col].apply(norm_rfc)
df_ref['_key']    = df_ref[ref_key_col].apply(norm_rfc)

# Construir diccionario de referencia: key -> row
ref_dict = {row['_key']: row for _, row in df_ref.iterrows() if row['_key']}

# ── Columnas demográficas a copiar desde referencia ─────────────
# IMPORTANTE: NO tomamos correo ni teléfono del INBODY.
# Los correctos vienen de las primeras columnas del archivo de referencia.
DEMO_COLS = ['id_usuario', 'CURP', 'sexo', 'Telefono', 'correo']

# Columnas clínicas ECG
EKG_COLS = ['ELECTROCARDIOGRAMA_Observaciones', 'ELECTROCARDIOGRAMA_Conclusion']

ALL_COLS = DEMO_COLS + EKG_COLS

# Filtrar solo las que existen en el archivo de referencia
cols_to_update = [c for c in ALL_COLS if c in df_ref.columns]
cols_missing   = [c for c in ALL_COLS if c not in df_ref.columns]
if cols_missing:
    print(f"\n[AVISO] Las siguientes columnas no están en el archivo de referencia: {cols_missing}")

print(f"\nColumnas que se actualizarán: {cols_to_update}")

# ── Aplicar merge fila por fila ──────────────────────────────────
updated = 0
skipped_no_key = 0
skipped_no_ref = 0
changes_log = []

for idx, master_row in df_master.iterrows():
    key = master_row['_key']
    if not key:
        skipped_no_key += 1
        continue

    if key not in ref_dict:
        skipped_no_ref += 1
        continue

    ref_row = ref_dict[key]
    changed_fields = []

    for col in cols_to_update:
        ref_val = ref_row.get(col)
        current_val = master_row.get(col)

        # Solo actualizar si el valor de referencia es válido (no nulo)
        if pd.isna(ref_val) or str(ref_val).strip() in ['', 'nan', 'NaN']:
            continue

        # Actualizar si el valor actual está vacío O si difiere
        current_empty = pd.isna(current_val) or str(current_val).strip() in ['', 'nan', 'NaN']
        ref_str = str(ref_val).strip()
        cur_str = str(current_val).strip() if not current_empty else ''

        if current_empty or cur_str != ref_str:
            df_master.at[idx, col] = ref_val
            changed_fields.append(f"{col}: '{cur_str}' → '{ref_str}'")

    if changed_fields:
        updated += 1
        changes_log.append((key, master_row.get('nombre', ''), changed_fields))

# ── Guardar ──────────────────────────────────────────────────────
# Eliminar columna auxiliar antes de guardar
df_master.drop(columns=['_key'], inplace=True)

print(f"\nResumen del merge:")
print(f"  Filas actualizadas:          {updated}")
print(f"  Filas sin clave p10:         {skipped_no_key}")
print(f"  Filas sin coincidencia ref:  {skipped_no_ref}")
print(f"  Total de filas en maestro:   {len(df_master)}")

if changes_log:
    print(f"\nDetalle de cambios (primeros 20):")
    for key, nombre, fields in changes_log[:20]:
        print(f"  [{key}] {nombre}")
        for f in fields:
            print(f"    · {f}")

print(f"\nGuardando maestro actualizado en: {OUT}")
df_master.to_excel(OUT, index=False)
print("✔  Archivo guardado correctamente.")
print("=" * 65)
