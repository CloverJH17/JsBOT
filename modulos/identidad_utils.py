"""
IDENTIDAD INSTITUCIONAL Y SANITIZACIÓN DE DATOS — JsBOT
Funciones puras de validación de documentos MPPE/Infocentro, teléfonos y nombres.
"""
import re
from typing import Optional

LISTA_ESTADOS_VENEZUELA = [
    "Amazonas", "Anzoátegui", "Apure", "Aragua", "Barinas", "Bolívar",
    "Carabobo", "Cojedes", "Delta Amacuro", "Distrito Capital", "Falcón",
    "Guárico", "La Guaira", "Lara", "Mérida", "Miranda", "Monagas",
    "Nueva Esparta", "Portuguesa", "Sucre", "Táchira", "Trujillo", "Yaracuy", "Zulia"
]

def limpiar_cedula_universal(valor) -> str:
    """Sanea el documento nacional admitiendo formatos V- o E- y eliminando puntuación."""
    if not valor:
        return ""
    val_str = str(valor).strip().upper()
    val_str = re.sub(r'[\s\.\-]', '', val_str)
    if val_str.startswith(('V', 'E')):
        prefijo = val_str[0]
        digitos = re.sub(r'\D', '', val_str[1:])
        return f"{prefijo}-{digitos}" if digitos else ""
    digitos = re.sub(r'\D', '', val_str)
    return f"V-{digitos}" if digitos else ""

def formatear_telefono_venezolano(telefono_raw, default: str = "0412-0000000") -> str:
    """Normaliza el número a formato nacional con guion (04XX-XXXXXXX o 02XX-XXXXXXX)."""
    if not telefono_raw:
        return default
    if isinstance(telefono_raw, float):
        telefono_raw = int(telefono_raw)
    val_str = str(telefono_raw).strip()
    if val_str.endswith(".0") and val_str[:-2].replace(".", "").isdigit():
        val_str = val_str[:-2]
    nums = re.sub(r'\D', '', val_str)
    if not nums:
        return default
    if nums.startswith('58') and len(nums) in (12, 13):
        nums = '0' + nums[2:]
    if len(nums) == 10 and (nums.startswith(('412', '414', '416', '424', '426')) or nums.startswith('2')):
        nums = "0" + nums
    if len(nums) == 11 and (nums.startswith(('0412', '0414', '0416', '0424', '0426')) or nums.startswith('02')):
        return f"{nums[:4]}-{nums[4:]}"
    elif len(nums) == 11:
        return f"{nums[:4]}-{nums[4:]}"
    return default

def formatear_nombre_institucional(nombre_raw: str) -> str:
    """Aplica Title Case preservando partículas institucionales en minúsculas."""
    if not nombre_raw:
        return ""
    particulas = {"de", "del", "la", "las", "los", "y", "e"}
    palabras = re.sub(r'\s+', ' ', str(nombre_raw).strip()).lower().split(' ')
    resultado = []
    for i, p in enumerate(palabras):
        if i > 0 and p in particulas:
            resultado.append(p)
        else:
            resultado.append(p.capitalize())
    return " ".join(resultado)
