"""
FACTORÍA CENTRALIZADA DE NAVEGADORES WEB (WEBDRIVER FACTORY) — JsBOT
Unifica el arranque de Selenium con blindaje para Linux Debian/Canaima y timeouts de red.
"""
import sys
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions

def obtener_driver_resiliente(
    headless: bool = False, 
    timeout_pagina: int = 30, 
    timeout_script: int = 20,
    navegador_preferido: Optional[str] = None
) -> Optional[webdriver.Remote]:
    """
    Instancia y retorna un WebDriver configurado con cascada Chrome -> Firefox -> Edge (o navegador preferido).
    Inyecta blindaje crítico para entornos Linux/Canaima y timeouts de socket anti-bloqueo.
    """
    def _crear_chrome():
        opts_chrome = ChromeOptions()
        if headless:
            opts_chrome.add_argument("--headless=new")
        opts_chrome.add_argument("--start-maximized")
        opts_chrome.add_argument("--log-level=3")

        # Banderas indispensables para Linux Debian / Canaima / VIT
        if sys.platform.startswith("linux"):
            opts_chrome.add_argument("--no-sandbox")
            opts_chrome.add_argument("--disable-dev-shm-usage")
            opts_chrome.add_argument("--disable-gpu")
            opts_chrome.add_argument("--disable-software-rasterizer")
            opts_chrome.add_argument("--remote-debugging-port=9222")
            opts_chrome.set_capability("goog:loggingPrefs", {"browser": "ALL"})

        return webdriver.Chrome(options=opts_chrome)

    def _crear_firefox():
        opts_ff = FirefoxOptions()
        if headless:
            opts_ff.add_argument("--headless")
        d = webdriver.Firefox(options=opts_ff)
        try:
            d.maximize_window()
        except Exception:
            pass
        return d

    def _crear_edge():
        from selenium.webdriver.edge.options import Options as EdgeOptions
        opts_edge = EdgeOptions()
        if headless:
            opts_edge.add_argument("--headless=new")
        opts_edge.add_argument("--start-maximized")
        return webdriver.Edge(options=opts_edge)

    creadores = {
        "chrome": ("Google Chrome", _crear_chrome),
        "firefox": ("Mozilla Firefox", _crear_firefox),
        "edge": ("Microsoft Edge", _crear_edge)
    }

    if navegador_preferido and str(navegador_preferido).lower() in creadores:
        pref = str(navegador_preferido).lower()
        orden = [pref] + [b for b in ("chrome", "firefox", "edge") if b != pref]
    else:
        orden = ["chrome", "firefox", "edge"]

    driver = None
    for nom in orden:
        label, fn = creadores[nom]
        try:
            driver = fn()
            if driver is not None:
                break
        except Exception as err:
            print(f"⚠️ [DriverFactory] {label} no pudo inicializarse: {err}.")

    if driver is None:
        print("❌ [DriverFactory] Error crítico: No se pudo levantar ningún navegador.")
        return None

    # Inyección estricta de timeouts de transporte contra congelamientos por pérdida de paquetes
    try:
        driver.set_page_load_timeout(timeout_pagina)
        driver.set_script_timeout(timeout_script)
    except Exception:
        pass

    return driver
