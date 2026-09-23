"""
FACTORÍA CENTRALIZADA DE NAVEGADORES WEB (PLAYWRIGHT FACTORY) — JsBOT
Unifica el arranque de Playwright con soporte para Linux Debian/Canaima
y contextos persistentes para mantener sesiones entre ejecuciones.
"""
import sys
import os
from typing import Optional, Tuple

from playwright.sync_api import sync_playwright, Playwright, BrowserContext


def _resolver_config_navegador(pw: Playwright, nombre: str):
    """Mapea un nombre de navegador a su tipo en Playwright, canal del sistema y subcarpeta."""
    nom = str(nombre).strip().lower()
    if "firefox" in nom:
        return pw.firefox, None, "firefox"
    elif "webkit" in nom or "safari" in nom:
        return pw.webkit, None, "webkit"
    elif "edge" in nom or "msedge" in nom:
        return pw.chromium, "msedge", "chromium"
    elif "chrome" in nom and "chromium" not in nom:
        return pw.chromium, "chrome", "chromium"
    else:
        return pw.chromium, None, "chromium"


def _construir_cascada(preferido: Optional[str] = None) -> list:
    """
    Construye la lista ordenada de navegadores a intentar:
      1. Navegador preferido
      2. chrome
      3. firefox
      4. chromium
      5. edge
    """
    orden_base = ["chrome", "firefox", "chromium", "edge"]
    candidatos = []
    if preferido:
        pref = str(preferido).strip().lower()
        if pref in ("google chrome", "google-chrome"):
            pref = "chrome"
        elif pref in ("microsoft edge", "msedge"):
            pref = "edge"
        elif pref in ("mozilla firefox",):
            pref = "firefox"
        candidatos.append(pref)

    for item in orden_base:
        if item not in candidatos:
            candidatos.append(item)
    return candidatos


def obtener_contexto_playwright(
    headless: bool = False,
    navegador: str = "chromium",
    user_data_dir: Optional[str] = None,
    timeout_pagina: int = 30000,
) -> Tuple[Playwright, BrowserContext]:
    """
    Instancia y retorna un contexto persistente Playwright configurado,
    evaluando la cascada resiliente:
      1. Navegador preferido
      2. Google Chrome (channel="chrome")
      3. Mozilla Firefox
      4. Chromium interno
      5. Microsoft Edge (channel="msedge")
    """
    pw = sync_playwright().start()

    args = []
    if sys.platform.startswith("linux"):
        args.extend(["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])

    cascada = _construir_cascada(navegador)
    ultimo_error = None

    for i, nombre_cand in enumerate(cascada):
        browser_type, channel, subfolder = _resolver_config_navegador(pw, nombre_cand)
        launch_kwargs = {
            "headless": headless,
            "args": list(args),
        }
        if channel:
            launch_kwargs["channel"] = channel

        try:
            if user_data_dir:
                motor_dir = os.path.join(user_data_dir, subfolder)
                os.makedirs(motor_dir, exist_ok=True)
                context = browser_type.launch_persistent_context(
                    user_data_dir=motor_dir,
                    **launch_kwargs
                )
            else:
                browser = browser_type.launch(**launch_kwargs)
                context = browser.new_context(no_viewport=True) if not headless else browser.new_context()

            # Timeout de navegación global (en ms)
            context.set_default_navigation_timeout(timeout_pagina)
            context.set_default_timeout(timeout_pagina)

            if i > 0:
                print(f"[INFO] Cascada activada: Conmutado exitosamente a '{nombre_cand}'.")
            return pw, context

        except Exception as err:
            ultimo_error = err
            # Si el canal específico falló, intentar sin canal antes de pasar al siguiente
            if channel:
                try:
                    launch_kwargs_sin_canal = dict(launch_kwargs)
                    launch_kwargs_sin_canal.pop("channel", None)
                    if user_data_dir:
                        motor_dir = os.path.join(user_data_dir, subfolder)
                        context = browser_type.launch_persistent_context(
                            user_data_dir=motor_dir,
                            **launch_kwargs_sin_canal
                        )
                    else:
                        browser = browser_type.launch(**launch_kwargs_sin_canal)
                        context = browser.new_context(no_viewport=True) if not headless else browser.new_context()
                    context.set_default_navigation_timeout(timeout_pagina)
                    context.set_default_timeout(timeout_pagina)
                    print(f"[INFO] Cascada activada: Conmutado a '{nombre_cand}' (modo estándar).")
                    return pw, context
                except Exception:
                    pass

            print(f"[AVISO] Fallo al iniciar navegador '{nombre_cand}': {err}. Intentando siguiente opción en cascada...")

    # Si se agotaron todas las opciones de la cascada
    try:
        pw.stop()
    except Exception:
        pass
    raise RuntimeError(
        f"No se pudo iniciar ningún navegador de la cascada {cascada}. "
        f"Último error: {ultimo_error}"
    )


# Alias de compatibilidad para código que importaba obtener_driver_resiliente
def obtener_driver_resiliente(
    headless: bool = False,
    navegador_preferido: Optional[str] = None,
    **kwargs
) -> Tuple[Playwright, BrowserContext]:
    """
    Alias de compatibilidad. Retorna (pw, context) Playwright.
    El parámetro navegador_preferido mapea a los tipos Playwright:
      chromium / chrome → chromium
      firefox           → firefox
      webkit / safari   → webkit
    """
    nav = str(navegador_preferido or "chromium").lower()
    # Normalizar nombres legacy de Selenium
    if nav in ("chrome", "google chrome"):
        nav = "chromium"
    elif nav in ("edge", "microsoft edge"):
        nav = "chromium"  # Edge es Chromium-based; usar chromium
    return obtener_contexto_playwright(headless=headless, navegador=nav)
