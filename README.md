# 🤖 JsBOT — Sistema RPA, Normalización ETL y Analítica de Auditoría (v5.3.1)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![UI](https://img.shields.io/badge/GUI-CustomTkinter-blueviolet.svg)](https://customtkinter.tomschimansky.com/)
[![CLI](https://img.shields.io/badge/CLI-Rich%20%2B%20InquirerPy-cyan.svg)](https://github.com/Textualize/rich)
[![Automation](https://img.shields.io/badge/Engine-Playwright%20%2B%20HTTP%20Turbo-green.svg)](https://playwright.dev/python/)
[![Tests](https://img.shields.io/badge/Tests-504%20passed%20%2F%201%20skipped-success.svg)](#calidad-y-resiliencia)
[![OS](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20(Canaima%20%2F%20Mint)-lightgrey.svg)](#requisitos-e-instalación)
[![Architecture](https://img.shields.io/badge/Memory-Codebase%20Memory%203D-orange.svg)](#-arquitectura-y-grafo-de-conocimiento)

> **JsBOT** es una suite integral de Automatización Robótica de Procesos (RPA), procesamiento ETL y Analítica de Auditoría diseñada para la normalización, validación documental, inyección masiva de participantes, generación de actas formativas ODS/XLSX y auditoría operativa de alto rendimiento en la plataforma institucional InfoApp (Fundación Infocentro).

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
  - **Exportación Multiformato:** Generación en 1 clic de reportes en Excel (.xlsx con auto-filtro en todas las hojas), LibreOffice Calc (.ods con 4 hojas), PDF (.pdf tabular en UTF-8), CSV (.csv) o Consola con diálogo de guardado y apertura automática en el sistema operativo.
- **Verificador Post-Carga y Anti-Duplicados:**
  - Confirmación instantánea (0.5s) de participantes y servicios cargados contrastando directamente contra la base de datos de InfoApp (`verificador_cargas_export.py`).
  - Extracción previa de participantes existentes para prevenir duplicidades en aula.
- **Generador de Planillas Oficiales desde InfoApp:**
  - Generación de planillas oficiales ODS y XLSX de asistencia con datos reales descargados desde cualquier ID de actividad en InfoApp.
- **Diagnóstico Preventivo del Facilitador:**
  - Detección proactiva de actividades creadas sin participantes cargados o inconsistencias de registro (`diagnostico_facilitador.py`).
- **Bitácora Atómica en SQLite:**
  - Registro de eventos y auditorías en tabla indexada `app_logs` dentro de `data/jsbot.db` con transacciones ACID y modo WAL.
  - Purga automática y retención inteligente a 30 días, eliminando archivos de texto redundantes en disco.
- **Motor ETL de Normalización Inteligente:**
  - Ingesta multi-formato (`.xlsx`, `.ods`, `.csv`, `.txt`) con Calamine Workbook y Pandas fallback en milisegundos.
  - Ingesta tolerante a numeración y viñetas en cabeceras (`1.N°`, `3.Nombres`, `4.Apellidos`, `5.Cédula de Identidad (si aplica)`, etc.) con limpieza de prefijos y límites de palabra (`\b`).
  - Apertura asistida e interactiva en la suite ofimática local (`✎ Abrir en Excel / Calc`) accesible desde el chip de archivo y desde el modal preventivo para corrección inmediata.
  - Detección automática de Cédulas SAIME (`V-`), generación de Cédulas Escolares estructuradas (`CE`), corrección de claves truncadas y protección ante menores sin documento.
  - Limpieza de cadenas a formato Title Case institucional y saneamiento telefónico estandarizado a 11 dígitos.
- **Blindaje y Concurrencia:**
  - Cerrojo de exclusión mutua (`file lock`) para prevenir instancias duplicadas.
  - Fuente única de versión centralizada en `modulos/version.py` sincronizada con `config/settings.json`.
  - Suite certificada con 505 pruebas unitarias, de estrés, de regresión, seguridad e interfaz gráfica: 504 aprobadas y 1 omitida por dependencia externa de entorno.

---

## 🖥️ Módulos de la Interfaz

| Sección | Función Operativa |
| :--- | :--- |
| **Diagnóstico** | Matriz de tarjetas en tiempo real (Python, SO, librerías, conectividad y navegador). |
| **Credenciales** | Administración segura de usuario y contraseña para la plataforma InfoApp. |
| **Formación** | Carga masiva de participantes con apertura asistida y pre-vuelo ETL. |
| **Servicios** | Carga automatizada de beneficiarios con catálogo desplegable institucional ("Actividades de educación o aprendizaje"). |
| **Reportes** | Auditoría ultra rápida (50x), balances operativos, inspector modal y exportación multiformato. |
| **Planillas** | Generación directa multiformato (ODS, XLSX, PDF), pre-vuelo ETL y Ficha Formativa sin requerir RPA web. |
| **Ajustes** | Preferencia de navegador (Chrome / Edge / Chromium) y personalización operativa limpia sin placebos. |
| **Créditos** | Ficha técnica, licencias y autoría del proyecto. |

---

## 🚀 Instalación y Despliegue Express (One-Line)

JsBOT cuenta con instaladores autónomos desatendidos en una sola línea que configuran el entorno, instalan dependencias, crean accesos directos en el **Escritorio y Menú Inicio**, y registran el comando global `jsbot` en tu terminal.

### 🔷 En Windows (PowerShell)
Abre PowerShell y pega el siguiente comando:
```powershell
irm https://raw.githubusercontent.com/CloverJH17/JsBOT/main/install.ps1 | iex
```

> [!TIP]
> **¿Qué hace el instalador en Windows?**
> - Instala Python 3.12 automáticamente si no está presente en el equipo.
> - Configura el programa en `%LocalAppData%\JsBOT`.
> - Sincroniza todas las librerías (`requirements.txt`) y el navegador Playwright.
> - **Crea el acceso directo con icono oficial en tu Escritorio y en el Menú de Inicio**.
> - Registra el comando global `jsbot` para que puedas abrir el bot desde cualquier consola.
> - Inicia la aplicación de inmediato.

---

### 🐧 En Linux (Canaima / Debian / Ubuntu)
Abre tu terminal y ejecuta:
```bash
curl -sSL https://raw.githubusercontent.com/CloverJH17/JsBOT/main/install.sh | bash
```

> [!TIP]
> **¿Qué hace el instalador en Linux?**
> - Verifica y asegura paquetes base (`python3`, `pip`, `tkinter`, `venv`).
> - Configura el programa en `~/.local/share/JsBOT`.
> - Instala las librerías requeridas y navegadores de automatización.
> - **Crea el lanzador `.desktop` en el Menú de Aplicaciones y en tu Escritorio**.
> - Enlaza el comando global `~/.local/bin/jsbot` para invocarlo desde cualquier terminal.
> - Inicia la aplicación de inmediato.

---

### 🚀 Formas de Uso Diario

Una vez instalado, puedes abrir **JsBOT** de cualquiera de estas formas:

1. **Desde el Escritorio o Menú:** Haz clic en el icono oficial de **JsBOT RPA** en tu Escritorio o búscalo en el Menú de Inicio / Aplicaciones.
2. **Desde cualquier Terminal:**
   ```bash
   jsbot          # Abre la interfaz gráfica (GUI)
   jsbot --cli    # Abre en modo consola interactivo
   ```
3. **Modo Portable Tradicional:**
   - En Windows: Ejecuta `.\windows.bat` o `JsBOT_Sin_Consola.vbs`.
   - En Linux: Ejecuta `bash linux.sh`.

---

### 🗑️ Desinstalación Limpia

Si deseas retirar JsBOT de tu equipo de forma 100% limpia:
* **En Windows (PowerShell):**
  ```powershell
  irm https://raw.githubusercontent.com/CloverJH17/JsBOT/main/uninstall.ps1 | iex
  ```
* **En Linux (Terminal):**
  ```bash
  curl -sSL https://raw.githubusercontent.com/CloverJH17/JsBOT/main/uninstall.sh | bash
  ```
*(El desinstalador te consultará si deseas conservar una copia de seguridad de tus Planillas y Reportes locales generados antes de eliminar el programa).*

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
├── config/                      # Ajustes, credenciales, plantillas e iconografía
│   ├── assets/iconos/           # Iconografía vectorial y bitmap de la interfaz
│   ├── settings.json            # Configuración centralizada de timeouts y parámetros
│   ├── requirements.txt         # Dependencias técnicas del proyecto (PyPI)
│   ├── config.example.ini       # Plantilla limpia de credenciales institucionales
│   ├── config.ini               # Credenciales activas de usuario (ignorado por git)
│   ├── config_servicios.json    # Catálogo institucional de servicios y trámites
│   ├── datos_actividad.json     # Metadatos cacheados de actividad en curso
│   └── plantilla_base.ods       # Plantilla base institucional para actas
├── modulos/                     # Núcleo modular del sistema RPA
│   ├── auditor_reportes.py      # Auditoría, balances, Turbo HTTP y exportación multiformato
│   ├── automatizador_web.py     # Automatización Selenium/Playwright y control de sesión
│   ├── config_manager.py        # Gestor de configuración y sincronización de settings.json
│   ├── diagnostico_facilitador.py # Detección preventiva de actividades sin participantes
│   ├── driver_factory.py        # Fábrica resiliente de controladores (Chrome/Firefox/Edge)
│   ├── entorno.py               # Blindaje estricto de rutas, directorios y variables de entorno
│   ├── generador_planilla.py    # Motor de exportación OpenDocument (.ods y .xlsx)
│   ├── gestor_sesion.py         # Checkpoints ACID y bitácora atómica en SQLite
│   ├── identidad_utils.py       # Saneamiento de cédulas SAIME, escolares y menores
│   ├── interfaz_grafica.py      # Aplicación de escritorio nativa (CustomTkinter)
│   ├── interfaz_usuario.py      # Interfaz de consola interactiva (Rich + InquirerPy)
│   ├── motor_export_auditoria.py# Motor de extracción nativa ultra rápida (aceleración 50x)
│   ├── normalizador_datos.py    # Motor ETL, normalización de cadenas y teléfonos
│   ├── orquestador.py           # Despachador bimodal y control de ejecución
│   ├── verificador_cargas_export.py # Verificador post-carga y anti-duplicados en tiempo real
│   ├── verificador_entorno.py   # Diagnóstico de librerías y conectividad
│   ├── version.py               # Fuente única de versión del sistema
│   └── web_utils.py             # Utilidades HTTP, cabeceras y manejo seguro de red
├── data/                        # Persistencia de base de datos y cookies de sesión
│   ├── jsbot.db                 # Base de datos SQLite (telemetría, logs y checkpoints ACID)
│   └── playwright_context/      # Almacenamiento persistente de sesión y estado web
├── docs/                        # Documentación técnica y manuales
│   ├── arquitectura/            # Matriz de funciones y arquitectura del sistema
│   ├── diagramas/               # Diagramas de flujo integral y ciclo de vida
│   ├── historial/               # Historial consolidado de versiones
│   ├── manuales/                # Manuales de usuario y funcionamiento técnico
│   ├── PROJECT.md               # Bitácora técnica de arquitectura y contratos de interfaz
│   ├── REGLAS_IA.md             # Guías de codificación y estándares para asistentes IA
│   └── version.txt              # Registro cronológico de cambios (Changelog)
├── Planillas/                   # Directorio de salida para actas formativas generadas
├── Reportes_Auditoria/          # Directorio de salida para reportes analíticos (.xlsx, .pdf, .ods, .csv)
├── logs/                        # Bitácoras de eventos y registro de depuración
├── scripts/                     # Scripts auxiliares para entornos Unix/Linux
├── tests/                       # Suite completa de tests unitarios, regresión y estrés
├── main.py                      # Punto de entrada raíz unificado (GUI / CLI)
├── windows.bat                  # Instalador y lanzador nativo para Windows
├── JsBOT_Sin_Consola.vbs        # Lanzador silencioso sin ventana de terminal para Windows
├── linux.sh                     # Lanzador resiliente para Canaima / Debian / Mint
└── README.md                    # Documentación técnica oficial
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

### Servidor 3D en Tiempo Real (Codebase Memory MCP)
Para explorar la constelación 3D interactiva en vivo, indexar cambios en tiempo real o conectar el grafo con asistentes de IA:

#### 1. Instalación del servidor
Puedes instalar `codebase-memory-mcp` en la nueva máquina con cualquiera de estos métodos:

- **Desde Python (Recomendado, usa el mismo entorno de JsBOT):**
  ```bash
  pip install codebase-memory-mcp
  ```
- **Desde Node.js (vía npm global):**
  ```bash
  npm install -g codebase-memory-mcp
  ```
- **En Linux / macOS (Instalador oficial con UI):**
  ```bash
  curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash -s -- --ui
  ```

#### 2. Indexación y lanzamiento del servidor
Abre una terminal en la carpeta raíz del proyecto (`JsBOT`) y ejecuta:
```bash
# Iniciar servidor e indexación automática
codebase-memory-mcp
```
*(O de forma directa sin instalación previa si cuentas con Node.js: `npx -y codebase-memory-mcp`)*

#### 3. Abrir la constelación 3D
Abre tu navegador y entra a:
```text
http://localhost:9749
```
*(Se desplegará el mapa 3D navegable de nodos y aristas con filtros por capas, trazado de rutas y buscador de símbolos).*

---

## 👤 Autor
- **Desarrollador:** Jair Alejandro Hernández González
- **Ubicación:** San Felipe, Estado Yaracuy, República Bolivariana de Venezuela
- **GitHub:** [@CloverJH17](https://github.com/CloverJH17)
