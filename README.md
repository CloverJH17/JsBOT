# 🤖 JsBOT — Sistema RPA y Normalización ETL de Participantes (v4.0.0)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![UI](https://img.shields.io/badge/GUI-CustomTkinter-blueviolet.svg)](https://customtkinter.tomschimansky.com/)
[![CLI](https://img.shields.io/badge/CLI-Rich%20%2B%20InquirerPy-cyan.svg)](https://github.com/Textualize/rich)
[![Automation](https://img.shields.io/badge/Engine-Selenium-green.svg)](https://www.selenium.dev/)
[![Tests](https://img.shields.io/badge/Tests-240%20passed-success.svg)](#calidad-y-resiliencia)
[![OS](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20(Canaima%20%2F%20Mint)-lightgrey.svg)](#requisitos-e-instalación)

> **JsBOT** es una herramienta de Automatización Robótica de Procesos (RPA) y procesamiento ETL diseñada para la normalización, validación, cálculo de identificadores escolares/menores y carga masiva de participantes en la plataforma institucional InfoApp (Fundación Infocentro).

---

## ⚡ Características Principales

- **Arquitectura Bimodal (GUI + CLI):**
  - **Modo Gráfico Nativo:** Interfaz moderna en Dark Mode construida con CustomTkinter, optimizada para resoluciones desde 1366×768 hasta 1080p.
  - **Modo Consola Interactivo (CLI):** Menú rápido por terminal asistido por Rich e InquirerPy.
  - **Feature Toggle & Fallback:** Conmutación automática a consola si el entorno anfitrión carece de servidor gráfico X11/Wayland.
- **Motor ETL de Normalización Inteligente:**
  - Ingesta multi-formato (`.xlsx`, `.ods`, `.csv`).
  - Detección automática de Cédulas SAIME (`V-`), generación de Cédulas Escolares estructuradas (`CE`) y gestión de menores sin documento (`S/C`).
  - Limpieza de cadenas a formato Title Case institucional y saneamiento telefónico.
- **Auditoría Previa (Pre-Flight Data Panel):**
  - Panel de resumen de datos antes de disparar Selenium.
  - Visor modal tabular (`CTkToplevel`) para inspeccionar la lista normalizada de alumnos en vivo.
- **Planillas Oficiales ODS:**
  - Generación directa de reportes y actas formativas en formato abierto OpenDocument Spreadsheet (`.ods`).
- **Blindaje y Concurrencia:**
  - Cerrojo de exclusión mutua (`file lock`) para prevenir instancias duplicadas.
  - Suite certificada con más de 240 pruebas unitarias y de estrés ante cortes abruptos de red o fallos eléctricos.

---

## 🖥️ Módulos de la Interfaz

| Sección | Función Operativa |
| :--- | :--- |
| **Formación** | Carga masiva de participantes en actividades y cursos formativos. |
| **Servicios** | Carga automatizada de beneficiarios y registros de atención comunitaria. |
| **Reportes** | Generación de planillas oficiales `.ods` y apertura de trazas de ejecución. |
| **Diagnóstico** | Matriz de tarjetas en tiempo real (Python, SO, librerías, conectividad y navegador). |
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
├── config/                  # Ajustes, selectores web, plantillas ODS e iconos PNG
│   ├── assets/iconos/       # Iconografía vectorial de la interfaz
│   ├── settings.json        # Configuración centralizada de timeouts y parámetros
│   └── plantilla_base.ods   # Plantilla base institucional
├── modulos/                 # Lógica de negocio y módulos desacoplados
│   ├── automatizador_web.py # Automatización Selenium y control de sesión
│   ├── generador_planilla.py# Motor de exportación OpenDocument (.ods)
│   ├── interfaz_grafica.py  # Aplicación de escritorio nativa (CustomTkinter)
│   ├── interfaz_usuario.py  # Interfaz de consola interactiva (Rich)
│   ├── normalizador_datos.py# Motor ETL y normalización de identidades
│   ├── orquestador.py       # Despachador bimodal y control de ejecución
│   └── verificador_entorno.py# Diagnóstico de librerías y conectividad
├── tests/                   # Suite completa de 240+ tests unitarios y de estrés
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
python -m unittest discover tests
```
- **Tests de Concurrencia:** Verificación de bloqueo de procesos concurrentes.
- **Tests de Ingesta:** Cobertura de casos límites en archivos Excel/CSV corruptos o mal estructurados.
- **Tests de Normalización:** Validación de fórmulas de cédula escolar y saneamiento de cadenas.

---

## 👤 Autor
- **Desarrollador:** Jair Alejandro Hernández González
- **Ubicación:** San Felipe, Estado Yaracuy, República Bolivariana de Venezuela
- **GitHub:** [@CloverJH17](https://github.com/CloverJH17)
