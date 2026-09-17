#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
MÓDULO: GESTOR DE SESIÓN, AUDITORÍA Y CHECKPOINTS (gestor_sesion.py)
===============================================================================
Sistema   : JsBOT (Robotic Process Automation) — versión: ver modulos/version.py
Autor     : Jair Alejandro Hernández González
Ubicación : San Felipe, Estado Yaracuy, República Bolivariana de Venezuela
===============================================================================
"""

import os
import sys
import json
import configparser
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime
import pandas as pd
from loguru import logger

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from modulos.interfaz_usuario import (
    prompt_credenciales_guardadas,
    prompt_nuevas_credenciales,
    prompt_url_actividad
)
import modulos.entorno as entorno
from modulos.version import ETIQUETA_VERSION

BASE_DIR = str(entorno.RAIZ_PROYECTO)
CONFIG_DIR = str(entorno.CARPETA_CONFIG)
LOGS_DIR = str(entorno.CARPETA_LOGS)
DATA_DIR = str(entorno.CARPETA_DATA)

CONFIG_FILE = str(entorno.ARCHIVO_CONFIG_INI)
CONFIG_SERV_PATH = os.path.join(CONFIG_DIR, "config_servicios.json")
SESSION_STATE_FILE = str(entorno.ARCHIVO_ESTADO_SESION)
SESSION_STATE_SERV_FILE = str(entorno.ARCHIVO_ESTADO_SESION_SERVICIOS)
DB_FILE = str(entorno.ARCHIVO_DB)


def extraer_id_actividad(url: str) -> str:
    """Extrae el ID de la actividad desde los parámetros de la URL de InfoApp."""
    match = re.search(r'id_activity=(\d+)', url, re.IGNORECASE)
    if match:
        return match.group(1)
    match_gen = re.search(r'/(\d+)(?:/|$|\?)', url)
    if match_gen:
        return match_gen.group(1)
    return "general"

def extraer_id_servicio(url: str) -> str:
    """Extrae el ID del servicio desde los parámetros de la URL de InfoApp."""
    match = re.search(r'id_service=(\d+)', url, re.IGNORECASE)
    if match:
        return match.group(1)
    match_gen = re.search(r'/(\d+)(?:/|$|\?)', url)
    if match_gen:
        return match_gen.group(1)
    return "general"

def obtener_credenciales() -> tuple:
    """Lee las credenciales guardadas en config.ini (prioriza [LOGIN], fallback [CREDENCIALES])."""
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        try:
            config.read(CONFIG_FILE, encoding='utf-8')
            seccion = 'LOGIN' if 'LOGIN' in config else ('CREDENCIALES' if 'CREDENCIALES' in config else None)
            if seccion:
                u = config[seccion].get('usuario', '')
                c = config[seccion].get('clave', '')
                if u and c:
                    return u, c
        except Exception:
            pass
    return "", ""

def guardar_credenciales(usuario: str, clave: str):
    """Guarda las credenciales en config.ini en [LOGIN] y [CREDENCIALES]."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        try:
            config.read(CONFIG_FILE, encoding='utf-8')
        except Exception:
            pass
    config['LOGIN'] = {
        'usuario': usuario,
        'clave': clave
    }
    config['CREDENCIALES'] = {
        'usuario': usuario,
        'clave': clave
    }
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        config.write(f)

def gestionar_credenciales() -> tuple:
    """Gestiona el flujo interactivo de autenticación."""
    u, c = obtener_credenciales()
    if u and c:
        if prompt_credenciales_guardadas(u):
            return u, c

    u, c = prompt_nuevas_credenciales()
    guardar_credenciales(u, c)
    return u, c

# =============================================================================
# PERSISTENCIA ACID Y AUDITORÍA HISTÓRICA CON SQLITE3
# =============================================================================

@contextmanager
def _abrir_conexion_db(db_path: str = None, timeout: float = 30.0):
    """Context manager que garantiza commit, rollback y cierre explícito de la conexión SQLite."""
    ruta = db_path or DB_FILE
    os.makedirs(os.path.dirname(os.path.abspath(ruta)), exist_ok=True)
    conn = sqlite3.connect(ruta, timeout=timeout)
    try:
        yield conn
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            conn.close()
        except Exception:
            pass

def inicializar_db(db_path: str = None):
    """Crea y valida el esquema ACID de la base de datos SQLite data/jsbot.db con WAL mode."""
    with _abrir_conexion_db(db_path, timeout=30.0) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_actividad TEXT NOT NULL,
                cedula TEXT,
                indice INTEGER NOT NULL DEFAULT 0,
                estado TEXT NOT NULL DEFAULT 'EN_PROCESO',
                tipo TEXT NOT NULL DEFAULT 'formacion',
                timestamp TEXT NOT NULL,
                datos_json TEXT,
                UNIQUE(id_actividad, tipo)
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inscritos_historico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_actividad TEXT NOT NULL,
                cedula TEXT NOT NULL,
                nombre TEXT,
                telefono TEXT,
                fecha_registro TEXT NOT NULL
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                nivel TEXT NOT NULL,
                origen TEXT NOT NULL,
                mensaje TEXT NOT NULL,
                metadata TEXT
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_checkpoints_actividad ON checkpoints(id_actividad, tipo);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_historico_actividad ON inscritos_historico(id_actividad);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_historico_cedula ON inscritos_historico(cedula);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_logs_ts ON app_logs(timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_logs_nivel ON app_logs(nivel);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_logs_origen ON app_logs(origen);")

def guardar_checkpoint_db(id_actividad: str, indice: int, cedula: str = None, estado: str = "EN_PROCESO", tipo: str = "formacion", timestamp: str = None, datos_json: str = None, db_path: str = None):
    """Persiste un checkpoint transaccional con semántica ACID."""
    ruta = db_path or DB_FILE
    inicializar_db(ruta)
    ts = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _abrir_conexion_db(ruta, timeout=30.0) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO checkpoints (id_actividad, cedula, indice, estado, tipo, timestamp, datos_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id_actividad, tipo) DO UPDATE SET
                cedula = excluded.cedula,
                indice = excluded.indice,
                estado = excluded.estado,
                timestamp = excluded.timestamp,
                datos_json = excluded.datos_json;
        """, (str(id_actividad), str(cedula or ''), int(indice), str(estado), str(tipo), ts, str(datos_json or '')))

def obtener_checkpoint_db(id_actividad: str = None, tipo: str = "formacion", db_path: str = None) -> dict:
    """Recupera el checkpoint activo más reciente desde SQLite."""
    ruta = db_path or DB_FILE
    if not os.path.exists(ruta):
        return None
    try:
        with _abrir_conexion_db(ruta, timeout=30.0) as conn:
            cursor = conn.cursor()
            if id_actividad:
                cursor.execute("""
                    SELECT id_actividad, cedula, indice, estado, tipo, timestamp, datos_json
                    FROM checkpoints
                    WHERE tipo = ? AND id_actividad = ?
                    ORDER BY id DESC LIMIT 1;
                """, (tipo, str(id_actividad)))
            else:
                cursor.execute("""
                    SELECT id_actividad, cedula, indice, estado, tipo, timestamp, datos_json
                    FROM checkpoints
                    WHERE tipo = ?
                    ORDER BY id DESC LIMIT 1;
                """, (tipo,))
            fila = cursor.fetchone()
            if fila:
                return {
                    "id_actividad": fila[0],
                    "cedula": fila[1],
                    "indice": fila[2],
                    "estado": fila[3],
                    "tipo": fila[4],
                    "timestamp": fila[5],
                    "datos_json": fila[6]
                }
    except Exception:
        pass
    return None

def limpiar_checkpoint_db(id_actividad: str = None, tipo: str = "formacion", db_path: str = None):
    """Elimina checkpoints completados en SQLite."""
    ruta = db_path or DB_FILE
    if not os.path.exists(ruta):
        return
    try:
        with _abrir_conexion_db(ruta, timeout=30.0) as conn:
            cursor = conn.cursor()
            if id_actividad:
                cursor.execute("DELETE FROM checkpoints WHERE tipo = ? AND id_actividad = ?;", (tipo, str(id_actividad)))
            else:
                cursor.execute("DELETE FROM checkpoints WHERE tipo = ?;", (tipo,))
    except Exception:
        pass

def registrar_inscrito_historico_db(id_actividad: str, cedula: str, nombre: str, telefono: str, fecha_registro: str = None, db_path: str = None):
    """Registra una inscripción histórica en la base de datos."""
    ruta = db_path or DB_FILE
    inicializar_db(ruta)
    ts = fecha_registro or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _abrir_conexion_db(ruta, timeout=30.0) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO inscritos_historico (id_actividad, cedula, nombre, telefono, fecha_registro)
            VALUES (?, ?, ?, ?, ?);
        """, (str(id_actividad), str(cedula), str(nombre or ''), str(telefono or ''), ts))

def consultar_inscritos_historico_db(id_actividad: str = None, cedula: str = None, db_path: str = None) -> list:
    """Consulta registros históricos por actividad y/o cédula."""
    ruta = db_path or DB_FILE
    if not os.path.exists(ruta):
        return []
    try:
        with _abrir_conexion_db(ruta, timeout=30.0) as conn:
            cursor = conn.cursor()
            query = "SELECT id_actividad, cedula, nombre, telefono, fecha_registro FROM inscritos_historico WHERE 1=1"
            params = []
            if id_actividad:
                query += " AND id_actividad = ?"
                params.append(str(id_actividad))
            if cedula:
                query += " AND cedula = ?"
                params.append(str(cedula))
            query += " ORDER BY id ASC;"
            cursor.execute(query, params)
            filas = cursor.fetchall()
            return [
                {
                    "id_actividad": f[0],
                    "cedula": f[1],
                    "nombre": f[2],
                    "telefono": f[3],
                    "fecha_registro": f[4]
                }
                for f in filas
            ]
    except Exception:
        return []

# =============================================================================
# PERSISTENCIA ATÓMICA DE LOGS EN SQLITE Y LOGURU SINK
# =============================================================================

def registrar_log_db(nivel: str, origen: str, mensaje: str, metadata: dict = None, db_path: str = None):
    """Registra una entrada estructurada en SQLite de forma atómica, transaccional y thread-safe."""
    ruta = db_path or DB_FILE
    inicializar_db(ruta)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    meta_str = json.dumps(metadata, ensure_ascii=False) if metadata else None
    try:
        with _abrir_conexion_db(ruta, timeout=15.0) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO app_logs (timestamp, nivel, origen, mensaje, metadata)
                VALUES (?, ?, ?, ?, ?);
            """, (ts, str(nivel).upper(), str(origen), str(mensaje), meta_str))
    except Exception:
        pass

def consultar_logs_db(limite: int = 100, nivel: str = None, origen: str = None, desde_ts: str = None, db_path: str = None) -> list:
    """Consulta logs estructurados almacenados en SQLite con filtros."""
    ruta = db_path or DB_FILE
    if not os.path.exists(ruta):
        return []
    try:
        with _abrir_conexion_db(ruta, timeout=15.0) as conn:
            cursor = conn.cursor()
            query = "SELECT id, timestamp, nivel, origen, mensaje, metadata FROM app_logs WHERE 1=1"
            params = []
            if nivel:
                query += " AND nivel = ?"
                params.append(str(nivel).upper())
            if origen:
                query += " AND origen = ?"
                params.append(str(origen))
            if desde_ts:
                query += " AND timestamp >= ?"
                params.append(str(desde_ts))
            query += " ORDER BY id DESC LIMIT ?;"
            params.append(int(limite))
            cursor.execute(query, params)
            filas = cursor.fetchall()
            return [
                {
                    "id": f[0],
                    "timestamp": f[1],
                    "nivel": f[2],
                    "origen": f[3],
                    "mensaje": f[4],
                    "metadata": json.loads(f[5]) if f[5] else None
                }
                for f in filas
            ]
    except Exception:
        return []

def purgar_logs_antiguos_db(dias_retencion: int = 30, max_registros: int = 10000, db_path: str = None) -> int:
    """Purga registros antiguos de logs para optimizar espacio y rendimiento."""
    ruta = db_path or DB_FILE
    if not os.path.exists(ruta):
        return 0
    eliminados = 0
    try:
        with _abrir_conexion_db(ruta, timeout=15.0) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM app_logs
                WHERE datetime(timestamp) < datetime('now', '-' || ? || ' days');
            """, (int(dias_retencion),))
            eliminados += cursor.rowcount

            cursor.execute("SELECT COUNT(*) FROM app_logs;")
            total = cursor.fetchone()[0]
            if total > max_registros:
                exceso = total - max_registros
                cursor.execute("""
                    DELETE FROM app_logs WHERE id IN (
                        SELECT id FROM app_logs ORDER BY id ASC LIMIT ?
                    );
                """, (exceso,))
                eliminados += cursor.rowcount
    except Exception:
        pass
    return eliminados

def _sqlite_loguru_sink(message):
    """Sink interno que deriva eventos de Loguru hacia la base de datos SQLite."""
    try:
        record = message.record
        nivel = record["level"].name
        origen = record["name"]
        mensaje = record["message"]
        registrar_log_db(nivel=nivel, origen=origen, mensaje=mensaje)
    except Exception:
        pass

def configurar_logger(ruta_log: str = None, nivel: str = "INFO", activar_sink_db: bool = True):
    """Configura Loguru con rotación automática a 5MB, compresión zip y sincronización SQLite."""
    if ruta_log is None:
        ruta_log = str(entorno.CARPETA_LOGS / "actividad_{time:YYYY-MM-DD}.log")
    os.makedirs(os.path.dirname(os.path.abspath(ruta_log)), exist_ok=True)
    try:
        logger.remove()
    except Exception:
        pass
    logger.add(
        ruta_log,
        rotation="5 MB",
        compression="zip",
        encoding="utf-8",
        level=nivel
    )
    if activar_sink_db:
        try:
            logger.add(_sqlite_loguru_sink, level=nivel)
        except Exception:
            pass
    return logger

try:
    configurar_logger()
except Exception:
    pass

# =============================================================================
# CHECKPOINTS Y AUDITORÍA DE FORMACIÓN (PUENTE RETROCOMPATIBLE)
# =============================================================================

def guardar_estado_sesion(config: dict, participantes: list, indice_ultimo: int):
    """Guarda checkpoint en disco de forma atómica y en SQLite con persistencia ACID."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    id_act = config.get("id_actividad", "general")
    datos = {
        "id_actividad": id_act,
        "url": config.get("url"),
        "usuario": config.get("usuario"),
        "timestamp_str": config.get("timestamp_str"),
        "archivo_log": config.get("archivo_log"),
        "indice_ultimo_procesado": indice_ultimo,
        "participantes": participantes
    }
    # Persistencia ACID en SQLite
    try:
        ced_actual = ""
        if participantes and 0 <= indice_ultimo < len(participantes):
            p = participantes[indice_ultimo]
            ced_actual = p.get('cedula') or p.get('cedula_escolar') or p.get('cedula_padre') or ''
        guardar_checkpoint_db(
            id_actividad=id_act,
            indice=indice_ultimo,
            cedula=ced_actual,
            estado="EN_PROCESO",
            tipo="formacion",
            datos_json=json.dumps(datos, ensure_ascii=False)
        )
    except Exception:
        pass

    # Respaldo atómico en JSON
    temp_file = f"{SESSION_STATE_FILE}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=4)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp_file, SESSION_STATE_FILE)

def leer_estado_sesion() -> dict:
    """Lee el checkpoint de formación si existe y no está completado."""
    if not os.path.exists(SESSION_STATE_FILE):
        # Intentar desde SQLite si el archivo físico no está presente
        try:
            cp = obtener_checkpoint_db(tipo="formacion")
            if cp and cp.get("datos_json"):
                datos = json.loads(cp["datos_json"])
                total = len(datos.get("participantes", []))
                ult = datos.get("indice_ultimo_procesado", 0)
                if total > 0 and ult < total:
                    return datos
        except Exception:
            pass
        return None
    try:
        with open(SESSION_STATE_FILE, "r", encoding="utf-8") as f:
            datos = json.load(f)
        total = len(datos.get("participantes", []))
        ult = datos.get("indice_ultimo_procesado", 0)
        if total > 0 and ult < total:
            return datos
    except Exception:
        pass
    return None

def limpiar_estado_sesion():
    """Elimina el checkpoint de formación tras completar con éxito la carga."""
    try:
        limpiar_checkpoint_db(tipo="formacion")
    except Exception:
        pass
    if os.path.exists(SESSION_STATE_FILE):
        try:
            os.remove(SESSION_STATE_FILE)
        except Exception:
            pass


def inicializar_sesion_actividad() -> dict:
    """Configura la sesión inicial solicitando la URL."""
    u, c = gestionar_credenciales()
    url = prompt_url_actividad()
    if not url:
        return None

    id_act = extraer_id_actividad(url)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    
    os.makedirs(LOGS_DIR, exist_ok=True)
    archivo_log = os.path.join(LOGS_DIR, f"log_actividad_{id_act}_{ts}.txt")

    with open(archivo_log, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write(f"REGISTRO DE AUDITORÍA — JsBOT RPA {ETIQUETA_VERSION}\n")
        f.write(f"Actividad ID : {id_act}\n")
        f.write(f"URL          : {url}\n")
        f.write(f"Fecha Inicio : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Facilitador  : {u}\n")
        f.write("=" * 80 + "\n\n")

    return {
        "usuario": u,
        "clave": c,
        "url": url,
        "id_actividad": id_act,
        "timestamp_str": ts,
        "archivo_log": archivo_log
    }

def registrar_evento_log(archivo_log: str, cedula: str, nombre: str, estado: str, detalle: str):
    """Registra una línea estructurada de auditoría en el archivo log."""
    if not archivo_log:
        return
    ts = datetime.now().strftime("%H:%M:%S")
    with open(archivo_log, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] [{estado:<8}] Doc: {cedula:<18} | {nombre:<32} | {detalle}\n")

def finalizar_log_exito(config: dict):
    """Cierra el log y remueve checkpoint."""
    if config and config.get('archivo_log'):
        with open(config['archivo_log'], "a", encoding="utf-8") as f:
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"PROCESO FINALIZADO EXITOSAMENTE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n")
    limpiar_estado_sesion()

def finalizar_log_incompleto(config: dict, motivo: str = ""):
    """Registra cierre prematuro o pausa en el log."""
    if config and config.get('archivo_log'):
        with open(config['archivo_log'], "a", encoding="utf-8") as f:
            f.write("\n" + "!" * 80 + "\n")
            f.write(f"PROCESO PAUSADO O INCOMPLETO: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            if motivo:
                f.write(f"Motivo: {motivo}\n")
            f.write("!" * 80 + "\n")

def generar_reporte_auditoria_excel(config: dict, exitosos: list, fallidos: list) -> str:
    """Genera un libro Excel con 2 hojas: 'Exitosos' e 'Incidencias'."""
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        id_act = config.get('id_actividad', 'general')
        ts = config.get('timestamp_str', datetime.now().strftime("%Y-%m-%d_%H%M"))
        ruta_excel = os.path.join(LOGS_DIR, f"Auditoria_Carga_Actividad_{id_act}_{ts}.xlsx")

        datos_exitosos = []
        for i, p in enumerate(exitosos, 1):
            doc = p.get('cedula') or (f"CE:{p.get('cedula_escolar')}" if p.get('cedulado') == 'escolar' else (f"Rep:{p.get('cedula_padre')}" if p.get('cedula_padre') else "S/C"))
            nom_comp = f"{p.get('nombre', '')} {p.get('apellido', '')}".strip()
            datos_exitosos.append({
                "N°": i,
                "Documento": doc,
                "Modalidad": p.get('cedulado', 'si').upper(),
                "Nombres y Apellidos": nom_comp,
                "Fecha Nacimiento": p.get('nacimiento', ''),
                "Teléfono": p.get('telefono', ''),
                "Género": p.get('genero', ''),
                "Estado": "EXITOSO",
                "Verificación DOM": "Confirmado en tabla InfoApp"
            })

        datos_fallidos = []
        if fallidos:
            for i, f_item in enumerate(fallidos, 1):
                p = f_item.get('participante', {})
                doc = p.get('cedula') or (f"CE:{p.get('cedula_escolar')}" if p.get('cedulado') == 'escolar' else (f"Rep:{p.get('cedula_padre')}" if p.get('cedula_padre') else "S/C"))
                nom_comp = f"{p.get('nombre', '')} {p.get('apellido', '')}".strip()
                datos_fallidos.append({
                    "N°": i,
                    "Documento": doc,
                    "Modalidad": p.get('cedulado', 'si').upper(),
                    "Nombres y Apellidos": nom_comp,
                    "Fecha Nacimiento": p.get('nacimiento', ''),
                    "Teléfono": p.get('telefono', ''),
                    "Estado": f_item.get('estado', 'FALLIDO'),
                    "Causa de la Incidencia": f_item.get('detalle', 'No especificado'),
                    "Acción Sugerida": "Verificar en InfoApp manualmente o corregir datos"
                })

        max_intentos = 3
        intento = 0
        while intento < max_intentos:
            try:
                with pd.ExcelWriter(ruta_excel, engine='openpyxl') as writer:
                    df_ex = pd.DataFrame(datos_exitosos) if datos_exitosos else pd.DataFrame([{"Mensaje": "No se registraron participantes exitosos"}])
                    df_ex.to_excel(writer, sheet_name="Exitosos", index=False)

                    if datos_fallidos:
                        df_fa = pd.DataFrame(datos_fallidos)
                        df_fa.to_excel(writer, sheet_name="Incidencias", index=False)
                break
            except PermissionError:
                intento += 1
                if sys.stdin and sys.stdin.isatty():
                    print(f"\n⚠️ El archivo '{os.path.basename(ruta_excel)}' está abierto en Excel o LibreOffice.")
                    try:
                        input("Por favor ciérralo y presiona Enter para reintentar el guardado...")
                    except Exception:
                        pass
                else:
                    ts_alt = datetime.now().strftime("%Y%m%d_%H%M%S")
                    ruta_excel = os.path.join(LOGS_DIR, f"Auditoria_Actividad_{id_act}_{ts_alt}.xlsx")

        return ruta_excel
    except Exception as e:
        print(f"⚠️ No se pudo generar el reporte Excel de auditoría: {e}")
        return ""

# =============================================================================
# CHECKPOINTS Y AUDITORÍA DE SERVICIOS
# =============================================================================

def cargar_config_servicios() -> dict:
    """Carga configuración de servicios desde config/config_servicios.json."""
    if os.path.exists(CONFIG_SERV_PATH):
        try:
            with open(CONFIG_SERV_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "catalogo_servicios": [
            "Gestión en el Sistema de Protección Social Patria",
            "Actividades de educación o aprendizaje",
            "Operaciones bancarias por Internet",
            "Interacción con organizaciones gubernamentales en general",
            "Préstamo de espacios del Infocentro",
            "Descarga de películas, imágenes y música, programas de televisión o videos, programas de radio o música",
            "Interacción y producción de contenidos en redes sociales y medios digitales de comunicación",
            "Envío o recepción de mensajes electrónicos",
            "Lectura o descarga de periódicos, revistas en línea o libros electrónicos",
            "Obtención de información sobre organizaciones gubernamentales en general",
            "Obtención de información relacionada con la salud o con servicios médicos",
            "Compra o pedido de bienes y servicios",
            "Descarga de programas informáticos",
            "Llamadas telefónicas a través del Protocolo de Internet",
            "Publicación de información o de mensajes instantáneos",
            "Registro/Actualización enmarcados en las Políticas de Gobierno",
            "Uso o descarga de video juegos"
        ],
        "servicio_por_defecto": "Gestión en el Sistema de Protección Social Patria",
        "infocentro": {
            "user_id": "1325",
            "code_info": "NRYAR24",
            "estado_nombre": "Yaracuy",
            "estado_id": "22",
            "municipio_nombre": "San Felipe",
            "municipio_id": "1",
            "direccion": "Av. principal El Jovito, Antigua Sede Del Inan"
        }
    }

def guardar_config_servicios(cfg: dict):
    """Persiste configuración de servicios."""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_SERV_PATH, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Error al guardar config de servicios: {e}")

def guardar_estado_sesion_servicios(config_bot: dict, config_servicio: dict, personas: list, indice_ultimo: int):
    """Guarda checkpoint de servicios de forma atómica y en SQLite."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    datos = {
        "usuario": config_bot.get("usuario"),
        "archivo_log": config_bot.get("archivo_log"),
        "timestamp_str": config_bot.get("timestamp_str"),
        "config_servicio": config_servicio,
        "indice_ultimo_procesado": indice_ultimo,
        "personas": personas
    }
    # Guardar en SQLite
    try:
        ced_actual = ""
        if personas and 0 <= indice_ultimo < len(personas):
            ced_actual = str(personas[indice_ultimo].get('cedula', ''))
        guardar_checkpoint_db(
            id_actividad="servicios",
            indice=indice_ultimo,
            cedula=ced_actual,
            estado="EN_PROCESO",
            tipo="servicios",
            datos_json=json.dumps(datos, ensure_ascii=False)
        )
    except Exception:
        pass

    try:
        temp_file = f"{SESSION_STATE_SERV_FILE}.tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_file, SESSION_STATE_SERV_FILE)
    except Exception:
        pass

def leer_estado_sesion_servicios() -> dict:
    """Lee el checkpoint de servicios si existe."""
    if not os.path.exists(SESSION_STATE_SERV_FILE):
        try:
            cp = obtener_checkpoint_db(tipo="servicios")
            if cp and cp.get("datos_json"):
                datos = json.loads(cp["datos_json"])
                personas = datos.get("personas", [])
                idx = datos.get("indice_ultimo_procesado", 0)
                if personas and idx < len(personas):
                    return datos
        except Exception:
            pass
        return None
    try:
        with open(SESSION_STATE_SERV_FILE, "r", encoding="utf-8") as f:
            datos = json.load(f)
        personas = datos.get("personas", [])
        idx = datos.get("indice_ultimo_procesado", 0)
        if personas and idx < len(personas):
            return datos
    except Exception:
        pass
    return None

def limpiar_estado_sesion_servicios():
    """Elimina el checkpoint de servicios al concluir exitosamente."""
    try:
        limpiar_checkpoint_db(tipo="servicios")
    except Exception:
        pass
    if os.path.exists(SESSION_STATE_SERV_FILE):
        try:
            os.remove(SESSION_STATE_SERV_FILE)
        except Exception:
            pass


def generar_reporte_auditoria_servicios(config: dict, config_servicio: dict, personas_exitosas: list, fallidos: list) -> str:
    """Genera reporte Excel de auditoría para servicios asentados."""
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        ts = config.get("timestamp_str") or datetime.now().strftime("%Y-%m-%d_%H%M")
        ruta_excel = os.path.join(LOGS_DIR, f"Auditoria_Servicios_{ts}.xlsx")

        datos_ex = []
        for i, p in enumerate(personas_exitosas, 1):
            nom = f"{p.get('nombre', '')} {p.get('apellido', '')}".strip() or "Usuario Registrado"
            datos_ex.append({
                "N°": i,
                "Cédula": f"V-{p['cedula']}" if not str(p['cedula']).startswith('E-') else str(p['cedula']),
                "Nombre y Apellido": nom,
                "Servicio Prestado": p.get('servicio_fila') or config_servicio.get('tipo_servicio'),
                "Fecha": p.get('fecha_fila') or config_servicio.get('fecha_servicio'),
                "Teléfono": p.get('telefono', ''),
                "Estado": "EXITOSO"
            })

        datos_fa = []
        for i, f in enumerate(fallidos, 1):
            p = f.get('participante', {})
            nom = f"{p.get('nombre', '')} {p.get('apellido', '')}".strip() or "Usuario"
            datos_fa.append({
                "N°": i,
                "Cédula": f"V-{p.get('cedula', '')}" if not str(p.get('cedula', '')).startswith('E-') else str(p.get('cedula', '')),
                "Nombre y Apellido": nom,
                "Estado": f.get('estado', 'FALLIDO'),
                "Incidencia / Detalle": f.get('detalle', 'Error no especificado')
            })

        max_intentos = 3
        intento = 0
        while intento < max_intentos:
            try:
                with pd.ExcelWriter(ruta_excel, engine='openpyxl') as writer:
                    df_ex = pd.DataFrame(datos_ex) if datos_ex else pd.DataFrame([{"Mensaje": "Sin exitosos"}])
                    df_ex.to_excel(writer, sheet_name="Servicios Exitosos", index=False)
                    if datos_fa:
                        df_fa = pd.DataFrame(datos_fa)
                        df_fa.to_excel(writer, sheet_name="Incidencias", index=False)
                break
            except PermissionError:
                intento += 1
                if sys.stdin and sys.stdin.isatty():
                    print(f"\n⚠️ El archivo '{os.path.basename(ruta_excel)}' está abierto en Excel o LibreOffice.")
                    try:
                        input("Por favor ciérralo y presiona Enter para reintentar el guardado...")
                    except Exception:
                        pass
                else:
                    ts_alt = datetime.now().strftime("%Y%m%d_%H%M%S")
                    ruta_excel = os.path.join(LOGS_DIR, f"Auditoria_Servicios_{ts_alt}.xlsx")

        return ruta_excel
    except Exception as e:
        print(f"⚠️ No se pudo generar el reporte Excel de servicios: {e}")
        return ""
