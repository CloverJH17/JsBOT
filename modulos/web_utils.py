"""
UTILIDADES WEB Y MANIPULACIÓN DEL DOM — JsBOT
Centraliza el bypass de overlays, neutralización de spinners, inyección JS y autenticación.
"""
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def limpiar_overlays(driver) -> None:
    """Elimina del DOM el spinner #cover-spin, alertas flotantes y toasts de InfoApp."""
    try:
        driver.execute_script("""
            document.querySelectorAll('#cover-spin, .toastify, .alert, .badge, .modal-backdrop, .loading, .swal2-container').forEach(el => {
                el.style.display = 'none';
                el.remove();
            });
        """)
    except Exception:
        pass

def esperar_desbloqueo_ajax(driver, timeout: int = 12) -> None:
    """Aguarda a que el spinner #cover-spin desaparezca y fuerza la limpieza de capas residuales."""
    try:
        WebDriverWait(driver, timeout).until(
            EC.invisibility_of_element_located((By.ID, "cover-spin"))
        )
    except Exception:
        limpiar_overlays(driver)

def scroll_y_obtener(driver, wait: WebDriverWait, by: By, locator: str):
    """Realiza scroll centrado sobre el elemento y aguarda hasta que sea cliqueable."""
    esperar_desbloqueo_ajax(driver)
    limpiar_overlays(driver)
    elem = wait.until(EC.presence_of_element_located((by, locator)))
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
    esperar_desbloqueo_ajax(driver)
    limpiar_overlays(driver)
    return wait.until(EC.element_to_be_clickable((by, locator)))

def escribir_input_nativo_js(driver, elemento, valor: str) -> None:
    """Asigna valor disparando eventos 'input' y 'change' para burlar máscaras reactivas defectuosas."""
    driver.execute_script("""
        arguments[0].value = arguments[1];
        arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
    """, elemento, str(valor))

def realizar_login_infoapp(
    driver, 
    usuario: str, 
    clave: str, 
    url_login: str = "https://infoapp2.infocentro.gob.ve/admin/index.php"
) -> bool:
    """Protocolo unificado de autenticación en InfoApp con validación de URL y retorno booleano."""
    wait = WebDriverWait(driver, 15)
    driver.get(url_login)

    campo_email = wait.until(EC.visibility_of_element_located((By.NAME, "email")))
    campo_email.clear()
    campo_email.send_keys(usuario)

    campo_pass = driver.find_element(By.ID, "password")
    campo_pass.clear()
    campo_pass.send_keys(clave)

    btn_submit = driver.find_element(By.XPATH, "//input[@value='Iniciar Sesión']")
    btn_submit.click()

    wait.until(EC.url_changes(url_login))
    limpiar_overlays(driver)
    return True
