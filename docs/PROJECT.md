# Project: JsBOT v5.1.0 Architecture & Robustness Specification

## Architecture
- **GUI Engine**: CustomTkinter on top of Tkinter / Tcl.
- **Threading Model**: Main thread strictly runs Tkinter event loop (`mainloop()`) and polling loop (`_iniciar_escucha_cola` every 35 ms via `.after()`). All heavy computations (Pandas, Playwright, OpenPyXL, ODS/report generation) and network/disk I/O run on background daemon threads and communicate exclusively through `cola_eventos = queue.Queue()`.
- **Modal Lifecycle**: Centralized tracking in `self.modales_activos: dict[str, ctk.CTkToplevel]`. Every modal registers a `"WM_DELETE_WINDOW"` protocol, releases grabs safely, and cleans up upon dismissal, view change, or session reset.
- **View Navigation**: Canonical view registry and accent-insensitive normalization (`normalizar_clave_vista`). Frame switching operates on unique widget instances (`set(self.vistas.values())`) preventing self-ungriding bugs.
- **Canaima GNU/Linux Shielding**: Early injection of `os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")` before graphics/Tk imports, plus headless/X11 display fallback detection (`verificar_display_linux()`).
- **Turbo Export Engine & Secure Crawlers**: High-throughput extraction via `motor_export_auditoria.py` with sanitized SQL parameters and uncoupled HTTP crawlers in `auditor_reportes.py`.
- **Security & Parameterized Automation**: DOM interactions in `automatizador_web.py` use parameterized `page.evaluate(script, payload)` eliminating JavaScript injection vulnerabilities.
- **ACID Session Recovery**: Two-tier session recovery via SQLite (`data/jsbot.db`) and atomic JSON checkpoints, propagating `OSError` on disk write failures.

## Feature Inventory
| # | Feature | Description | Milestone | Source | Status |
|---|---------|-------------|-----------|--------|--------|
| 1 | Modal Registry (`self.modales_activos`) | Centralized dictionary and registration/cleanup methods for all active `CTkToplevel` instances | M1 | Survey (R1) | DONE |
| 2 | Safe Protocol (`WM_DELETE_WINDOW`) | Register closure handlers on all 8 `CTkToplevel` instances releasing grabs and triggering cancel callbacks | M1 | Survey (R1) | DONE |
| 3 | Safe Grab Management | Balanced `grab_set()` and `grab_release()` preventing focus deadlocks on Windows and X11 | M1 | Survey (R1) | DONE |
| 4 | Auto-close Modals on View Change / Reset | Hook `cerrar_modales_activos()` into view switching, file discarding, and main window close | M1 | Survey (R1) | DONE |
| 5 | Telemetry Queue Unification | Route all log/status updates in `_hilo_proceso_carga_formacion` and `_hilo_proceso_carga_servicios` through `cola_eventos` instead of direct `self.after(0)` | M2 | Survey (R2) | DONE |
| 6 | Asynchronous Report Export | Decouple `ar.exportar_reporte_auditoria` to background thread, notifying GUI via `cola_eventos` | M2 | Survey (R2) | DONE |
| 7 | Non-blocking Settings & Cache I/O | Decouple inspector cache save (`guardar_cache_inspector`) and ensure settings saving does not freeze GUI | M2 | Survey (R2) | DONE |
| 8 | Canonical Navigation Dispatchers | Implement `cambiar_vista`, `_cambiar_vista`, `mostrar_vista`, `_mostrar_vista`, `cambiar_seccion`, `mostrar_seccion` | M3 | Survey (R3) | DONE |
| 9 | Accent-Insensitive View Normalization | Support `"Diagnóstico"`/`"Diagnostico"`, `"Créditos"`/`"Creditos"` seamlessly in navigation | M3 | Survey (R3) | DONE |
| 10 | Fix Formación Self-Ungriding Bug | Iterate over distinct widget instances in `_cambiar_seccion` using identity checks to prevent ungriding alias | M3 | Survey (R3) | DONE |
| 11 | Fix Typo in Session Recovery | Fix `_cambiar_vista` calls in `_reanudar_flujo_desde_estado` to canonical navigation dispatch | M3 | Survey (R3) | DONE |
| 12 | Early `LIBGL_ALWAYS_SOFTWARE=1` Injection | Inject `LIBGL_ALWAYS_SOFTWARE=1` in `main.py`, `modulos/entorno.py`, and `modulos/interfaz_grafica.py` before Tk imports | M4 | Survey (R4) | DONE |
| 13 | Headless Display Detection | Graceful `DISPLAY`/`WAYLAND_DISPLAY` check in Linux before GUI startup | M4 | Survey (R4) | DONE |
| 14 | 65 GUI Audit Tests Verification | Run `pytest tests/test_auditoria_completa_ui_ux.py` verifying 65/65 tests pass | M5 | Acceptance Criteria | DONE |
| 15 | Global Test Suite & Regression Guard | Verify full test suite passes with zero regressions | M5 | Acceptance Criteria | DONE |
| 16 | SQL Sanitization & Injection Defense | Strict `sanitizar_texto_sql`, `validar_codigo_sql` (with `--` comment stripping), and `validar_fecha_sql` | M6 | Security Refactor | DONE |
| 17 | JavaScript Injection Elimination | Strict parameterized `page.evaluate(script, payload)` across all dynamic DOM inputs | M6 | Security Refactor | DONE |
| 18 | Crawler & Export Decoupling | Decouple `consultar_actividades_infoapp_http_crawler` and `consultar_servicios_infoapp_http_crawler` eliminating circular fallback | M6 | Architecture | DONE |
| 19 | Centralized Activity Classification | Unified `obtener_tipo_clasificacion_actividad` consumed across ODS, XLSX, PDF, and GUI views | M6 | Architecture | DONE |
| 20 | SQLite Recovery & Exception Logging | Replace silent passes with SQLite recovery fallback and detailed logging in session manager | M6 | Architecture | DONE |
| 21 | Placebo Config Purge | Eradicate non-functional configuration switches (`start_maximized`) across UI and JSON settings | M6 | Architecture | DONE |
| 22 | Cloud Telemetry & One-Line Deployers | Multi-platform unattended deployment (`install.ps1`, `install.sh`) and Google Apps Script telemetry | M7 | Operations | DONE |

## Milestones
| # | Name | Scope | Dependencies | Status | Key Verification Output |
|---|------|-------|-------------|--------|-------------------------|
| 1 | M1: Modal Lifecycle Management (R1) | Centralized modal registry, `WM_DELETE_WINDOW` on all 8 modals, safe grab release, auto-close on view change | None | DONE | 8 modals verified; grab released cleanly; 5/5 modal tests passed; 19/19 adversarial tests passed |
| 2 | M2: GUI Thread Decoupling & Queue Polling (R2) | Replace `after(0)` in load workers with `cola_eventos.put`, background thread for report export, non-blocking cache save | M1 | DONE | 10,000 events stress tested with 0 drops; background I/O < 24ms; Doherty startup < 2.5s, navigation < 100ms |
| 3 | M3: View Navigation & Normalization (R3) | Canonical navigation aliases, accent normalization (`normalizar_clave_vista`), identity-based frame switching | M1 | DONE | Unicode NFKD accent normalization passed; self-ungriding eliminated; canonical aliases functioning |
| 4 | M4: Canaima GNU/Linux Compatibility (R4) | Early `LIBGL_ALWAYS_SOFTWARE=1` injection, `DISPLAY` checking in `modulos/entorno.py` and `main.py` | None | DONE | Early injection verified in main.py, entorno.py, interfaz_grafica.py; display check verified |
| 5 | M5: Acceptance & Full Suite Regression Verification | Run all 65 audit tests in `tests/test_auditoria_completa_ui_ux.py` + full test suite, verify no regressions | M1, M2, M3, M4 | DONE | 391/391 comprehensive unit, stress, and GUI tests passed (100%); 0 regressions; Forensic Audit CLEAN |
| 6 | M6: Security Hardening & Crawler Decoupling | SQL parameter sanitization, safe JS evaluate payloads, decoupled crawlers, centralized classification, SQLite fallback, placebo purge | M1-M5 | DONE | 9 new unit tests in `test_blindaje_refactor.py`; 452/452 tests passed (100%) |
| 7 | M7: One-Line Deployers & Cloud Telemetry | Unattended install/uninstall scripts (`.ps1`, `.sh`), desktop/menu integration, cloud telemetry to Google Sheets | M1-M6 | DONE | `test_instaladores_y_telemetria.py` passing; verified SemVer v5.1.0 consistency |

## Interface Contracts
### Modal Registry ↔ `JsBotGUI`
```python
def registrar_modal(self, nombre: str, modal: ctk.CTkToplevel, grab: bool = True, al_cerrar: Optional[Callable] = None) -> ctk.CTkToplevel:
    """Registers an active modal in self.modales_activos, configures WM_DELETE_WINDOW protocol and safe grab."""

def cerrar_modal(self, nombre_o_instancia: Union[str, ctk.CTkToplevel]) -> None:
    """Safely releases grab, unregisters, and destroys the specified modal."""

def cerrar_modales_activos(self, excluir: Optional[Union[str, ctk.CTkToplevel]] = None) -> None:
    """Closes all tracked secondary modals. Invoked during view transitions, file discards, and main window close."""
```

### Event Queue (`cola_eventos`) ↔ GUI Main Loop
```python
# Event tuples pushed by background workers:
("log", str_message)                  # Appended to telemetry via self.agregar_log_telemetria
("log_auditoria", str_message)        # Appended to inspector audit log
("fin_auditoria", dict_resultado)     # Triggers audit completion handler
("exportacion_ok", str_ruta_final)    # Notifies user of successful export without freezing UI
("exportacion_error", str_error_msg)  # Notifies user of export failure
```

### Navigation Normalization ↔ `JsBotGUI`
```python
def normalizar_clave_vista(clave: str) -> str:
    """Converts view names (case-insensitive, accent-insensitive) to canonical key."""

# Canonical dispatchers on JsBotGUI:
def cambiar_vista(self, seccion: str) -> None
def mostrar_vista(self, seccion: str) -> None
def _cambiar_vista(self, seccion: str) -> None
def _mostrar_vista(self, seccion: str) -> None
def cambiar_seccion(self, seccion: str) -> None
def _cambiar_seccion(self, seccion: str) -> None
```

### SQL Sanitization & Crawler Contracts
```python
# Sanitizers in motor_export_auditoria.py:
def sanitizar_texto_sql(valor: str) -> str
def validar_codigo_sql(valor: str) -> str
def validar_fecha_sql(valor: str) -> str

# Decoupled Pure Crawlers in auditor_reportes.py:
def consultar_actividades_infoapp_http_crawler(session, base_url, criterio, valor, fecha_inicio, fecha_fin, page_timeout=20) -> list[dict]
def consultar_servicios_infoapp_http_crawler(session, base_url, criterio, valor, fecha_inicio, fecha_fin, page_timeout=20) -> list[dict]

# Centralized Classification:
def obtener_tipo_clasificacion_actividad(tipo_raw: str, area_formacion_raw: str = "", nombre_taller_raw: str = "") -> str
```

## Code Layout
- `modulos/interfaz_grafica.py`: Primary GUI code (modal lifecycle, queue polling, navigation dispatch, view frames).
- `modulos/config_manager.py`: Configuration and settings persistence (`settings.json`).
- `modulos/auditor_reportes.py`: Inspector logic, pure crawlers, cache persistence, and export functions.
- `modulos/motor_export_auditoria.py`: Accelerated SQL export engine with strict query sanitization and crawler fallback.
- `modulos/automatizador_web.py`: Web automation with parameterized `page.evaluate()` and DOM error recovery.
- `modulos/gestor_sesion.py`: SQLite session persistence, checkpoint management, and audit Excel export.
- `modulos/normalizador_datos.py`: ETL pipeline, participant deduplication, and field sanitization.
- `modulos/generador_planilla.py`: ODS and XLSX official document generator.
- `modulos/verificador_cargas_export.py`: Instant post-upload verification and duplicate prevention.
- `modulos/diagnostico_facilitador.py`: Proactive facilitator activity health scanner.
- `modulos/telemetria.py`: Asynchronous cloud telemetry to Google Sheets.
- `modulos/entorno.py`: Environment verification, `LIBGL_ALWAYS_SOFTWARE=1` configuration, and display checks.
- `main.py`: Main application entry point with Canaima software rendering guard.
- `tests/test_blindaje_refactor.py`: 9-test unit suite verifying SQL sanitization, JS safety, and uncoupled crawlers.
- `tests/test_auditoria_completa_ui_ux.py`: 65-test comprehensive GUI audit suite.
