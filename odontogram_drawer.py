import os
from PIL import Image, ImageDraw

def generate_marked_odontogram(record, output_path, base_img_path):
    """
    Genera el odontograma con SEMAFORIZACIÓN y puntos en el CENTROIDE de cada corona.
    """
    try:
        if not os.path.exists(base_img_path):
            return False
            
        img = Image.open(base_img_path).convert("RGBA")
        draw = ImageDraw.Draw(img)
        
        # Diccionario de Centroides Manuales (Coordenadas X, Y para imagen 1024x1024)
        # Basado en la anatomía del diagrama premium
        centroids = {
            # SUPERIOR (Izquierda a Derecha del espectador: 18 a 28)
            "dp18": (290, 430), "dp17": (310, 360), "dp16": (330, 300), "dp15": (350, 250),
            "dp14": (385, 210), "dp13": (430, 180), "dp12": (475, 170), "dp11": (475, 170),
            "dp21": (525, 170), "dp22": (575, 180), "dp23": (620, 210), "dp24": (655, 250),
            "dp25": (655, 250), "dp26": (675, 300), "dp27": (695, 360), "dp28": (715, 430),
            
            # INFERIOR (Izquierda a Derecha del espectador: 48 a 38)
            "dp48": (290, 570), "dp47": (310, 640), "dp46": (330, 700), "dp45": (350, 750),
            "dp44": (385, 790), "dp43": (430, 820), "dp42": (475, 830), "dp41": (525, 830),
            "dp31": (575, 830), "dp32": (620, 820), "dp33": (655, 790), "dp34": (675, 750),
            "dp35": (695, 700), "dp36": (715, 640), "dp37": (715, 640), "dp38": (725, 570)
        }
        
        def get_color_severity(value):
            """
            Semaforización según el código de Med&Corp:
            Rojo: 1, 2, 3, 5
            Amarillo: 4, 7, 9
            Ninguno: 0, 6, 8, '-'
            """
            val_str = str(value).strip()
            
            # Casos Graves (ROJO)
            if val_str in ["1", "2", "3", "5"]:
                return (210, 41, 54, 210), (130, 0, 0, 255) # Fill, Outline
                
            # Casos Leves (AMARILLO)
            if val_str in ["4", "7", "9"]:
                return (255, 215, 0, 210), (180, 150, 0, 255) # Fill, Outline
                
            return None, None

        # Procesar cada diente en el registro
        for tooth_id, coords in centroids.items():
            # Buscar primero con el prefijo "p" (ej. "p31"), fallando de regreso a "dp31"
            p_id = tooth_id.replace("dp", "p")
            val = record.get(p_id)
            if val is None or str(val).strip() in ["", "0", "0.0"]:
                val = record.get(tooth_id, "0")
                
            fill_color, edge_color = get_color_severity(val)
            
            if fill_color:
                x, y = coords
                r = 18 # Tamaño ideal del punto para el centroide
                draw.ellipse([x-r, y-r, x+r, y+r], fill=fill_color, outline=edge_color, width=2)
            
        img.save(output_path, "PNG")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False
