import sys
sys.path.insert(0, '.')
import requests
import configparser
import modulos.auditor_reportes as ar
import modulos.motor_export_auditoria as mea

cp = configparser.ConfigParser()
cp.read('config/config.ini', encoding='utf-8')
u = cp.get('LOGIN', 'usuario', fallback='')
c = cp.get('LOGIN', 'clave', fallback='')

driver = ar.iniciar_driver_auditoria(headless=True)
sess = requests.Session()
sess.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})
ar.autenticar_infoapp(driver, u, c)
for ck in driver.get_cookies():
    sess.cookies.set(ck['name'], ck['value'], domain=ck.get('domain', ''), path=ck.get('path', '/'))
driver.quit()

res_aud = ar.ejecutar_auditoria(
    session=sess,
    estado="Yaracuy",
    fecha_inicio="2026-09-01",
    fecha_fin="2026-09-17",
    modo_turbo=True,
    exportar_formato="consola"
)

print("\n--- RESULTADO DE AUDITORIA ---")
print("Total Actividades:", res_aud.get("total_actividades"))
print("Formaciones:", len(res_aud.get("formaciones", [])))
print("Estudiantes Formados:", res_aud.get("total_estudiantes"))
print("Productos:", len(res_aud.get("productos", [])))
print("Otras Actividades:", len(res_aud.get("otras_actividades", [])))
print("Servicios:", res_aud.get("total_servicios"))
print("Cuadre:", res_aud.get("cuadre_perfecto"))
