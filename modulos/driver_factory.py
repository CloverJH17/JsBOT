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
    timeout_script: int = 20
) -> Optional[webdriver.Remote]:
    """
    Instancia y retorna un WebDriver configurado con cascada Chrome -> Firefox -> Edge.
    Inyecta blindaje crítico para entornos Linux/Canaima y timeouts de socket anti-bloqueo.
    """
    driver = None

    # 1. Intentar instanciar Google Chrome / Chromium
    try:
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

        driver = webdriver.Chrome(options=opts_chrome)
    except Exception as e_chrome:
        print(f"⚠️ [DriverFactory] Chrome no pudo inicializarse: {e_chrome}. Intentando con Firefox...")

    # 2. Cascada de fallback a Mozilla Firefox
    if driver is None:
        try:
            opts_ff = FirefoxOptions()
            if headless:
                opts_ff.add_argument("--headless")
            driver = webdriver.Firefox(options=opts_ff)
            driver.maximize_window()
        except Exception as e_ff:
            print(f"⚠️ [DriverFactory] Firefox no pudo inicializarse: {e_ff}. Intentando con Edge...")

    # 3. Cascada de fallback a Microsoft Edge (vital en entornos Windows)
    if driver is None:
        try:
            from selenium.webdriver.edge.options import Options as EdgeOptions
            opts_edge = EdgeOptions()
            if headless:
                opts_edge.add_argument("--headless=new")
            opts_edge.add_argument("--start-maximized")
            driver = webdriver.Edge(options=opts_edge)
        except Exception as e_edge:
            print(f"❌ [DriverFactory] Error crítico: No se pudo levantar ningún navegador: {e_edge}")
            return None

    # Inyección estricta de timeouts de transporte contra congelamientos por pérdida de paquetes
    try:
        driver.set_page_load_timeout(timeout_pagina)
        driver.set_script_timeout(timeout_script)
    except Exception:
        pass

    return driver
