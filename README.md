# 🤖 JsBOT — Sistema RPA, Normalización ETL y Analítica de Auditoría (v4.3.0)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![UI](https://img.shields.io/badge/GUI-CustomTkinter-blueviolet.svg)](https://customtkinter.tomschimansky.com/)
[![CLI](https://img.shields.io/badge/CLI-Rich%20%2B%20InquirerPy-cyan.svg)](https://github.com/Textualize/rich)
[![Automation](https://img.shields.io/badge/Engine-Selenium%20%2B%20HTTP%20Turbo-green.svg)](https://www.selenium.dev/)
[![Tests](https://img.shields.io/badge/Tests-284%20passed-success.svg)](#calidad-y-resiliencia)
[![OS](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20(Canaima%20%2F%20Mint)-lightgrey.svg)](#requisitos-e-instalación)

> **JsBOT** es una suite integral de Automatización Robótica de Procesos (RPA), procesamiento ETL y Analítica de Auditoría diseñada para la normalización, validación documental, inyección de participantes, generación de actas formativas ODS y auditoría operativa en la plataforma institucional InfoApp (Fundación Infocentro).

---

## ⚡ Características Principales

- **Arquitectura Bimodal (GUI + CLI):**
  - **Modo Gráfico Nativo:** Interfaz moderna en Dark Mode construida con CustomTkinter, optimizada para resoluciones desde 1366×768 hasta 1080p.
  - **Modo Consola Interactivo (CLI):** Menú rápido por terminal asistido por Rich e InquirerPy.
  - **Feature Toggle & Fallback:** Conmutación automática a consola si el entorno anfitrión carece de servidor gráfico X11/Wayland.
- **Inspector de Auditoría y Balance Operativo (v4.2.7):**
  - **Auditorías Multi-criterio:** Búsqueda por Facilitador (UID con aislamiento estricto de sede), por Infocentro (código de sede) o Resumen Estadal (Región completa).
  - **Modo Turbo (HTTP Concurrente):** Aceleración extrema desacoplando Selenium tras el login hacia peticiones paralelas con `requests.Session` y `ThreadPoolExecutor` (hasta 10x más rápido).
  - **Doble Capa de Extracción (DOM Fallback):** Recuperación robusta de temas, talleres, participantes y productos incluso ante etiquetas ausentes en el HTML.
  - **Dashboard Analítico:** 4 KPIs de alto impacto con promedios por aula, sedes únicas, trámites más demandados y control de cuadre matemático (100%).
  - **Ventanas Modales al Frente:** Inspección detallada con modalidad bloqueante estricta (`grab_set()`), buscador reactivo y cabeceras clickeables para ordenamiento instantáneo.
  - **Exportación Interactiva Multiformato:** Generación a un clic de reportes en Excel (.xlsx con auto-filtro en todas las hojas), LibreOffice (.odt), PDF (.pdf), CSV (.csv) o Consola con diálogo de guardado y apertura automática en el sistema operativo.
  - **Caché Ligero Local:** Almacenamiento JSON para consulta y revisión offline inmediata.
- **Motor ETL de Normalización Inteligente:**
  - Ingesta multi-formato (`.xlsx`, `.ods`, `.csv`).
  - Detección automática de Cédulas SAIME (`V-`), generación de Cédulas Escolares estructuradas (`CE`), corrección de claves truncadas y protección ante menores sin documento.
  - Limpieza de cadenas a formato Title Case institucional y saneamiento telefónico.
- **Auditoría Previa (Pre-Flight Data Panel):**
  - Panel de resumen de datos antes de disparar Selenium.
  - Visor modal tabular (`CTkToplevel`) para inspeccionar la lista normalizada de alumnos en vivo.
- **Planillas Oficiales ODS:**
  - Generación directa de reportes y actas formativas en formato abierto OpenDocument Spreadsheet (`.ods`).
- **Blindaje y Concurrencia:**
  - Cerrojo de exclusión mutua (`file lock`) para prevenir instancias duplicadas.
  - Suite certificada con más de 270 pruebas unitarias y de estrés ante cortes abruptos de red o fallos eléctricos.

---

## 🖥️ Módulos de la Interfaz

| Sección | Función Operativa |
| :--- | :--- |
| **Diagnóstico** | Matriz de tarjetas en tiempo real (Python, SO, librerías, conectividad y navegador). |
| **Credenciales** | Administración segura de usuario y contraseña para la plataforma InfoApp. |
| **Formación** | Carga masiva de participantes en actividades y cursos formativos. |
| **Servicios** | Carga automatizada de beneficiarios y registros de atención comunitaria. |
| **Reportes** | Inspector de Auditoría, balances operativos, ventanas modales y exportación multiformato. |
| **Planillas** | Generación de planillas formativas oficiales `.ods` y actas institucionales. |
| **Ajustes** | Calibración de timeouts de red (Login, AJAX, DOM) y conmutador visual de navegador. |
| **Créditos** | Ficha técnica, licencias y autoría del proyecto. |

---

## 🚀 Requisitos e Instalación

### Requisitos Base
- **Python:** 3.10 o superior.
- **Navegadores Soportados:** Google Chrome, Chromium o Mozilla Firefox (con sus respectivos webdrivers administrados automáticamente).

### Instalación Rápida en Linux (Canaima / Linux Mint / Ubuntu)
```bash
# Clonar y entrar al repositorio
git clone https://github.com/CloverJH17/JsBOT.git
cd JsBOT

# Asignar permisos y ejecutar (configura librerías automáticamente)
chmod +x linux.sh
./linux.sh
```

### Ejecución en Windows
Haz doble clic sobre `windows.bat` o ejecuta desde PowerShell / CMD:
```dos
windows.bat
```

---

## 💻 Modos de Uso y Banderas de Terminal
```bash
# Iniciar en modo gráfico predeterminado (GUI)
python main.py
# o con argumento explícito:
python main.py --gui

# Forzar inicio en consola interactiva (Modo Seguro / Headless)
python main.py --cli
```

---

## 📂 Estructura del Proyecto
```plaintext
JsBOT/
├── config/                  # Ajustes, credenciales, plantillas ODS e iconos PNG
│   ├── assets/iconos/       # Iconografía vectorial de la interfaz
│   ├── settings.json        # Configuración centralizada de timeouts y parámetros
│   └── plantilla_base.ods   # Plantilla base institucional
├── modulos/                 # Lógica de negocio y módulos desacoplados
│   ├── auditor_reportes.py  # Motor de auditoría, balances, Turbo HTTP y exportación multiformato
│   ├── automatizador_web.py # Automatización Selenium y control de sesión
│   ├── generador_planilla.py# Motor de exportación OpenDocument (.ods)
│   ├── gestor_sesion.py     # Checkpoints de sesión y reportes de incidencias
│   ├── interfaz_grafica.py  # Aplicación de escritorio nativa (CustomTkinter)
│   ├── interfaz_usuario.py  # Interfaz de consola interactiva (Rich)
│   ├── normalizador_datos.py# Motor ETL y normalización de identidades
│   ├── orquestador.py       # Despachador bimodal y control de ejecución
│   └── verificador_entorno.py# Diagnóstico de librerías y conectividad
├── Reportes_Auditoria/      # Informes de auditoría exportados (.xlsx, .odt, .pdf, .csv)
├── Planillas/               # Planillas formativas oficiales generadas (.ods)
├── tests/                   # Suite completa de 276 tests unitarios y de estrés
├── main.py                  # Punto de entrada raíz unificado
├── windows.bat              # Lanzador resiliente para entornos Windows
├── linux.sh                 # Lanzador resiliente con auto-instalador para Linux
├── requirements.txt         # Dependencias del proyecto
└── README.md                # Documentación técnica
```

---

## 🛡️ Calidad y Resiliencia
El sistema cuenta con cobertura completa de pruebas automatizadas:
```bash
python -m unittest discover -s tests -p "test_*.py"
```
- **Tests del Inspector:** Validación de DOM fallback, modo turbo HTTP concurrente, auto-filtro en Excel y aislamiento estricto de criterios.
- **Tests de Interfaz Gráfica:** Verificación de modales bloqueantes al frente (`grab_set()`), layouts responsivos y reactividad.
- **Tests de Concurrencia y Resiliencia:** Verificación de bloqueo de procesos concurrentes y checkpoints ante caídas de red o apagones.
- **Tests de Ingesta y Normalización:** Cobertura exhaustiva de clasificación SAIME/Escolar/Sin documento, saneamiento y detección de anomalías.

---

## 👤 Autor
- **Desarrollador:** Jair Alejandro Hernández González
- **Ubicación:** San Felipe, Estado Yaracuy, República Bolivariana de Venezuela
- **GitHub:** [@CloverJH17](https://github.com/CloverJH17)
