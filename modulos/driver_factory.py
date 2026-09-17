"""
FACTORÍA CENTRALIZADA DE NAVEGADORES WEB (PLAYWRIGHT FACTORY) — JsBOT
Unifica el arranque de Playwright con soporte para Linux Debian/Canaima
y contextos persistentes para mantener sesiones entre ejecuciones.
"""
import sys
import os
from typing import Optional, Tuple

from playwright.sync_api import sync_playwright, Playwright, BrowserContext


def obtener_contexto_playwright(
    headless: bool = False,
    navegador: str = "chromium",
    user_data_dir: Optional[str] = None,
    timeout_pagina: int = 30000,
) -> Tuple[Playwright, BrowserContext]:
    """
    Instancia y retorna un contexto persistente Playwright configurado.

    Playwright usa auto-waiting nativo — no se necesitan timeouts manuales
    para elementos web. El parámetro timeout_pagina (en ms) controla la
    espera máxima de navegación.

    Retorna (pw, context) que el llamador debe cerrar con context.close() + pw.stop().
    """
    pw = sync_playwright().start()

    # Selección del tipo de navegador (chromium por defecto)
    nombre = str(navegador).strip().lower()
    if "firefox" in nombre:
        browser_type = pw.firefox
    elif "webkit" in nombre or "safari" in nombre:
        browser_type = pw.webkit
    else:
        browser_type = pw.chromium

    args = []
    if sys.platform.startswith("linux"):
        args.extend(["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])

    launch_kwargs = {
        "headless": headless,
        "args": args,
    }

    if "chrome" in nombre and "chromium" not in nombre:
        launch_kwargs["channel"] = "chrome"
    elif "edge" in nombre or "msedge" in nombre:
        launch_kwargs["channel"] = "msedge"

    if user_data_dir:
        subfolder = "firefox" if "firefox" in nombre else "webkit" if ("webkit" in nombre or "safari" in nombre) else "chromium"
        motor_dir = os.path.join(user_data_dir, subfolder)
        os.makedirs(motor_dir, exist_ok=True)
        try:
            context = browser_type.launch_persistent_context(
                user_data_dir=motor_dir,
                **launch_kwargs
            )
        except Exception:
            # Fallback a chromium estándar si el canal específico falla
            launch_kwargs.pop("channel", None)
            context = browser_type.launch_persistent_context(
                user_data_dir=motor_dir,
                **launch_kwargs
            )
    else:
        try:
            browser = browser_type.launch(**launch_kwargs)
        except Exception:
            launch_kwargs.pop("channel", None)
            browser = browser_type.launch(**launch_kwargs)
        context = browser.new_context(no_viewport=True) if not headless else browser.new_context()

    # Timeout de navegación global (en ms)
    context.set_default_navigation_timeout(timeout_pagina)
    context.set_default_timeout(timeout_pagina)

    return pw, context


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
