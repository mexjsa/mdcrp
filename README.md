# Med&Corp CheckUp - Sistema de Reportes Epidemiológicos

Este repositorio contiene el conjunto de herramientas de automatización clínica desarrolladas para procesar, consolidar y visualizar la información epidemiológica del programa de Check-Up Corporativo.

## 📋 Estructura del Proyecto

*   `Generador_Reporte_Estadistico.py`: Orquestador principal que consolida el máster de datos y compila el dashboard interactivo premium.
*   `Generador_Reportes_PDF.py`: Motor de renderizado en PDF para los reportes clínicos individuales de cada colaborador.
*   `Integrador_Maestro.py`: Módulo de integración de datos maestros.
*   `Orquestador_Final.py`: Flujo general de orquestación.
*   `excel_lab_integrator.py` y `lab_extractor_native.py`: Scripts de extracción e integración de resultados de laboratorios externos.
*   `odontogram_drawer.py`: Motor gráfico interactivo para dibujar patologías en el odontograma.
*   `template_checkup_final.html`: Plantilla base HTML de alta fidelidad utilizada para compilar reportes.

## 🛠️ Requisitos de Ejecución

El sistema está construido en Python 3 y requiere las siguientes dependencias:

```bash
pip install pandas openpyxl pillow jinja2
```

## ⚙️ Uso y Compilación

Para compilar y actualizar el dashboard de visualización epidemiológica a partir de la base de datos Excel consolidada, ejecuta:

```bash
python Generador_Reporte_Estadistico.py
```

## 🔒 Privacidad y Seguridad de Datos

De acuerdo con la legislación mexicana (LFPDPPP), este repositorio **excluye explícitamente** bases de datos Excel (`.xlsx`), archivos individuales de resultados clínicos, ejecutables locales de extracción de datos, y los entregables compilados finales que contengan registros médicos directos o indirectos para resguardar la confidencialidad de los colaboradores.
