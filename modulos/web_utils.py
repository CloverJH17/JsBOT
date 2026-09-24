"""
UTILIDADES WEB Y MANIPULACIÓN DEL DOM — JsBOT
Centraliza el bypass de overlays, neutralización de spinners, inyección JS
y autenticación usando Playwright (auto-waiting nativo).
"""
from playwright.sync_api import Page


# ---------------------------------------------------------------------------
# Script JS reutilizable para limpiar overlays de InfoApp
# ---------------------------------------------------------------------------
_JS_LIMPIAR_OVERLAYS = """
    document.querySelectorAll(
        '#cover-spin, .toastify, .alert, .badge, .modal-backdrop, .loading, .swal2-container'
    ).forEach(el => {
        el.style.display = 'none';
        el.remove();
    });
"""

_JS_AJAX_LISTO = """
    () => {
        let spin = document.getElementById('cover-spin');
        let spinOculto = !spin || spin.style.display === 'none'
                          || getComputedStyle(spin).display === 'none';
        let jqListo = (typeof window.jQuery !== 'undefined')
                       ? (window.jQuery.active === 0)
                       : true;
        return spinOculto && jqListo;
    }
"""


def limpiar_overlays(page: Page) -> None:
    """Elimina del DOM el spinner #cover-spin, alertas flotantes y toasts de InfoApp."""
    try:
        page.evaluate(_JS_LIMPIAR_OVERLAYS)
    except Exception:
        pass


def esperar_desbloqueo_ajax(page: Page, timeout: int = 12) -> None:
    """
    Aguarda a que el spinner #cover-spin desaparezca y jQuery termine.
    Con Playwright, esto es sólo una comprobación extra de seguridad;
    el auto-waiting nativo ya maneja la mayoría de casos.
    timeout en segundos (se convierte a ms internamente).
    """
    try:
        page.wait_for_function(_JS_AJAX_LISTO, timeout=timeout * 1000)
    except Exception:
        pass
    limpiar_overlays(page)


def scroll_y_obtener(page: Page, locator: str):
    """
    Realiza scroll centrado sobre el elemento y lo retorna listo para interactuar.
    Con Playwright el auto-scroll es nativo, pero se fuerza para garantizar visibilidad.
    """
    esperar_desbloqueo_ajax(page)
    limpiar_overlays(page)
    elem = page.locator(locator)
    elem.scroll_into_view_if_needed()
    esperar_desbloqueo_ajax(page)
    limpiar_overlays(page)
    return elem


def escribir_input_nativo_js(page: Page, locator: str, valor: str) -> None:
    """
    Asigna valor disparando eventos 'input' y 'change' para burlar máscaras reactivas.
    Recibe el locator CSS/XPath como string.
    """
    try:
        page.evaluate(
            """([sel, val]) => {
                const el = document.querySelector(sel);
                if (!el) return;
                el.value = val;
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            }""",
            [locator, str(valor)]
        )
    except Exception:
        pass


def realizar_login_infoapp(
    page: Page,
    usuario: str,
    clave: str,
    url_login: str = "https://infoapp2.infocentro.gob.ve/admin/index.php"
) -> bool:
    """
    Protocolo unificado de autenticación en InfoApp con Playwright.
    Usa auto-waiting nativo y verificación de presencia de sesión.
    """
    try:
        # 1. Navegar primero a la raíz donde está el formulario de login de InfoApp
        page.goto(url_login, wait_until="domcontentloaded", timeout=25000)
        esperar_desbloqueo_ajax(page)

        email_input = page.locator("input[name='email'], input#email").first
        pass_input = page.locator("input[name='password'], input#password").first

        # Si los campos de login están presentes, rellenar y enviar
        if email_input.is_visible(timeout=4000) or pass_input.is_visible(timeout=4000):
            try:
                email_input.fill(usuario)
                pass_input.fill(clave)
            except Exception:
                pass

            selectores_btn = [
                "input[value='Iniciar Sesión']",
                "input[value*='Iniciar']",
                "input[type='submit']",
                "button[type='submit']",
                "button:has-text('Iniciar')",
            ]
            click_exitoso = False
            for sel in selectores_btn:
                try:
                    btn = page.locator(sel).first
                    if btn.is_visible():
                        btn.click()
                        click_exitoso = True
                        break
                except Exception:
                    continue

            if not click_exitoso:
                try:
                    page.evaluate("() => { const form = document.querySelector('form'); if(form) form.submit(); }")
                except Exception:
                    pass

            page.wait_for_timeout(2500)
            esperar_desbloqueo_ajax(page)
            limpiar_overlays(page)

        # 2. Navegar al panel de administración para confirmar sesión
        page.goto(url_login, wait_until="domcontentloaded", timeout=15000)
        esperar_desbloqueo_ajax(page)
        limpiar_overlays(page)

        # Comprobar que no hayamos sido rebotados al login
        email_rebotado = page.locator("input[name='email'], input#email").first
        login_valido = not email_rebotado.is_visible(timeout=1500)
        return login_valido
    except Exception:
        return False

