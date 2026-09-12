# REGLAS ESTRICTAS PARA IAs Y AGENTES DE DESARROLLO - JsBOT

Todo agente, IA o desarrollador que modifique este repositorio DEBE acatar obligatoriamente estas reglas antes de ejecutar cualquier comando o edición de código:

## 1. PRINCIPIO DE PRESERVACIÓN DE CÓDIGO (NO ROMPER LO QUE FUNCIONA)
- **Regla:** Bajo ningún concepto se debe editar, eliminar o alterar código que actualmente es funcional, a menos que el usuario lo exija explícitamente.
- **Acción:** Si una nueva función (feature) requiere tocar una función existente que ya funciona, se debe realizar una **Pregunta Crítica** al usuario para confirmar si la modificación de ese código validado está autorizada.

## 2. ESTILO VISUAL ESTRICTO (NORMALIZACIÓN DE INTERFAZ)
- **Regla:** Todos los menús de terminal, banners y elementos visuales deben mantener la uniformidad y el diseño preestablecido.
- **Formato del Banner:**
  ```text
  ╔══════════════════════════════════════════════════════════════════════════╗
  ║   JsBOT v3.5.2 — GESTIÓN MASIVA DE ACTIVIDADES Y SERVICIOS INFOCENTRO    ║
  ╚══════════════════════════════════════════════════════════════════════════╝
  ```
- **Formato InquirerPy:** El InquirerPy debe usar `qmark=""` para evitar mostrar `? ¿Qué acción...` y en su lugar mostrar un estilo limpio:
  ```text
  ¿Qué acción deseas realizar? (Usa flechas o presiona número)
  ❯  [1] Formación (Carga de Estudiantes y Planillas ODS)
  ```
- Ninguna IA tiene permiso de rediseñar o cambiar este estilo.

## 3. APROBACIÓN PREVIA OBLIGATORIA (PLANNING MODE)
- **Regla:** SIEMPRE se debe mostrar al usuario el código o explicarle claramente las funciones nuevas que se pretenden inyectar.
- **Acción:** Pedir permiso explícito antes de reemplazar código complejo. Solo proceder cuando el usuario diga "sí" o "procede".

## 4. CONTROL DE VERSIONES LOCAL (version.txt)
- **Regla:** Siempre que un cambio significativo sea implementado, probado y validado (aprobado por el usuario con un "sí funciona" o "todo bien"), se DEBE actualizar obligatoriamente el archivo `version.txt`.
- **Formato:** Se debe mantener el formato actual del archivo `version.txt` (usualmente detallando la versión, la fecha, y los *changelogs* o cambios realizados en esa iteración).
