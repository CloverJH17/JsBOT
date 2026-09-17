import sys
sys.path.insert(0, '.')
import requests
import configparser
import modulos.auditor_reportes as ar

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

url_csv = 'https://infoapp2.infocentro.gob.ve/admin/pdf/csv_pdo.php'
sql = "SELECT * FROM services_users LIMIT 1"
resp = sess.get(url_csv, params={'param_csv': sql, 'param_sql': 'true', 'DB_name': 'services_users'}, timeout=20)
text = resp.content.decode('latin1', errors='replace')
lines = text.strip().splitlines()
print('Total lines in services_users:', len(lines))
if lines:
    cols = lines[0].split('|')
    print('Services Header cols (' + str(len(cols)) + '):')
    for idx, c in enumerate(cols):
        print(f'  col[{idx}] = {c}')
if len(lines) > 1:
    import csv, io
    reader = csv.reader(io.StringIO(text), delimiter="|")
    rows = list(reader)
    total_fe = 0
    total_ma = 0
    formaciones = 0
    productos = 0
    otras = 0
    for r in rows[1:]:
        if len(r) < 30:
            continue
        fe = int(r[25].strip("'\"")) if len(r) > 25 and r[25].strip("'\"").isdigit() else 0
        ma = int(r[26].strip("'\"")) if len(r) > 26 and r[26].strip("'\"").isdigit() else 0
        total_fe += fe
        total_ma += ma
        linea = r[6].strip("'\"") if len(r) > 6 else ""
        reporte = r[7].strip("'\"") if len(r) > 7 else ""
        taller = r[42].strip("'\"") if len(r) > 42 else ""
        titulo = r[16].strip("'\"") if len(r) > 16 else ""
        prod = int(r[41].strip("'\"")) if len(r) > 41 and r[41].strip("'\"").isdigit() else 0
        
        texto_comb = f"{linea} {reporte} {taller} {titulo}".lower()
        if any(k in texto_comb for k in ["aprendizaje", "robótica", "robotica", "taller", "curso", "formación", "formacion", "alfabetización"]):
            formaciones += 1
        elif prod > 0 or "contenido" in texto_comb or "medios digitales" in texto_comb:
            productos += 1
        else:
            otras += 1
            
    print(f'Total Activities: {len(rows)-1}')
    print(f'  Formaciones: {formaciones}, Productos: {productos}, Otras: {otras}')
    print(f'  Total Estudiantes: {total_fe + total_ma} (Mujeres: {total_fe}, Hombres: {total_ma})')
