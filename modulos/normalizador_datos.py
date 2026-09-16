#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
MÓDULO: NORMALIZADOR DE DATOS Y EXTRACCIÓN ETL CONSOLIDADO (normalizador_datos.py)
===============================================================================
Sistema   : JsBOT (Robotic Process Automation) — v3.5.2
Autor     : Jair Alejandro Hernández González
Ubicación : San Felipe, Estado Yaracuy, República Bolivariana de Venezuela
===============================================================================
"""

import os
import sys
import re
import subprocess
import pandas as pd
from datetime import datetime, timedelta

# Asegurar codificación UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

def abrir_archivo_asistido(ruta_archivo: str) -> None:
    """Intenta abrir el archivo con la app nativa; si no hay suite, guía al usuario."""
    abierto = False
    try:
        if sys.platform == "win32":
            os.startfile(ruta_archivo)
            abierto = True
        else:
            # Linux (Canaima, Debian, Ubuntu)
            res = subprocess.run(["xdg-open", ruta_archivo], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            if res.returncode == 0:
                abierto = True
    except Exception:
        abierto = False

    if not abierto:
        print("\n" + "=" * 80)
        print("⚠️ AVISO: No se detectó ninguna suite ofimática (Excel / LibreOffice) instalada.")
        print(f"👉 Por favor abre y edita manualmente el archivo en:")
        print(f"   {os.path.abspath(ruta_archivo)}")
        print("=" * 80)
        input("\nPresiona [Enter] cuando hayas terminado de corregir y guardar el archivo...")

try:
    import tkinter as tk
    from tkinter import filedialog
    TK_AVAILABLE = True
except ImportError:
    TK_AVAILABLE = False

from modulos.interfaz_usuario import (
    mostrar_tabla_participantes,
    prompt_confirmar_carga,
    prompt_seleccionar_hojas,
    limpiar_consola,
    imprimir_banner
)
from modulos import config_manager as cm
from modulos.identidad_utils import (
    limpiar_cedula_universal,
    formatear_telefono_venezolano,
    formatear_nombre_institucional,
    LISTA_ESTADOS_VENEZUELA
)

FORMATOS_VALIDOS = ('.xlsx', '.xls', '.ods', '.csv', '.txt')
TELEFONO_DEFAULT = cm.telefono_por_defecto()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_BACKUP_PATH = os.path.join(BASE_DIR, "estudiantes.csv")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

PARTICULAS_MENORES = {'de', 'del', 'la', 'las', 'los', 'el', 'al', 'y', 'e', 'en', 'o'}
PREFIJOS_VALIDOS_TLF = ('0412', '0414', '0424', '0416', '0426', '0212', '0254', '0251', '0255', '0281', '0241')
PREFIJOS_SIN_CERO = tuple(p[1:] for p in PREFIJOS_VALIDOS_TLF)
PREFIJOS_MOVILES_SIN_CERO = tuple(p[1:] for p in PREFIJOS_VALIDOS_TLF[:5])

# Única fuente de verdad para el filtrado de filas/columnas basura (estadísticas,
# totales, firmas, autoridades). Consumida por es_nombre_valido() y el ETL.
PALABRAS_INVALIDAS_NOMBRE = {
    'masculino', 'femenino', 'total', 'rango', 'edad', 'tabla',
    'estadistica', 'distribucion', 'participantes', 'resumen',
    'promedio', 'firma', 'observacion', 'nota', 'coordinac'
}

# Encabezados de columna que nunca corresponden a participantes (autoridades/fijos).
CABECERAS_IGNORADAS = [
    'ente', 'institucion', 'encargado', 'facilitador',
    'vocero', 'responsable', 'profesor', 'docente',
    'coordinador', 'director', 'local', 'habitacion'
]

MESES_ES = {
    'enero': '01', 'ene': '01',
    'febrero': '02', 'feb': '02',
    'marzo': '03', 'mar': '03',
    'abril': '04', 'abr': '04',
    'mayo': '05', 'may': '05',
    'junio': '06', 'jun': '06',
    'julio': '07', 'jul': '07',
    'agosto': '08', 'ago': '08',
    'septiembre': '09', 'setiembre': '09', 'sep': '09', 'set': '09',
    'octubre': '10', 'oct': '10',
    'noviembre': '11', 'nov': '11',
    'diciembre': '12', 'dic': '12'
}

MAPA_PRIORITARIO = {
    'cedula_alumno': [
        r'\bcedula(?:\s+de)?\s+identidad\b',
        r'\bci(?:\s+de)?\s+identidad\b',
        r'\bcedula\s*escolar\b',
        r'\bcedula(?:\s+del?)?\s*(?:estudiante|alumno|participante|nino|joven|usuario|persona)\b',
        r'\bci(?:\s+del?)?\s*(?:estudiante|alumno|participante|nino|joven|usuario|persona)\b',
        r'^\s*document\s*id\s*$',
        r'^\s*cedula\b',
        r'^\s*dni\b',
        r'^\s*c\.?i\.?\s*$',
        r'^\s*ci\b',
        r'^\s*documento\b',
        r'\bidentificacion\b',
        r'^\s*identidad\b',
        r'\bdoc\s*identidad\b'
    ],
    'cedula_padre': [
        r'\bcedula(?:\s+de\s+identidad)?(?:\s+del?)?\s*(?:representante|padre|madre|tutor|rep|apoderado)\b',
        r'\bci(?:\s+de\s+identidad)?(?:\s+del?)?\s*(?:representante|padre|madre|tutor|rep|apoderado)\b',
        r'\bcedula\s*del?\s*rep\b',
        r'\bci\s*del?\s*rep\b',
        r'^\s*parent\s*dni\s*$',
        r'^\s*parent\s*id\s*$'
    ],
    'nacimiento': [
        r'\bfecha(?:\s+de)?\s*nac(?:imiento)?(?:\s+del?)?\s*(?:estudiante|alumno|participante|usuario)?\b',
        r'\buser\s*f\s*nacimiento\b',
        r'^\s*birth\s*date\b',
        r'^\s*birthday\s*$',
        r'^\s*dob\s*$',
        r'\bf\.?\s*nac\b',
        r'^\s*nacimiento\s*$'
    ],
    'telefono': [
        r'\btelefono\s*celular\b',
        r'\bteléfono\s*celular\b',
        r'^\s*celular\b',
        r'^\s*telefono\b',
        r'^\s*teléfono\b',
        r'^\s*phone\s*$',
        r'^\s*movil\b',
        r'^\s*móvil\b',
        r'^\s*contacto\b',
        r'^\s*tlf\b'
    ],
    'nombre': [
        r'^\s*nombres?(?:\s+del?)?\s*(?:estudiante|alumno|participante|usuario)?\b',
        r'^\s*primer\s*nombre\b',
        r'^\s*name\s*$',
        r'^\s*first\s*name\b',
        r'^\s*nombres?\s*$',
        r'^\s*nom\s*$',
        r'^\s*names?\s*$'
    ],
    'apellido': [
        r'^\s*apellidos?(?:\s+del?)?\s*(?:estudiante|alumno|participante|usuario)?\b',
        r'^\s*primer\s*apellido\b',
        r'^\s*lastname\s*$',
        r'^\s*last\s*name\b',
        r'^\s*surname\s*$',
        r'^\s*apellidos?\s*$',
        r'^\s*ape\s*$'
    ],
    'nombre_y_apellido': [
        r'\bnombres?\s*y\s*apellidos?\b',
        r'\bnombre\s*y\s*apellido\b',
        r'\bnombres?\s*apellidos?\b',
        r'\bapellidos?\s*y\s*nombres?\b',
        r'^\s*full\s*name\b',
        r'^\s*estudiante\b',
        r'^\s*participante\b',
        r'^\s*usuario\b',
        r'^\s*alumno\b'
    ],
    'edad': [
        r'\bedad\b',
        r'^\s*edad\b',
        r'^\s*años\b',
        r'^\s*edad\s*actual\b',
        r'^\s*age\s*$'
    ],
    'genero': [
        r'^\s*genero\b',
        r'^\s*género\b',
        r'^\s*sexo\b',
        r'^\s*gender\s*$',
        r'^\s*sex\s*$'
    ]
}

def log_etl(mensaje: str):
    """Registra trazas del proceso ETL."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(os.path.join(LOGS_DIR, "normalizacion.log"), "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {mensaje}\n")

def limpiar_texto(val) -> str:
    """Sanea cadenas eliminando espacios y caracteres nulos."""
    if val is None or pd.isna(val):
        return ""
    txt = str(val).strip()
    if txt.lower() in ("nan", "none", "nat", "null"):
        return ""
    if isinstance(val, float) and val.is_integer():
        return str(int(val))
    return txt

def formatear_nombre_propio(texto: str) -> str:
    """
    Convierte nombres y apellidos a formato Capitalizado/Title Case
    respetando partículas intermedias delegando a modulos.identidad_utils.
    """
    return formatear_nombre_institucional(texto)

def es_nombre_valido(nombre: str) -> bool:
    """Verifica que el nombre contenga letras válidas y no sea una fila de totales, estadísticas o ruido."""
    if not nombre or not isinstance(nombre, str):
        return False
    nom_norm = normalizar_col_nombre(nombre)
    if any(pal in nom_norm for pal in PALABRAS_INVALIDAS_NOMBRE):
        return False
    if nom_norm.replace(" ", "").isdigit():
        return False
    if len(nom_norm.replace(" ", "")) < 3:
        return False
    letras = re.findall(r'[a-zA-ZáéíóúÁÉÍÓÚñÑ]', nombre)
    if len(letras) < 2:
        return False
    return True

def normalizar_col_nombre(txt: str) -> str:
    """Normaliza encabezados para comparación regex."""
    if not isinstance(txt, str):
        return ""
    txt = txt.lower().strip()
    replacements = (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n"))
    for a, b in replacements:
        txt = txt.replace(a, b)
    txt = re.sub(r'(?<=\w)\.(?=\w)', '', txt)
    txt = re.sub(r'[\*\:\.\,\n\r#\-\/]', ' ', txt)
    return re.sub(r'[_\s]+', ' ', txt).strip()

def limpiar_cedula(val) -> str:
    """
    Extrae el documento respetando prefijo de nacionalidad extranjero (E-) o venezolano (V-).
    Ejemplo: 'E-12345678' -> 'E-12345678', 'E12345678' -> 'E-12345678', 'V12345678' -> '12345678'.
    """
    txt = limpiar_texto(val).upper().replace(" ", "").replace(".", "")
    if not txt or txt in ("0", "000", "SD", "S/D", "S/C", "NOAPLICA", "NO APLICA", "NONE"):
        return ""
    
    es_extranjero = txt.startswith("E-") or (txt.startswith("E") and len(txt) > 1 and txt[1:].isdigit())
    digitos = re.sub(r'\D', '', txt)
    if digitos and len(digitos) >= 5 and int(digitos) > 0:
        return f"E-{digitos}" if es_extranjero else digitos
    return ""

def generar_cedula_escolar(fecha_nac_iso: str, cedula_padre: str, pos_hijo: str = "1") -> str:
    """
    Calcula la Cédula Escolar MPPE según la fórmula matemática oficial:
    '1' + (Últimos 2 dígitos del año de nacimiento) + (C.I. Representante rellenada a 8 dígitos)
    Ejemplo: nacimiento 2016, padre 30348783 → 11630348783 (11 dígitos)
             nacimiento 2016, padre E-84321000 → 11684321000
    """
    ci_limpia = re.sub(r'\D', '', str(cedula_padre or ""))
    if not ci_limpia or int(ci_limpia) == 0:
        return ""

    aa = "00"
    if fecha_nac_iso:
        try:
            fn = datetime.strptime(fecha_nac_iso, "%Y-%m-%d")
            aa = str(fn.year)[-2:]
        except Exception:
            pass

    return f"1{aa}{ci_limpia.zfill(8)}"

def limpiar_telefono(val) -> str:
    """
    Formatea y valida rigurosamente números telefónicos venezolanos delegando a modulos.identidad_utils.
    """
    txt = limpiar_texto(val)
    return formatear_telefono_venezolano(txt, default=TELEFONO_DEFAULT)

def resolver_huerfanos_de_documento(participantes: list, modo_interactivo: bool = True) -> list:
    """
    Identifica y gestiona participantes sin documento de identidad propio ni de tutor ('sin_documento').
    En CLI (modo_interactivo=True), permite consultar u omitir por consola.
    En GUI (modo_interactivo=False), no bloquea y mantiene los registros para resolución visual.
    """
    if not participantes:
        return []
    huerfanos = [p for p in participantes if p.get('cedulado') == 'sin_documento' or (not p.get('cedula') and not p.get('cedula_escolar') and not p.get('cedula_padre'))]
    if not huerfanos:
        return participantes

    if modo_interactivo and sys.stdin.isatty():
        try:
            print(f"\n⚠️  [ATENCIÓN] Se detectaron {len(huerfanos)} participante(s) sin cédula ni representante:")
            for h in huerfanos[:3]:
                print(f"   • {h.get('nombre', '')} {h.get('apellido', '')}")
            resp = input(f"¿Deseas conservar estos registros para carga de cortesía? [S/N] (Enter = Sí): ").strip().lower()
            if resp == 'n':
                return [p for p in participantes if p not in huerfanos]
        except Exception:
            pass

    return participantes

def resolver_fechas_faltantes(participantes: list, modo_interactivo: bool = True, anio_referencia: int = None) -> list:
    """
    Resuelve fechas de nacimiento ausentes calculándolas a partir de la edad si está presente.
    No bloquea la GUI.
    """
    if not participantes:
        return []
    anio_actual = anio_referencia or datetime.now().year
    for p in participantes:
        if not p.get('nacimiento') and p.get('edad'):
            try:
                edad_val = int(p['edad'])
                if 1 <= edad_val <= 100:
                    anio_est = anio_actual - edad_val
                    p['nacimiento'] = f"{anio_est}-01-01"
            except Exception:
                pass
    return participantes

def resolver_telefonos_faltantes(participantes: list, modo_interactivo: bool = True, default: str = None) -> list:
    """
    Garantiza que todos los participantes tengan un teléfono asignado usando el valor institucional por defecto.
    """
    if not participantes:
        return []
    tel_def = default or TELEFONO_DEFAULT
    for p in participantes:
        if not p.get('telefono') or p.get('telefono') == "0412-0000000":
            p['telefono'] = tel_def
    return participantes

def limpiar_genero(val) -> str:
    """
    Estandariza género a M o F tolerando errores tipográficos como 'Marculino'.
    Valida que la detección de 'M' no sea un falso positivo si contiene fragmentos de femenino.
    """
    txt = limpiar_texto(val).upper().strip()
    if not txt:
        return ""
    # Femenino prioritario
    if any(txt.startswith(pref) for pref in ('F', 'MUJ', 'HEMB', 'W', 'WOMAN', 'GIRL', 'NINA', 'NIÑA', 'MADR', 'MAMA', 'MAMÁ', 'FEM')):
        return "F"
    if "FEM" in txt or "MUJER" in txt or "HEMBRA" in txt:
        return "F"
    # Masculino (incluyendo typos como 'MARCULINO', 'MACULINO', 'MASC', 'VARON', 'HOMBRE')
    if any(txt.startswith(pref) for pref in ('M', 'V', 'HOMB', 'BOY', 'NINO', 'NIÑO', 'VAR', 'CAB', 'PADR', 'PAPA', 'PAPÁ')):
        return "M"
    if "MASC" in txt or "MARCUL" in txt or "HOMBRE" in txt or "VARON" in txt or "MACUL" in txt:
        return "M"
    return ""

def limpiar_fecha(val) -> str:
    """
    Interpreta seriales de Excel, timestamps SQL y fechas en español/texto natural a formato ISO YYYY-MM-DD.
    Ejemplos:
      - 41713 -> '2014-03-15'
      - '15 de marzo de 2014' -> '2014-03-15'
      - '15-mar-2014' -> '2014-03-15'
      - '2014-03-15 14:30:00' -> '2014-03-15'
      - '15/03/2014' -> '2014-03-15'
    """
    if val is None or pd.isna(val):
        return ""

    # 1. Serial numérico de Excel (epoch base: 1899-12-30)
    try:
        num = float(val)
        if 30000 < num < 80000:
            origen = datetime(1899, 12, 30)
            return (origen + timedelta(days=int(num))).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        pass

    if isinstance(val, (datetime, pd.Timestamp)):
        return val.strftime("%Y-%m-%d")

    txt = limpiar_texto(val).strip()
    if not txt:
        return ""

    # 2. Quitar timestamps SQL o partes de hora
    if " " in txt and (":" in txt or re.search(r'\d{4}-\d{2}-\d{2}', txt)):
        parte_fecha = txt.split()[0]
        if re.match(r'^\d{4}-\d{2}-\d{2}$', parte_fecha):
            return parte_fecha
    if "T" in txt and ":" in txt:
        parte_fecha = txt.split("T")[0]
        if re.match(r'^\d{4}-\d{2}-\d{2}$', parte_fecha):
            return parte_fecha

    # 3. Normalizar fechas en texto en español
    txt_lower = txt.lower()
    for mes_nom, mes_num in MESES_ES.items():
        if mes_nom in txt_lower:
            patron = rf'(?:\bde\s+)?\b{mes_nom}\b(?:\s+de)?'
            txt_num = re.sub(patron, f"-{mes_num}-", txt_lower)
            txt_num = re.sub(r'[\s/]+', '-', txt_num).strip('-')
            partes = [p for p in txt_num.split('-') if p]
            if len(partes) == 3:
                d, m, y = partes[0], partes[1], partes[2]
                if len(y) == 2:
                    y = f"20{y}" if int(y) < 50 else f"19{y}"
                if len(d) == 4 and len(y) <= 2:
                    d, y = y, d
                try:
                    dt = datetime(int(y), int(m), int(d))
                    if 1920 <= dt.year <= datetime.now().year + 1:
                        return dt.strftime("%Y-%m-%d")
                except ValueError:
                    pass

    # 4. Formatos estándar de fecha en string
    formatos = [
        "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y",
        "%d-%m-%y", "%Y/%m/%d", "%d.%m.%Y", "%Y.%m.%d"
    ]
    for fmt in formatos:
        try:
            dt = datetime.strptime(txt, fmt)
            # Solo para formatos de 2 dígitos: %y mapea '51' -> 2051; para
            # fechas de nacimiento se asume el siglo anterior cuando cae en futuro
            if fmt.endswith('%y') and dt.year > datetime.now().year + 1 and dt.year >= 2000:
                dt = dt.replace(year=dt.year - 100)
            if 1920 <= dt.year <= datetime.now().year + 1:
                return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Fallback con pandas to_datetime (rechazar números puros como '2014'
    # para no inventar fechas con datos basura numérica)
    if re.fullmatch(r'\d+', txt):
        return ""
    try:
        dt_pd = pd.to_datetime(txt, dayfirst=True, errors='coerce')
        if pd.notna(dt_pd) and 1920 <= dt_pd.year <= datetime.now().year + 1:
            return dt_pd.strftime("%Y-%m-%d")
    except Exception:
        pass

    return ""

def generar_clave_dedup(p: dict) -> str:
    """
    Genera la clave única de deduplicación compartida por Formación y Servicios.
    Prioridad: C.I. propia -> Cédula Escolar -> C.I. del representante -> Nombre/Fecha.
    La inclusión del primer nombre en las claves CE/REP preserva a hermanos gemelos.
    """
    nom_key = re.sub(r'[^a-zA-Z0-9]', '', str(p.get('nombre', '')).lower().split()[0] if p.get('nombre') else '')
    if p.get('cedula'):
        return f"CI:{p['cedula']}"
    if p.get('cedula_escolar') or p.get('cedulado') == 'escolar':
        return f"CE:{p.get('cedula_escolar', '')}_{nom_key}"
    if p.get('cedula_padre') or p.get('cedulado') == 'no':
        return f"REP:{p.get('cedula_padre', '')}_{nom_key}"
    return f"NOM:{normalizar_col_nombre(p.get('nombre',''))}_{normalizar_col_nombre(p.get('apellido',''))}_{p.get('nacimiento','')}"

def deduplicar_participantes(
    participantes: list,
    modo_interactivo: bool = True,
    retornar_reporte: bool = None
) -> list | tuple[list, dict]:
    """
    Identifica y filtra participantes duplicados en la lista de entrada.
    Usa clave compuesta por nombre para gemelos con idéntica cédula escolar / representante.

    Parámetros:
        participantes: Lista de diccionarios de participantes normalizados.
        modo_interactivo: Si es True (CLI), consulta por terminal ante duplicados.
                          Si es False (GUI), descarta duplicados automáticamente sin usar InquirerPy ni input().
        retornar_reporte: Si es True, retorna tupla (unicos, reporte). Si es None, retorna tupla
                          cuando modo_interactivo es False y lista cuando modo_interactivo es True.
    """
    debe_retornar_reporte = retornar_reporte if retornar_reporte is not None else (not modo_interactivo)

    if not participantes:
        reporte_vacio = {
            "duplicados_omitidos": 0,
            "nombres": [],
            "detalles": [],
            "total_original": 0,
            "total_unicos": 0
        }
        return ([], reporte_vacio) if debe_retornar_reporte else []

    vistos = {}
    duplicados = []
    unicos = []

    for p in participantes:
        clave = generar_clave_dedup(p)

        if clave in vistos:
            duplicados.append(p)
        else:
            vistos[clave] = p
            unicos.append(p)

    reporte = {
        "duplicados_omitidos": len(duplicados),
        "nombres": [
            f"{d.get('nombre', '')} {d.get('apellido', '')}".strip()
            for d in duplicados
        ],
        "detalles": [
            {
                "nombre": f"{d.get('nombre', '')} {d.get('apellido', '')}".strip(),
                "documento": d.get('cedula') or d.get('cedula_escolar') or d.get('cedula_padre') or 'S/D',
                "registro": d
            }
            for d in duplicados
        ],
        "total_original": len(participantes),
        "total_unicos": len(unicos)
    }

    if not modo_interactivo:
        # Modo no interactivo (GUI / background): no invocar terminal ni InquirerPy.
        # Descartar duplicados por defecto y conservar los registros únicos.
        if debe_retornar_reporte:
            return unicos, reporte
        return unicos

    if duplicados:
        print(f"\n⚠️  [ATENCIÓN] Se detectaron {len(duplicados)} registro(s) duplicado(s) en la lista:")
        for d in duplicados[:5]:
            nom = f"{d.get('nombre','')} {d.get('apellido','')}".strip()
            doc = d.get('cedula') or d.get('cedula_escolar') or d.get('cedula_padre') or 'S/D'
            print(f"   • {nom} (Doc: {doc})")
        if len(duplicados) > 5:
            print(f"   ... y {len(duplicados) - 5} más.")

        try:
            if not sys.stdin.isatty():
                raise RuntimeError("Non-interactive stdin")
            from InquirerPy import inquirer
            from InquirerPy.base.control import Choice
            opc = inquirer.select(
                message="¿Cómo deseas gestionar los participantes duplicados?",
                choices=[
                    Choice("DEDUP", f"Eliminar duplicados y conservar {len(unicos)} registros únicos (Recomendado)"),
                    Choice("KEEP", f"Conservar todos ({len(participantes)} registros, incluyendo duplicados)")
                ],
                default="DEDUP",
                pointer="> "
            ).execute()
        except Exception:
            if not sys.stdin.isatty():
                opc = "DEDUP"
            else:
                try:
                    resp = input(f"¿Deseas eliminar los duplicados y dejar solo {len(unicos)} registros únicos? [S/N] (Enter = Sí): ").strip().lower()
                    opc = "KEEP" if resp == 'n' else "DEDUP"
                except Exception:
                    opc = "DEDUP"

        if opc == "DEDUP":
            print(f"✅ Lista deduplicada: {len(unicos)} participantes únicos listos para carga.")
            if debe_retornar_reporte:
                return unicos, reporte
            return unicos

    if debe_retornar_reporte:
        return participantes, reporte
    return participantes

def seleccionar_archivo_interactivo(titulo: str = "Participantes / Estudiantes") -> str:
    """
    Abre el explorador de archivos o solicita ruta en consola.
    Permite salir de forma segura escribiendo '0' o 'cancelar'.
    """
    print(f"\n📂 Selecciona el archivo de {titulo} (.xlsx, .xls, .ods, .csv, .txt)...")
    print("   (Escribe '0' o 'cancelar' para volver al menú principal)")
    
    if TK_AVAILABLE:
        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            ruta = filedialog.askopenfilename(
                title=f"Selecciona el archivo de {titulo}",
                filetypes=[
                    ("Todos los formatos soportados", "*.xlsx *.xls *.ods *.csv *.txt"),
                    ("Hojas de Cálculo", "*.xlsx *.xls *.ods *.csv"),
                    ("Archivos de Texto Plano", "*.txt"),
                    ("Todos los archivos", "*.*")
                ]
            )
            root.destroy()
            if ruta and os.path.exists(ruta):
                return ruta
        except Exception:
            pass

    # Entrada por consola con escape seguro
    while True:
        ruta_input = input(f"\nIntroduce la ruta del archivo (.xlsx, .ods, .csv, .txt) o '0' para cancelar: ").strip().strip('"').strip("'")
        if ruta_input.lower() in ('0', 'cancelar', 'salir', 'volver', 'back', 'q'):
            return ""
        if not ruta_input:
            return ""
        if os.path.exists(ruta_input) and ruta_input.lower().endswith(FORMATOS_VALIDOS):
            return ruta_input
        print(f"❌ El archivo no existe o no es un formato válido (.xlsx, .xls, .ods, .csv, .txt). Intenta de nuevo.")

def detectar_cabeceras(df: pd.DataFrame):
    """Localiza la fila de encabezados evaluando hasta 15 filas para tolerar membretes institucionales."""
    mejor_fila = 0
    mejor_mapeo = {}
    max_coincidencias = 0

    for r_idx in range(min(15, len(df))):
        fila = df.iloc[r_idx]
        mapeo_temp = {}
        coincidencias = 0

        for c_idx, val in enumerate(fila):
            txt_norm = normalizar_col_nombre(str(val))
            if not txt_norm:
                continue

            # =================================================================
            # FILTRO ESTRICTO DE EXCLUSIÓN (IGNORAR AUTORIDADES Y FIJOS)
            # =================================================================
            if any(palabra in txt_norm.split() for palabra in CABECERAS_IGNORADAS):
                continue

            es_rep = any(k in txt_norm for k in ['representante', 'padre', 'madre', 'tutor', 'rep'])

            for campo, patrones in MAPA_PRIORITARIO.items():
                if campo in mapeo_temp:
                    continue
                if es_rep and campo in ['nombre', 'apellido', 'cedula_alumno', 'nombre_y_apellido', 'edad', 'nacimiento', 'telefono']:
                    continue
                if not es_rep and campo in ['cedula_padre']:
                    continue

                for pat in patrones:
                    if re.search(pat, txt_norm):
                        mapeo_temp[campo] = c_idx
                        coincidencias += 1
                        break

        if 'nombre' in mapeo_temp and 'apellido' in mapeo_temp:
            mapeo_temp.pop('nombre_y_apellido', None)

        if coincidencias > max_coincidencias:
            max_coincidencias = coincidencias
            mejor_fila = r_idx
            mejor_mapeo = mapeo_temp

    # Heurística para columna de teléfono sin encabezado
    if 'telefono' not in mejor_mapeo and len(df) > mejor_fila + 1:
        for c_idx in range(len(df.columns)):
            if c_idx in mejor_mapeo.values():
                continue
            coincidencias_tlf = 0
            for r_idx in range(mejor_fila + 1, min(mejor_fila + 16, len(df))):
                val_c = str(df.iloc[r_idx, c_idx]).strip()
                digs = re.sub(r'\D', '', val_c)
                if len(digs) in (10, 11) and digs.startswith(PREFIJOS_VALIDOS_TLF + PREFIJOS_SIN_CERO):
                    coincidencias_tlf += 1
            if coincidencias_tlf >= 2:
                mejor_mapeo['telefono'] = c_idx
                break

    return mejor_fila, mejor_mapeo

def procesar_archivo_texto(ruta: str) -> list:
    """
    Procesa un archivo de texto plano (.txt) con una cédula por línea,
    pares Cédula / Nombre o valores separados por comas/tabuladores.
    """
    personas = []
    with open(ruta, 'r', encoding='utf-8', errors='ignore') as f:
        for linea in f:
            l = linea.strip()
            if not l or l.startswith('#'):
                continue
            partes = [p.strip() for p in re.split(r'[,;\t|]', l) if p.strip()]
            if not partes:
                continue
            
            ci = limpiar_cedula(partes[0])
            nom_idx = 1
            if not ci and len(partes) > 1:
                ci = limpiar_cedula(partes[1])
                nom_idx = 0
            
            if ci:
                nombre_raw = partes[nom_idx] if len(partes) > nom_idx and not limpiar_cedula(partes[nom_idx]) else ""
                nom_form = formatear_nombre_propio(nombre_raw)
                personas.append({
                    'nombre': nom_form,
                    'apellido': "",
                    'cedula': ci,
                    'cedulado': 'si',
                    'cedula_padre': "",
                    'cedula_escolar': "",
                    'nacimiento': "2000-01-01",
                    'edad': 25,
                    'genero': "M",
                    'telefono': TELEFONO_DEFAULT,
                    'solo_cedula': not bool(nom_form)
                })
    return personas

def procesar_archivo_participantes(ruta_archivo: str, hoja_especifica: str = None) -> list:
    """Lee e interpreta el libro de datos y retorna los participantes estructurados."""
    if not os.path.exists(ruta_archivo):
        return []

    ext = os.path.splitext(ruta_archivo)[1].lower()
    
    if ext == '.txt':
        return procesar_archivo_texto(ruta_archivo)

    hojas_dict = {}
    if ext == '.csv':
        for enc in ('utf-8', 'utf-8-sig', 'latin1', 'cp1252'):
            try:
                df = pd.read_csv(ruta_archivo, header=None, encoding=enc)
                hojas_dict["CSV"] = df
                break
            except Exception:
                continue
    elif ext == '.ods':
        try:
            excel_obj = pd.ExcelFile(ruta_archivo, engine='odf')
            hojas_a_leer = [hoja_especifica] if (hoja_especifica and hoja_especifica in excel_obj.sheet_names) else excel_obj.sheet_names
            for h in hojas_a_leer:
                hojas_dict[h] = pd.read_excel(excel_obj, sheet_name=h, header=None)
        except Exception as e:
            log_etl(f"Error abriendo ODS: {e}")
            return []
    else:
        try:
            excel_obj = pd.ExcelFile(ruta_archivo)
            hojas_a_leer = [hoja_especifica] if (hoja_especifica and hoja_especifica in excel_obj.sheet_names) else excel_obj.sheet_names
            for h in hojas_a_leer:
                hojas_dict[h] = pd.read_excel(excel_obj, sheet_name=h, header=None)
        except Exception as e:
            log_etl(f"Error abriendo Excel: {e}")
            return []

    participantes = []
    hoy = datetime.now()

    for nombre_hoja, df_raw in hojas_dict.items():
        if df_raw.empty or len(df_raw) < 1:
            continue

        mejor_fila, mapa_cols = detectar_cabeceras(df_raw)
        log_etl(f"Hoja '{nombre_hoja}': cabecera en fila {mejor_fila}, columnas: {mapa_cols}")

        for r_idx in range(mejor_fila + 1, len(df_raw)):
            row = df_raw.iloc[r_idx]

            if row.isna().all() or all(limpiar_texto(v) == "" for v in row):
                continue

            def get_val(campo):
                if campo in mapa_cols:
                    c = mapa_cols[campo]
                    if c < len(row):
                        return row.iloc[c]
                return None

            ced_alumno = limpiar_cedula(get_val('cedula_alumno'))
            ced_padre = limpiar_cedula(get_val('cedula_padre'))

            # Nombre y apellido
            raw_nom = ""
            raw_ape = ""

            if 'nombre' in mapa_cols and 'apellido' in mapa_cols:
                raw_nom = formatear_nombre_propio(limpiar_texto(get_val('nombre')))
                raw_ape = formatear_nombre_propio(limpiar_texto(get_val('apellido')))
            elif 'nombre' in mapa_cols:
                raw_nom = formatear_nombre_propio(limpiar_texto(get_val('nombre')))
            elif 'nombre_y_apellido' in mapa_cols:
                nom_completo = limpiar_texto(get_val('nombre_y_apellido'))
                if nom_completo:
                    partes = nom_completo.split()
                    if len(partes) >= 4:
                        raw_nom = formatear_nombre_propio(" ".join(partes[:2]))
                        raw_ape = formatear_nombre_propio(" ".join(partes[2:]))
                    elif len(partes) in (2, 3):
                        raw_nom = formatear_nombre_propio(partes[0])
                        raw_ape = formatear_nombre_propio(" ".join(partes[1:]))
                    else:
                        raw_nom = formatear_nombre_propio(nom_completo)

            nom_full = f"{raw_nom} {raw_ape}".lower().strip()

            # 1. FILTRADO ESTRICTO DE FILAS BASURA (reglas centralizadas en
            # es_nombre_valido / PALABRAS_INVALIDAS_NOMBRE):
            if not nom_full or not es_nombre_valido(nom_full):
                continue

            # Fecha de nacimiento
            fecha_iso = limpiar_fecha(get_val('nacimiento'))

            # Cálculo de edad
            edad_val = None
            try:
                edad_val = int(re.sub(r'\D', '', limpiar_texto(get_val('edad'))))
            except Exception:
                pass

            if edad_val is None and fecha_iso:
                try:
                    fn = datetime.strptime(fecha_iso, "%Y-%m-%d")
                    edad_val = hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))
                except Exception:
                    pass

            # Saneamiento de fechas futuras (año actual puesto por error en el formulario)
            if fecha_iso and int(fecha_iso[:4]) >= 2024 and edad_val and edad_val >= 3:
                anio_corr = datetime.now().year - int(edad_val)
                fecha_iso = f"{anio_corr}{fecha_iso[4:]}"

            # Género
            gen = limpiar_genero(get_val('genero'))
            if not gen and raw_nom:
                p_nom = raw_nom.split()[0].lower()
                NOMBRES_MASC_EXCEPCION = {
                    'luis', 'alexis', 'denis', 'boris', 'chris', 'elis', 'elvis',
                    'francis', 'harris', 'jonas', 'josias', 'isaias', 'matias',
                    'nicolas', 'tobias', 'tomas', 'andres', 'moises', 'ulises',
                    'jesus', 'carlos', 'marcos', 'lucas', 'elias', 'cesar', 'omar'
                }
                if p_nom in NOMBRES_MASC_EXCEPCION:
                    gen = "M"
                elif p_nom.endswith(('a', 'ia', 'eth', 'bel')):
                    gen = "F"
                else:
                    gen = "M"

            # Teléfono estricto
            tlf = limpiar_telefono(get_val('telefono'))

            # 2. SANEAMIENTO INTELIGENTE DE CÉDULAS Y TIPOS DE DOCUMENTO:
            # A. Teléfonos en Campo Cédula (>= 10 dígitos con prefijo '04XX' o móvil '4XX')
            ced_digitos = re.sub(r'\D', '', str(ced_alumno or ""))
            es_tlf_en_ced = len(ced_digitos) >= 10 and (
                ced_digitos.startswith('04') or ced_digitos.startswith(PREFIJOS_MOVILES_SIN_CERO)
            )
            if es_tlf_en_ced:
                if tlf == TELEFONO_DEFAULT or not tlf:
                    tlf = limpiar_telefono(ced_alumno)
                ced_alumno = ""

            # B. Cédula Escolar previa en Campo Cédula (10 a 14 dígitos y no es teléfono)
            ced_escolar_previa = ""
            if ced_alumno and len(ced_digitos) >= 10 and not es_tlf_en_ced:
                ced_escolar_previa = ced_alumno
                ced_alumno = ""

            # C. Cédula Escolar Truncada por Excel (ej. 12018)
            es_ce_truncada = False
            if ced_alumno and 4 <= len(ced_digitos) <= 6 and ced_digitos.startswith(('120', '118', '119', '121', '122', '123', '124')):
                ced_alumno = ""
                es_ce_truncada = True

            # D. Cédula de adulto en menor (< 30 millones en menores de 10 años / nacidos >= 2015)
            if ced_alumno and ced_digitos.isdigit():
                val_num = int(ced_digitos)
                if val_num < 30000000 and ((edad_val is not None and edad_val < 10) or (fecha_iso and int(fecha_iso[:4]) >= 2015)):
                    if not ced_padre or len(re.sub(r'\D', '', str(ced_padre))) < 5:
                        ced_padre = str(val_num)
                    ced_alumno = ""

            # E. Clasificación Universal Escolar: Todo participante sin CI propia obtiene Cédula Escolar
            if ced_alumno:
                is_cedulado = "si"
                ced_escolar = ""
                ced_padre_final = ""
            elif ced_escolar_previa:
                is_cedulado = "escolar"
                ced_escolar = ced_escolar_previa
                ced_padre_final = ced_padre
            elif es_ce_truncada:
                is_cedulado = "escolar"
                tutor_ci = re.sub(r'\D', '', str(ced_padre)) if ced_padre else ""
                ced_escolar = generar_cedula_escolar(fecha_iso, tutor_ci, "1") if (tutor_ci and len(tutor_ci) >= 5) else ""
                ced_padre_final = tutor_ci
            elif ced_padre and len(re.sub(r'\D', '', str(ced_padre))) >= 5:
                is_cedulado = "escolar"
                tutor_ci = re.sub(r'\D', '', str(ced_padre))
                ced_escolar = generar_cedula_escolar(fecha_iso, tutor_ci, "1")
                ced_padre_final = tutor_ci
            else:
                is_cedulado = "sin_documento"
                ced_escolar = ""
                ced_padre_final = ""

            participantes.append({
                'nombre': raw_nom,
                'apellido': raw_ape,
                'cedula': ced_alumno,
                'cedulado': is_cedulado,
                'cedula_padre': ced_padre_final,
                'cedula_escolar': ced_escolar,
                'nacimiento': fecha_iso,
                'edad': edad_val,
                'genero': gen,
                'telefono': tlf
            })

    return participantes

def auditar_integridad_lote(participantes: list, ruta_archivo: str = "") -> dict:
    """
    Audita la consistencia global de una lista de participantes.
    Identifica faltantes críticos: participantes sin documento, ausencia de géneros, etc.
    """
    total = len(participantes)
    sin_doc = 0
    con_saime = 0
    con_escolar = 0
    sin_genero = 0
    sin_nacimiento = 0

    for p in participantes:
        ced = str(p.get('cedula', '') or '').strip()
        ced_esc = str(p.get('cedula_escolar', '') or '').strip()
        ced_pad = str(p.get('cedula_padre', '') or '').strip()

        if ced:
            con_saime += 1
        elif ced_esc or (ced_pad and len(ced_pad) >= 5):
            con_escolar += 1
        else:
            sin_doc += 1

        if not p.get('genero'):
            sin_genero += 1
        if not p.get('nacimiento'):
            sin_nacimiento += 1

    requiere_atencion = (sin_doc > 0)
    bloqueante_registro = (sin_doc == total and total > 0)

    return {
        "total": total,
        "sin_documento": sin_doc,
        "con_saime": con_saime,
        "con_escolar": con_escolar,
        "sin_genero": sin_genero,
        "sin_nacimiento": sin_nacimiento,
        "requiere_atencion": requiere_atencion,
        "bloqueante_registro": bloqueante_registro,
        "archivo": os.path.basename(ruta_archivo) if ruta_archivo else ""
    }

def ejecutar_modulo_etl(es_solo_planilla: bool = False) -> list:
    """Función de entrada del normalizador ETL para actividades formativas o planillas."""
    archivo = seleccionar_archivo_interactivo("Participantes de Formación" if not es_solo_planilla else "Participantes para Planilla ODS")
    if not archivo:
        return []

    ext = os.path.splitext(archivo)[1].lower()
    hoja_elegida = None

    if ext in ('.xlsx', '.xls'):
        try:
            excel_obj = pd.ExcelFile(archivo)
            if len(excel_obj.sheet_names) > 1:
                hojas = prompt_seleccionar_hojas(excel_obj.sheet_names)
                if len(hojas) == 1:
                    hoja_elegida = hojas[0]
        except Exception:
            pass

    # BUCLE DE INTERVENCIÓN HUMANA (HITL)
    while True:
        participantes = procesar_archivo_participantes(archivo, hoja_especifica=hoja_elegida)
        if not participantes:
            print(f"\n❌ ERROR CRÍTICO: No se pudieron extraer datos válidos del archivo.")
            print("Posibles causas: Las cabeceras (Nombres, Cédula) no están claras, o hay datos basura al inicio.")
            print(f"\n>> Abriendo {os.path.basename(archivo)} en tu editor predeterminado (Excel/Calc)...")
            abrir_archivo_asistido(archivo)
            
            print("\n⚠️ INSTRUCCIONES:")
            print(" 1. Elimina cualquier fila de 'título' o 'resumen' que esté sobre las cabeceras.")
            print(" 2. Asegúrate de que las columnas digan claramente 'Nombres', 'Apellidos', 'Cédula'.")
            print(" 3. Guarda el archivo (Ctrl+G) y cierra Excel.")
            
            try:
                input("\n[?] Presiona ENTER aquí cuando hayas guardado y cerrado para re-escanear (o Ctrl+C para salir)...")
            except KeyboardInterrupt:
                return []
            
            limpiar_consola()
            imprimir_banner()
            continue
        
        break

    # Deduplicación interactiva con preservación de gemelos
    participantes = deduplicar_participantes(participantes)

    # Limpieza visual y presentación de la tabla pre-validada
    limpiar_consola()
    imprimir_banner()
    mostrar_tabla_participantes(participantes)

    # Guardar copia de seguridad normalizada en la raíz como estudiantes.csv
    while True:
        try:
            pd.DataFrame(participantes).to_csv(CSV_BACKUP_PATH, index=False, encoding='utf-8-sig')
            log_etl(f"Respaldo CSV guardado en: {CSV_BACKUP_PATH}")
            break
        except PermissionError:
            print(f"\n⚠️ El archivo '{os.path.basename(CSV_BACKUP_PATH)}' está abierto en Excel o LibreOffice.")
            input("Por favor ciérralo y presiona Enter para reintentar el guardado...")
        except Exception as e:
            log_etl(f"Aviso al guardar respaldo CSV: {e}")
            break

    # Confirmación interactiva
    if not prompt_confirmar_carga(len(participantes), es_solo_planilla=es_solo_planilla):
        print("\n⚠️ Proceso cancelado.")
        return []

    return participantes

def normalizar_personas_servicios(ruta_archivo: str = None) -> list:
    """Punto de entrada consolidado para cargar y normalizar la lista de personas para servicios."""
    if not ruta_archivo:
        ruta_archivo = seleccionar_archivo_interactivo("Atención al Usuario / Servicios")
    
    if not ruta_archivo or not os.path.exists(ruta_archivo):
        return []

    ext = os.path.splitext(ruta_archivo)[1].lower()
    personas = []

    if ext == '.txt':
        personas = procesar_archivo_texto(ruta_archivo)
    else:
        # BUCLE DE INTERVENCIÓN HUMANA (HITL)
        while True:
            participantes_raw = procesar_archivo_participantes(ruta_archivo)
            
            if not participantes_raw:
                print(f"\n❌ ERROR CRÍTICO: No se pudieron extraer datos válidos del archivo.")
                print("Posibles causas: Las cabeceras (Nombres, Cédula) no están claras, o hay datos basura al inicio.")
                print(f"\n>> Abriendo {os.path.basename(ruta_archivo)} en tu editor predeterminado (Excel/Calc)...")
                abrir_archivo_asistido(ruta_archivo)
                
                print("\n⚠️ INSTRUCCIONES:")
                print(" 1. Elimina cualquier fila de 'título' o 'resumen' que esté sobre las cabeceras.")
                print(" 2. Asegúrate de que las columnas digan claramente 'Nombres', 'Apellidos', 'Cédula'.")
                print(" 3. Guarda el archivo (Ctrl+G) y cierra Excel.")
                
                try:
                    input("\n[?] Presiona ENTER aquí cuando hayas guardado y cerrado para re-escanear (o Ctrl+C para salir)...")
                except KeyboardInterrupt:
                    return []
                
                limpiar_consola()
                imprimir_banner()
                continue

            personas = [p for p in participantes_raw if p.get('cedula') or p.get('cedula_escolar') or p.get('cedula_padre')]
            break

    if not personas:
        print("⚠️ No se detectaron cédulas o personas válidas en el archivo seleccionado.")
        return []

    # Deduplicar preservando el primer orden de aparición (misma clave que Formación)
    vistos = set()
    personas_unicas = []
    for p in personas:
        clave = generar_clave_dedup(p)
        if clave not in vistos:
            vistos.add(clave)
            personas_unicas.append(p)

    return personas_unicas
