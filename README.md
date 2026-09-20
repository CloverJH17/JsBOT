# 🤖 JsBOT — Sistema RPA, Normalización ETL y Analítica de Auditoría (v4.10.0)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![UI](https://img.shields.io/badge/GUI-CustomTkinter-blueviolet.svg)](https://customtkinter.tomschimansky.com/)
[![CLI](https://img.shields.io/badge/CLI-Rich%20%2B%20InquirerPy-cyan.svg)](https://github.com/Textualize/rich)
[![Automation](https://img.shields.io/badge/Engine-Playwright%20%2B%20HTTP%20Turbo-green.svg)](https://playwright.dev/python/)
[![Tests](https://img.shields.io/badge/Tests-404%20passed-success.svg)](#calidad-y-resiliencia)
[![OS](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20(Canaima%20%2F%20Mint)-lightgrey.svg)](#requisitos-e-instalación)
[![Architecture](https://img.shields.io/badge/Memory-Codebase%20Memory%203D-orange.svg)](#-arquitectura-y-grafo-de-conocimiento)

> **JsBOT** es una suite integral de Automatización Robótica de Procesos (RPA), procesamiento ETL y Analítica de Auditoría diseñada para la normalización, validación documental, inyección masiva de participantes, generación de actas formativas ODS/XLSX, auditoría operativa de alto rendimiento y telemetría atómica en la plataforma institucional InfoApp (Fundación Infocentro).

---

## ⚡ Características Principales

- **Arquitectura Bimodal (GUI + CLI):**
  - **Modo Gráfico Nativo:** Interfaz moderna en Dark Mode construida con CustomTkinter, optimizada para resoluciones desde 1366×768 hasta 1080p.
  - **Modo Consola Interactivo (CLI):** Menú rápido por terminal asistido por Rich e InquirerPy con banner dinámico unificado.
  - **Feature Toggle & Fallback:** Conmutación automática a consola si el entorno anfitrión carece de servidor gráfico X11/Wayland.
- **Ecosistema de Auditoría Ultra Rápida (Aceleración 50x):**
  - **Motor de Extracción Nativo (`motor_export_auditoria.py`):** Consulta directa de endpoints optimizados reduciendo tiempos de consulta de 14 minutos a solo 17 segundos en rangos masivos de 40.000+ registros.
  - **Cruce Híbrido de Seguridad:** Combina la descarga masiva con la vista HTML para rescatar actividades en borrador o con 0 participantes (0% de pérdida de registros).
  - **Auditorías Multi-criterio:** Búsqueda por Facilitador (UID con aislamiento estricto de sede), por Infocentro (código de sede) o Resumen Estadal (Región completa).
  - **Dashboard Analítico:** 4 KPIs de alto impacto con promedios por aula, sedes únicas, trámites más demandados y control de cuadre matemático (100%).
  - **Ventanas Modales al Frente:** Inspección detallada con modalidad bloqueante estricta (`grab_set()`), buscador reactivo y cabeceras clickeables para ordenamiento instantáneo.
  - **Exportación Multiformato:** Generación en 1 clic de reportes en Excel (.xlsx con auto-filtro en todas las hojas), LibreOffice (.odt), PDF (.pdf), CSV (.csv) o Consola con diálogo de guardado y apertura automática en el sistema operativo.
- **Verificador Post-Carga y Anti-Duplicados:**
  - Confirmación instantánea (0.5s) de participantes y servicios cargados contrastando directamente contra la base de datos de InfoApp (`verificador_cargas_export.py`).
  - Extracción previa de participantes existentes para prevenir duplicidades en aula.
- **Generador de Planillas Oficiales desde InfoApp:**
  - Generación de planillas oficiales ODS y XLSX de asistencia con datos reales descargados desde cualquier ID de actividad en InfoApp.
- **Diagnóstico Preventivo del Facilitador:**
  - Detección proactiva de actividades creadas sin participantes cargados o inconsistencias de registro (`diagnostico_facilitador.py`).
- **Telemetría y Bitácora Atómica en SQLite:**
  - Registro de eventos y auditorías en tabla indexada `app_logs` dentro de `data/jsbot.db` con transacciones ACID y modo WAL.
  - Purga automática y retención inteligente a 30 días, eliminando archivos de texto redundantes en disco.
- **Motor ETL de Normalización Inteligente:**
  - Ingesta multi-formato (`.xlsx`, `.ods`, `.csv`, `.txt`).
  - Detección automática de Cédulas SAIME (`V-`), generación de Cédulas Escolares estructuradas (`CE`), corrección de claves truncadas y protección ante menores sin documento.
  - Limpieza de cadenas a formato Title Case institucional y saneamiento telefónico estandarizado a 11 dígitos.
- **Blindaje y Concurrencia:**
  - Cerrojo de exclusión mutua (`file lock`) para prevenir instancias duplicadas.
  - Fuente única de versión centralizada en `modulos/version.py` sincronizada con `config/settings.json`.
  - Suite certificada con más de 280 pruebas unitarias, de estrés y de regresión ante cortes abruptos de red o fallos eléctricos.

---

## 🖥️ Módulos de la Interfaz

| Sección | Función Operativa |
| :--- | :--- |
| **Diagnóstico** | Matriz de tarjetas en tiempo real (Python, SO, librerías, conectividad y navegador). |
| **Credenciales** | Administración segura de usuario y contraseña para la plataforma InfoApp. |
| **Formación** | Carga masiva de participantes en actividades y cursos formativos. |
| **Servicios** | Carga automatizada de beneficiarios con catálogo desplegable institucional ("Actividades de educación o aprendizaje"). |
| **Reportes** | Auditoría ultra rápida (50x), balances operativos, inspector modal y exportación multiformato. |
| **Planillas** | Generación directa multiformato (ODS, XLSX, PDF), pre-vuelo ETL y Ficha Formativa sin requerir RPA web. |
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
- **Modo Estándar (con terminal de apoyo):** Haz doble clic sobre `windows.bat` o ejecuta desde PowerShell / CMD:
  ```dos
  windows.bat
  ```
- **Modo Silencioso (sin consola emergente):** Haz doble clic sobre `JsBOT_Sin_Consola.vbs`.

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
├── config/                  # Ajustes, credenciales, plantilla ODS e iconos PNG
│   ├── assets/iconos/       # Iconografía vectorial de la interfaz
│   ├── settings.json        # Configuración centralizada de timeouts y parámetros
│   ├── requirements.txt     # Dependencias técnicas del proyecto
│   ├── config.example.ini   # Plantilla limpia de credenciales
│   └── plantilla_base.ods   # Plantilla base institucional
├── modulos/                 # Núcleo modular del sistema RPA
│   ├── auditor_reportes.py  # Auditoría, balances, Turbo HTTP y exportación multiformato
│   ├── motor_export_auditoria.py # Motor de extracción nativa ultra rápida (aceleración 50x)
│   ├── verificador_cargas_export.py # Verificador post-carga y anti-duplicados en tiempo real
│   ├── diagnostico_facilitador.py # Diagnóstico preventivo de actividades sin participantes
│   ├── automatizador_web.py # Automatización Selenium/Playwright y control de sesión
│   ├── generador_planilla.py# Motor de exportación OpenDocument (.ods y .xlsx)
│   ├── gestor_sesion.py     # Checkpoints ACID y bitácora atómica en SQLite
│   ├── interfaz_grafica.py  # Aplicación de escritorio nativa (CustomTkinter)
│   ├── interfaz_usuario.py  # Interfaz de consola interactiva (Rich + InquirerPy)
│   ├── normalizador_datos.py# Motor ETL y normalización de identidades
│   ├── orquestador.py       # Despachador bimodal y control de ejecución
│   ├── verificador_entorno.py# Diagnóstico de librerías y conectividad
│   ├── version.py           # Fuente única de versión del sistema
│   └── entorno.py           # Blindaje estricto de rutas y directorios
├── data/                    # Base de datos SQLite (jsbot.db) para telemetría y checkpoints
├── docs/                    # Documentación arquitectónica, manuales e historial consolidado
│   ├── arquitectura/        # Matriz y funciones de contexto
│   ├── diagramas/           # Diagrama de flujo integral del sistema
│   ├── manuales/            # Manual de funcionamiento técnico
│   └── historial/           # version.txt consolidado
├── Features/                # Entorno de pruebas y desarrollo de nuevos features
├── tests/                   # Suite completa de tests unitarios, regresión y estrés
├── main.py                  # Punto de entrada raíz unificado
├── windows.bat              # Lanzador nativo para Windows
├── JsBOT_Sin_Consola.vbs    # Lanzador silencioso sin ventana de terminal para Windows
├── linux.sh                 # Lanzador resiliente para Canaima / Linux Mint
└── README.md                # Documentación técnica oficial
```

---

## 🛡️ Calidad y Resiliencia
El sistema cuenta con cobertura completa de pruebas automatizadas con aislamiento de procesos para widgets gráficos:
```bash
# Linux / Canaima
for f in tests/test_*.py; do python3 -m pytest "$f" -q --tb=short; done
```
```powershell
# Windows PowerShell
Get-ChildItem tests\test_*.py | ForEach-Object { python -m pytest $_.FullName -q --tb=short }
```
- **Tests del Motor Ultra Rápido:** Verificación de concurrencia, cruce híbrido y tolerancia a fallos.
- **Tests de Interfaz Gráfica:** Modales bloqueantes al frente (`grab_set()`), layouts responsivos y reactividad.
- **Tests de Concurrencia y Resiliencia:** Bloqueo de instancias duplicadas y checkpoints ACID ante cortes eléctricos.
- **Tests de Ingesta y Normalización:** Cobertura exhaustiva de clasificación SAIME/Escolar/Sin documento y saneamiento telefónico.

---

## 🧠 Arquitectura y Grafo de Conocimiento (Codebase Memory)

JsBOT cuenta con un grafo de conocimiento y memoria estructural relacional indexado mediante [Codebase Memory MCP](https://github.com/DeusData/codebase-memory-mcp) que mapea de forma determinista todas las funciones, métodos, clases y flujos de ejecución del proyecto:

* **Topología Indexada:** 1.148 nodos y 5.034 aristas relacionales (`CALLS`, `DEFINES`, `TESTS`, `IMPORTS`).
* **Cero Código Muerto:** Arquitectura 100% cohesionada con desacoplamiento estricto entre presentación (GUI/CLI), lógica ETL (`normalizador_datos.py`), auditoría (`auditor_reportes.py`) y persistencia ACID (`gestor_sesion.py`).
* **Visualización 3D Interactiva:** Mapa de constelación navegable en tiempo real a través del servidor web integrado en el puerto `9749`.

```bash
# Iniciar servidor y explorar el grafo 3D del proyecto
codebase-memory-mcp
# Navegar a: http://localhost:9749
```

---

## 👤 Autor
- **Desarrollador:** Jair Alejandro Hernández González
- **Ubicación:** San Felipe, Estado Yaracuy, República Bolivariana de Venezuela
- **GitHub:** [@CloverJH17](https://github.com/CloverJH17)
