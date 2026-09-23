# Guía de Conexión: Telemetría de JsBOT en Google Sheets (Drive)

Esta guía explica cómo recibir en tiempo real las notificaciones de instalación, arranque y uso de **JsBOT v5.0.0** en una hoja de cálculo estética y organizada en tu Google Drive personal o institucional.

---

## 1. Crear la Hoja de Cálculo en Google Drive

1. Ve a [Google Drive](https://drive.google.com) y crea una nueva **Hoja de cálculo de Google**.
2. Nómbrala: `JsBOT - Registro de Instalaciones y Uso`.
3. Renombra la primera pestaña de la hoja (abajo a la izquierda) como: `Telemetría`.

---

## 2. Agregar el Script Automatizador (Google Apps Script)

1. En el menú superior de la hoja, haz clic en **Extensiones** > **Apps Script**.
2. Borra cualquier código que aparezca en el editor (`myFunction`).
3. Copia y pega el siguiente código completo:

```javascript
/**
 * ===============================================================================
 * RECEPTOR DE TELEMETRÍA Y CONTROL DE DESPLIEGUE — JsBOT RPA
 * ===============================================================================
 * Registra eventos en Google Sheets con formato visual automático, bordes finos,
 * alineación centrada y paleta de colores institucional según el tipo de evento.
 * ===============================================================================
 */

function doPost(e) {
  try {
    var lock = LockService.getScriptLock();
    lock.waitLock(10000); // Evitar colisiones concurrentes (10 seg)

    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName("Telemetría") || ss.getActiveSheet();

    // 1. Crear cabecera si la hoja está vacía
    if (sheet.getLastRow() === 0) {
      inicializarCabecera(sheet);
    }

    // 2. Parsear el JSON recibido
    var data = JSON.parse(e.postData.contents);

    var fechaHora = data.marca_temporal || Utilities.formatDate(new Date(), "GMT-4", "yyyy-MM-dd HH:mm:ss");
    var idMaquina = data.id_maquina || "N/A";
    var equipo = data.equipo || "Desconocido";
    var usuario = data.usuario || "Desconocido";
    var so = data.sistema_operativo || "Desconocido";
    var version = data.version_jsbot || "v5.0.0";
    var tipoEvento = (data.tipo_evento || "INICIO").toUpperCase();
    var detalle = data.detalle || "Operación estándar";

    // 3. Insertar fila
    var nextRow = sheet.getLastRow() + 1;
    sheet.appendRow([
      fechaHora,
      tipoEvento,
      version,
      equipo,
      usuario,
      so,
      idMaquina,
      detalle
    ]);

    // 4. Aplicar estilos estéticos a la fila recién agregada
    var filaRango = sheet.getRange(nextRow, 1, 1, 8);
    filaRango.setFontFamily("Roboto")
             .setFontSize(10)
             .setVerticalAlignment("middle")
             .setBorder(true, true, true, true, true, true, "#D0D7DE", SpreadsheetApp.BorderStyle.SOLID);

    // Centrar columnas clave
    sheet.getRange(nextRow, 1).setHorizontalAlignment("center"); // Fecha
    sheet.getRange(nextRow, 2).setHorizontalAlignment("center"); // Evento
    sheet.getRange(nextRow, 3).setHorizontalAlignment("center"); // Versión
    sheet.getRange(nextRow, 4).setHorizontalAlignment("center"); // Equipo
    sheet.getRange(nextRow, 5).setHorizontalAlignment("center"); // Usuario

    // Colorear celda de Evento según el tipo
    var celdaEvento = sheet.getRange(nextRow, 2);
    if (tipoEvento === "INSTALACION") {
      celdaEvento.setBackground("#D1E7DD").setFontColor("#0F5132").setFontWeight("bold"); // Verde suave
    } else if (tipoEvento === "INICIO") {
      celdaEvento.setBackground("#CFE2FF").setFontColor("#084298"); // Azul suave
    } else if (tipoEvento === "DESINSTALACION") {
      celdaEvento.setBackground("#F8D7DA").setFontColor("#842029").setFontWeight("bold"); // Rojo suave
    } else {
      celdaEvento.setBackground("#FFF3CD").setFontColor("#664D03"); // Amarillo
    }

    lock.releaseLock();
    return ContentService.createTextOutput(JSON.stringify({ status: "success" }))
                         .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ status: "error", message: err.toString() }))
                         .setMimeType(ContentService.MimeType.JSON);
  }
}

function inicializarCabecera(sheet) {
  var headers = [
    "Fecha y Hora",
    "Tipo de Evento",
    "Versión",
    "Equipo",
    "Usuario",
    "Sistema Operativo",
    "ID Máquina (Hash)",
    "Detalle de Operación"
  ];

  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  
  var cabecera = sheet.getRange(1, 1, 1, headers.length);
  cabecera.setFontFamily("Roboto")
          .setFontSize(11)
          .setFontWeight("bold")
          .setBackground("#1F2937") // Gris grafito elegante
          .setFontColor("#FFFFFF")
          .setHorizontalAlignment("center")
          .setVerticalAlignment("middle");

  sheet.setRowHeight(1, 35);
  sheet.setFrozenRows(1);

  // Anchos de columna ideales
  sheet.setColumnWidth(1, 160); // Fecha
  sheet.setColumnWidth(2, 130); // Evento
  sheet.setColumnWidth(3, 90);  // Versión
  sheet.setColumnWidth(4, 150); // Equipo
  sheet.setColumnWidth(5, 120); // Usuario
  sheet.setColumnWidth(6, 220); // SO
  sheet.setColumnWidth(7, 160); // ID Máquina
  sheet.setColumnWidth(8, 250); // Detalle
}
```

---

## 3. Publicar la Web App (Obtener tu Enlace Webhook)

1. En la esquina superior derecha del editor de Apps Script, haz clic en el botón azul **Implementar** (Deploy) > **Nueva implementación**.
2. En el engranaje ⚙️ (*Seleccionar tipo*), elige **Aplicación web**.
3. Configura:
   * **Descripción:** `Receptor Telemetría JsBOT`
   * **Ejecutar como:** `Yo` (*tu cuenta de Google*)
   * **Quién tiene acceso:** `Cualquier persona` (Anyone) *(esto es esencial para que el bot pueda enviar los datos sin requerir inicio de sesión de Google)*.
4. Haz clic en **Implementar**.
5. Concede los permisos que Google solicite.
6. Copia la **URL de la aplicación web** generada. Tendrá un formato similar a:
   `https://script.google.com/macros/s/AKfycb.../exec`

---

## 4. Configurar el Enlace en JsBOT

En tu archivo `config/settings.json`, pega tu URL en `"google_sheets_url"`:

```json
"telemetria": {
    "activa": true,
    "google_sheets_url": "https://script.google.com/macros/s/AKfycb.../exec"
}
```

¡Listo! A partir de ese momento, cada vez que alguien instale o use JsBOT, tu hoja de Google Drive se actualizará automáticamente con un registro limpio, ordenado y formateado con colores.
