# ⚠️ DIRECTRICES OPERATIVAS Y REGLAS ESTRICTAS PARA IAs — JsBOT
# [LECTURA OBLIGATORIA PREVIA A CUALQUIER ACCIÓN O INSTRUCCIÓN]

Todo agente, subagente o modelo de Inteligencia Artificial que opere en este repositorio DEBE leer, acatar y validar obligatoriamente estas 6 directrices antes de ejecutar cualquier comando, herramienta o edición de código:

## 1. Aprobación Obligatoria para `git push`
- NUNCA ejecutar comandos de subida remota (`git push`) sin el consentimiento y la autorización explícita del usuario.
- Todo cambio debe quedar verificado y probado localmente antes de consultar si se autoriza el push.

## 2. Aprobación Previa de Planes de Cambio (Planning Mode Estricto)
- NUNCA modificar archivos de código, configuración ni ejecutar acciones destructivas sin que el usuario haya revisado y aprobado formalmente el plan de implementación.
- Solo proceder a la edición cuando el usuario responda con un "sí", "adelante" o "procede".

## 3. Generación Obligatoria de Planes Detallados
- Ante cualquier solicitud que requiera cambios técnicos o refactorizaciones, generar siempre un plan técnico claro, modular y detallado con las acciones específicas a realizar antes de tocar cualquier archivo.

## 4. Comunicación Proactiva de Estado y Progreso
- Informar continuamente al usuario sobre el avance del trabajo mientras se está ejecutando, detallando qué parte de la tarea se está procesando (especialmente en ejecuciones largas, pruebas o análisis).

## 5. Versionado Semántico (SemVer) y Sistematización Obligatoria
- Cada cambio aprobado debe sistematizarse y actualizar la versión del proyecto siguiendo estrictamente SemVer (`MAJOR.MINOR.PATCH`):
  - `MAJOR`: Cambios que rompen compatibilidad con versiones anteriores.
  - `MINOR`: Nuevas funcionalidades, módulos o capacidades compatibles hacia atrás (ej. nuevas opciones en GUI, mejoras en ingesta ETL).
  - `PATCH`: Corrección de bugs menores y ajustes internos sin nuevas funcionalidades.
- Presentar SIEMPRE el plan de versionado al usuario para su aprobación previa.
- Al cambiar la versión, sincronizar obligatoriamente en todos los archivos del sistema:
  - `modulos/version.py` (`__version__`)
  - `config/settings.json` (`app.version`)
  - `docs/version.txt` y `docs/historial/version.txt`
  - `docs/PROJECT.md` y `README.md`

## 6. Pruebas Unitarias Obligatorias por Cada Cambio
- Al realizar cualquier modificación de código o lógica, crear o ampliar una prueba unitaria específica en `tests/test_*.py`.
- El test debe certificar el nuevo comportamiento o corrección para evitar regresiones futuras en el sistema.

---
### Principio Fundamental: Preservación de Código
- Bajo ningún concepto se debe alterar, eliminar o reescribir lógica que actualmente es funcional a menos que el usuario lo solicite explícitamente. Ante cualquier duda, formular una pregunta crítica antes de proceder.
