#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
MÓDULO: GENERADOR DE PLANILLA OFICIAL ODS (generador_planilla.py)
===============================================================================
Sistema   : JsBOT (Robotic Process Automation) — v3.5.2
Autor     : Jair Alejandro Hernández González
Ubicación : San Felipe, Estado Yaracuy, República Bolivariana de Venezuela
===============================================================================
"""

import os
import sys
import zipfile
import re
import urllib.parse
from datetime import datetime
import xml.etree.ElementTree as ET
import pandas as pd

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    import tkinter as tk
    from tkinter import filedialog
    TK_AVAILABLE = True
except ImportError:
    TK_AVAILABLE = False

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(BASE_DIR, "config", "plantilla_base.ods")

def limpiar_xml_texto(val) -> str:
    """Sanea cadenas convirtiendo None a '' y neutralizando caracteres de control inválidos para XML."""
    if val is None or pd.isna(val):
        return ""
    txt = str(val).strip()
    if txt.lower() in ("nan", "none", "nat", "null"):
        return ""
    # Neutralizar caracteres de control ASCII que rompen XML (excepto 0x09, 0x0A, 0x0D)
    txt = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', txt)
    return txt

def limpiar_fecha_ods(val) -> str:
    """Limpia fechas a formato estricto YYYY-MM-DD cortando timestamps residuales."""
    txt = limpiar_xml_texto(val)
    if not txt:
        return ""
    if ' ' in txt:
        txt = txt.split()[0]
    if 'T' in txt:
        txt = txt.split('T')[0]
    return txt

def sanitizar_nombre_archivo(texto: str) -> str:
    """Elimina caracteres inválidos para nombres de archivo en Windows/Linux."""
    if not texto:
        return "Actividad"
    s = re.sub(r'[\\/*?:"<>|]', "", texto)
    s = re.sub(r'\s+', '_', s.strip())
    return s[:60]

def parsear_metadatos_url(url: str) -> dict:
    """Extrae parámetros de la URL de InfoApp para poblar la cabecera del reporte."""
    datos = {
        'nombre_actividad': 'Actividad Formativa',
        'id_actividad': '',
        'estado': 'Yaracuy',
        'nombre_infocentro': 'Felix Pifano',
        'codigo_infocentro': 'Yar23',
        'nombre_facilitador': 'Jair Hernández',
        'cedula_facilitador': '30.348.783',
        'contenido': 'Formación en Tecnologías Libres',
        'modulo': 'Comunidades de participación digital',
        'fecha_desde': datetime.now().strftime("%d/%m/%Y"),
        'fecha_hasta': datetime.now().strftime("%d/%m/%Y"),
        'hora_inicio': '9:00 am',
        'hora_fin': '12:00 pm'
    }

    if not url:
        return datos

    try:
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)

        if 'id_activity' in params:
            datos['id_actividad'] = params['id_activity'][0]
        if 'activity' in params:
            datos['nombre_actividad'] = urllib.parse.unquote(params['activity'][0])
            datos['contenido'] = datos['nombre_actividad']
        if 'estate' in params:
            datos['estado'] = urllib.parse.unquote(params['estate'][0])
        if 'code_info' in params:
            datos['codigo_infocentro'] = params['code_info'][0]
        if 'line_action' in params:
            datos['modulo'] = urllib.parse.unquote(params['line_action'][0])
        if 'date_activity' in params:
            fechas = params['date_activity'][0].split('/')
            if len(fechas) >= 2:
                datos['fecha_desde'] = fechas[0].replace('-', '/')
                datos['fecha_hasta'] = fechas[1].replace('-', '/')
            elif len(fechas) == 1:
                datos['fecha_desde'] = fechas[0].replace('-', '/')
                datos['fecha_hasta'] = fechas[0].replace('-', '/')
    except Exception:
        pass

    return datos

def seleccionar_ubicacion_guardado(id_actividad: str = "") -> str:
    """Solicita la ruta de guardado para la planilla ODS."""
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    id_s = f"_{id_actividad}" if id_actividad and id_actividad != "general" else ""
    nombre_sugerido = f"Planilla_Participantes_Actividad{id_s}_{ts}.ods"

    if TK_AVAILABLE:
        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            ruta = filedialog.asksaveasfilename(
                title="Guardar Planilla Oficial de Participantes",
                initialfile=nombre_sugerido,
                defaultextension=".ods",
                filetypes=[("OpenDocument Spreadsheet", "*.ods")]
            )
            root.destroy()
            if ruta:
                return ruta
        except Exception:
            pass

    return os.path.join(BASE_DIR, nombre_sugerido)

def generar_planilla_oficial(participantes: list, id_actividad: str = "", url_actividad: str = ""):
    """
    Genera la planilla oficial ODS inyectando los participantes en la plantilla base.
    Preserva los logos, membretes, metadatos, bordes de celda y pie de firmas de la plantilla oficial.
    """
    if not participantes:
        print("\n⚠️ No hay participantes registrados para generar la planilla.")
        return

    # 1. Extraer metadatos de cabecera
    datos_act = parsear_metadatos_url(url_actividad)
    if id_actividad and not datos_act.get('id_actividad'):
        datos_act['id_actividad'] = id_actividad

    # 2. Seleccionar ubicación de guardado
    ruta_salida = seleccionar_ubicacion_guardado(id_actividad)

    # 3. Inyección en plantilla base oficial ODS (XML Nativo)
    if os.path.exists(TEMPLATE_PATH):
        while True:
            try:
                ns = {
                    'table': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
                    'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
                    'office': 'urn:oasis:names:tc:opendocument:xmlns:office:1.0'
                }
                ET.register_namespace('table', ns['table'])
                ET.register_namespace('text', ns['text'])
                ET.register_namespace('office', ns['office'])

                with zipfile.ZipFile(TEMPLATE_PATH, 'r') as zin:
                    with zipfile.ZipFile(ruta_salida, 'w', zipfile.ZIP_DEFLATED) as zout:
                        for item in zin.infolist():
                            buffer = zin.read(item.filename)
                            if item.filename == 'content.xml':
                                root = ET.fromstring(buffer)
                                table = root.find('.//table:table', ns)
                                if table is not None:
                                    rows = list(table.findall(f"{{{ns['table']}}}table-row"))

                                    # --- A. Actualizar Datos de Cabecera ---
                                    # Fila 3: Estado, Infocentro, Código
                                    if len(rows) > 3:
                                        cells_r3 = rows[3].findall(f"{{{ns['table']}}}table-cell")
                                        if len(cells_r3) > 0 and cells_r3[0].find(f"{{{ns['text']}}}p") is not None:
                                            cells_r3[0].find(f"{{{ns['text']}}}p").text = f"Estado:* {limpiar_xml_texto(datos_act.get('estado', 'Yaracuy'))}"
                                        if len(cells_r3) > 3 and cells_r3[3].find(f"{{{ns['text']}}}p") is not None:
                                            cells_r3[3].find(f"{{{ns['text']}}}p").text = f"Nombre del Infocentro: {limpiar_xml_texto(datos_act.get('nombre_infocentro', 'Felix Pifano'))}"
                                        if len(cells_r3) > 6 and cells_r3[6].find(f"{{{ns['text']}}}p") is not None:
                                            cells_r3[6].find(f"{{{ns['text']}}}p").text = f"Código: {limpiar_xml_texto(datos_act.get('codigo_infocentro', 'Yar23'))}"

                                    # Fila 4: Facilitador, Contenido, Cédula facilitador
                                    if len(rows) > 4:
                                        cells_r4 = rows[4].findall(f"{{{ns['table']}}}table-cell")
                                        if len(cells_r4) > 0 and cells_r4[0].find(f"{{{ns['text']}}}p") is not None:
                                            cells_r4[0].find(f"{{{ns['text']}}}p").text = f"Nombres y apellidos del facilitador (a): {limpiar_xml_texto(datos_act.get('nombre_facilitador', ''))}"
                                        if len(cells_r4) > 1 and cells_r4[1].find(f"{{{ns['text']}}}p") is not None:
                                            cells_r4[1].find(f"{{{ns['text']}}}p").text = f"Contenido a desarrollar: {limpiar_xml_texto(datos_act.get('contenido', ''))}"
                                        if len(cells_r4) > 2 and cells_r4[2].find(f"{{{ns['text']}}}p") is not None:
                                            cells_r4[2].find(f"{{{ns['text']}}}p").text = f"Cedula de identidad: {limpiar_xml_texto(datos_act.get('cedula_facilitador', ''))}"

                                    # Fila 5: Módulo, Fechas, Horarios
                                    if len(rows) > 5:
                                        cells_r5 = rows[5].findall(f"{{{ns['table']}}}table-cell")
                                        if len(cells_r5) > 0 and cells_r5[0].find(f"{{{ns['text']}}}p") is not None:
                                            cells_r5[0].find(f"{{{ns['text']}}}p").text = f"Modulo de formación: {limpiar_xml_texto(datos_act.get('modulo', ''))}"
                                        if len(cells_r5) > 3 and cells_r5[3].find(f"{{{ns['text']}}}p") is not None:
                                            cells_r5[3].find(f"{{{ns['text']}}}p").text = f"Desde:* {limpiar_xml_texto(datos_act.get('fecha_desde', ''))}"
                                        if len(cells_r5) > 4 and cells_r5[4].find(f"{{{ns['text']}}}p") is not None:
                                            cells_r5[4].find(f"{{{ns['text']}}}p").text = f"Hasta:* {limpiar_xml_texto(datos_act.get('fecha_hasta', ''))}"
                                        if len(cells_r5) > 5 and cells_r5[5].find(f"{{{ns['text']}}}p") is not None:
                                            cells_r5[5].find(f"{{{ns['text']}}}p").text = f"Hora de inicio: {limpiar_xml_texto(datos_act.get('hora_inicio', '9:00 am'))}"
                                        if len(cells_r5) > 6 and cells_r5[6].find(f"{{{ns['text']}}}p") is not None:
                                            cells_r5[6].find(f"{{{ns['text']}}}p").text = f"Hora de fin:* {limpiar_xml_texto(datos_act.get('hora_fin', '12:00 pm'))}"

                                    # --- B. División Dinámica: Cabecera, Filas de Ejemplo y Pie de Página ---
                                    header_rows = rows[:8]
                                    footer_rows = rows[18:] if len(rows) > 18 else []

                                    # Limpiar filas existentes de la tabla
                                    for r in list(table):
                                        if r.tag == f"{{{ns['table']}}}table-row":
                                            table.remove(r)

                                    # Reinsertar encabezados oficiales
                                    for hr in header_rows:
                                        table.append(hr)

                                    # Insertar cada participante según la estructura exacta de la plantilla oficial
                                    for i, p in enumerate(participantes, 1):
                                        row = ET.Element(f"{{{ns['table']}}}table-row", {
                                            f"{{{ns['table']}}}style-name": "ro1"
                                        })

                                        # Celda 0 (ce1): Número correlativo (float)
                                        c0 = ET.SubElement(row, f"{{{ns['table']}}}table-cell", {
                                            f"{{{ns['table']}}}style-name": "ce1",
                                            f"{{{ns['office']}}}value-type": "float",
                                            f"{{{ns['office']}}}value": str(i)
                                        })
                                        ET.SubElement(c0, f"{{{ns['text']}}}p").text = str(i)

                                        # Celda 1 (ce2): Nombres y Apellidos en Title Case (spanned 2 cols, 1 row)
                                        nom_comp = limpiar_xml_texto(f"{p.get('nombre', '')} {p.get('apellido', '')}")
                                        c1 = ET.SubElement(row, f"{{{ns['table']}}}table-cell", {
                                            f"{{{ns['table']}}}style-name": "ce2",
                                            f"{{{ns['table']}}}number-columns-spanned": "2",
                                            f"{{{ns['table']}}}number-rows-spanned": "1",
                                            f"{{{ns['office']}}}value-type": "string"
                                        })
                                        ET.SubElement(c1, f"{{{ns['text']}}}p").text = nom_comp

                                        # Celda 2 (ce8): Celda cubierta por el span anterior
                                        ET.SubElement(row, f"{{{ns['table']}}}covered-table-cell", {
                                            f"{{{ns['table']}}}style-name": "ce8"
                                        })

                                        # Celda 3 (ce1): Documento
                                        if p.get('cedula'):
                                            doc_str = str(p.get('cedula', ''))
                                        elif p.get('cedulado') == 'escolar' or p.get('cedula_escolar'):
                                            doc_str = f"CE{p.get('cedula_escolar', '')}"
                                        elif p.get('cedula_padre'):
                                            doc_str = f"S/C (Rep: {p.get('cedula_padre', '')})"
                                        else:
                                            doc_str = "S/C"
                                            
                                        c3 = ET.SubElement(row, f"{{{ns['table']}}}table-cell", {
                                            f"{{{ns['table']}}}style-name": "ce1",
                                            f"{{{ns['office']}}}value-type": "string"
                                        })
                                        ET.SubElement(c3, f"{{{ns['text']}}}p").text = limpiar_xml_texto(doc_str)

                                        # Celda 4 (ce11): Fecha De Nacimiento (YYYY-MM-DD)
                                        f_nac = limpiar_fecha_ods(p.get('nacimiento', ''))
                                        c4 = ET.SubElement(row, f"{{{ns['table']}}}table-cell", {
                                            f"{{{ns['table']}}}style-name": "ce11",
                                            f"{{{ns['office']}}}value-type": "string"
                                        })
                                        ET.SubElement(c4, f"{{{ns['text']}}}p").text = f_nac

                                        # Celda 5 (ce1): Sexo (M/F)
                                        c5 = ET.SubElement(row, f"{{{ns['table']}}}table-cell", {
                                            f"{{{ns['table']}}}style-name": "ce1",
                                            f"{{{ns['office']}}}value-type": "string"
                                        })
                                        ET.SubElement(c5, f"{{{ns['text']}}}p").text = limpiar_xml_texto(p.get('genero', ''))

                                        # Celda 6 (ce1): Dirección (San Felipe)
                                        dir_val = limpiar_xml_texto(p.get('direccion')) or "San Felipe"
                                        c6 = ET.SubElement(row, f"{{{ns['table']}}}table-cell", {
                                            f"{{{ns['table']}}}style-name": "ce1",
                                            f"{{{ns['office']}}}value-type": "string"
                                        })
                                        ET.SubElement(c6, f"{{{ns['text']}}}p").text = dir_val

                                        # Celda 7 (ce1): Correo Electrónico (--- o personalizado)
                                        corr_val = limpiar_xml_texto(p.get('correo')) or "---"
                                        c7 = ET.SubElement(row, f"{{{ns['table']}}}table-cell", {
                                            f"{{{ns['table']}}}style-name": "ce1",
                                            f"{{{ns['office']}}}value-type": "string"
                                        })
                                        ET.SubElement(c7, f"{{{ns['text']}}}p").text = corr_val

                                        # Celda 8 (ce1): Teléfono normalizado
                                        tlf_val = limpiar_xml_texto(p.get('telefono')) or "0412-0000000"
                                        c8 = ET.SubElement(row, f"{{{ns['table']}}}table-cell", {
                                            f"{{{ns['table']}}}style-name": "ce1",
                                            f"{{{ns['office']}}}value-type": "string"
                                        })
                                        ET.SubElement(c8, f"{{{ns['text']}}}p").text = tlf_val

                                        # Celda 9 (ce1): Nivel de Institución (Educación Básica)
                                        edad_num = p.get('edad') or 12
                                        nivel_def = limpiar_xml_texto(p.get('nivel')) or ('Educación Media General' if edad_num >= 12 else 'Educación Básica')
                                        c9 = ET.SubElement(row, f"{{{ns['table']}}}table-cell", {
                                            f"{{{ns['table']}}}style-name": "ce1",
                                            f"{{{ns['office']}}}value-type": "string"
                                        })
                                        ET.SubElement(c9, f"{{{ns['text']}}}p").text = nivel_def

                                        # Celda 10 (ce1): Ocupación (Estudiante)
                                        ocup_val = limpiar_xml_texto(p.get('ocupacion')) or "Estudiante"
                                        c10 = ET.SubElement(row, f"{{{ns['table']}}}table-cell", {
                                            f"{{{ns['table']}}}style-name": "ce1",
                                            f"{{{ns['office']}}}value-type": "string"
                                        })
                                        ET.SubElement(c10, f"{{{ns['text']}}}p").text = ocup_val

                                        # Celda 11 (ce1): Firma (celda vacía con borde para firmar)
                                        c11 = ET.SubElement(row, f"{{{ns['table']}}}table-cell", {
                                            f"{{{ns['table']}}}style-name": "ce1",
                                            f"{{{ns['office']}}}value-type": "string"
                                        })
                                        ET.SubElement(c11, f"{{{ns['text']}}}p").text = ""

                                        # Celda 12: Celdas vacías adyacentes con ce14 (sin borde)
                                        ET.SubElement(row, f"{{{ns['table']}}}table-cell", {
                                            f"{{{ns['table']}}}style-name": "ce14",
                                            f"{{{ns['table']}}}number-columns-repeated": "2"
                                        })

                                        # Celda 13: Celdas de cierre restantes sin estilo ni bordes
                                        ET.SubElement(row, f"{{{ns['table']}}}table-cell", {
                                            f"{{{ns['table']}}}number-columns-repeated": "1010"
                                        })

                                        table.append(row)

                                    # Reinsertar notas y pie de página intactos
                                    for fr in footer_rows:
                                        table.append(fr)

                                buffer = ET.tostring(root, encoding='utf-8', xml_declaration=True)
                            zout.writestr(item, buffer)

                print(f"\n📊 Planilla oficial ODS guardada con éxito en:\n   {ruta_salida}")
                return
            except PermissionError:
                print(f"\n⚠️ El archivo '{os.path.basename(ruta_salida)}' está abierto en Excel o LibreOffice.")
                input("Por favor ciérralo y presiona Enter para reintentar el guardado...")
            except Exception as e:
                print(f"\n⚠️ Fallo en inyección XML de plantilla ODS: {e}")
                break

    # Fallback con pandas/odf si no existe la plantilla base
    while True:
        try:
            registros_salida = []
            for i, p in enumerate(participantes, 1):
                doc_str = p.get('cedula') or (f"CE:{p.get('cedula_escolar')}" if p.get('cedulado') == 'escolar' else (f"Rep:{p.get('cedula_padre')}" if p.get('cedula_padre') else "S/C"))
                registros_salida.append({
                    "N°": i,
                    "Documento / Cédula": limpiar_xml_texto(doc_str),
                    "Tipo": p.get('cedulado', '').upper(),
                    "Nombres y Apellidos": limpiar_xml_texto(f"{p.get('nombre', '')} {p.get('apellido', '')}"),
                    "Fecha Nacimiento": limpiar_fecha_ods(p.get('nacimiento', '')),
                    "Edad": p.get('edad', ''),
                    "Teléfono": limpiar_xml_texto(p.get('telefono', '')),
                    "Género": limpiar_xml_texto(p.get('genero', ''))
                })
            df_out = pd.DataFrame(registros_salida)
            df_out.to_excel(ruta_salida, index=False, engine='odf')
            print(f"\n📊 Planilla oficial ODS guardada con éxito en:\n   {ruta_salida}")
            break
        except PermissionError:
            print(f"\n⚠️ El archivo '{os.path.basename(ruta_salida)}' está abierto en Excel o LibreOffice.")
            input("Por favor ciérralo y presiona Enter para reintentar el guardado...")
        except Exception as e:
            print(f"\n❌ Error al exportar archivo: {e}")
            break
