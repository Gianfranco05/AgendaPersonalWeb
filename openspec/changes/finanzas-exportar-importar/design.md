## Context

- **Finanzas hoy**: `backend/app/api/v1/finance.py` expone transacciones (`GET /finance/transactions` con filtros `date_from`, `date_to`, `transaction_type`, `category_id`), categorías, presupuestos, reportes (`/finance/reports`: gasto por categoría + 6 meses) y cuentas (`bank_accounts`). La lógica está en `backend/app/modules/finanzas/` (service + repository). `transactions.transaction_date`/`transaction_time` son texto ISO (`IsoText`, `String(10)`), `amount` es `Numeric(12,2)` siempre positivo con `type` `income|expense`, `currency` `String(3)` (default ARS) y el borrado es lógico (`is_deleted`, `deleted_at`). **Una transacción no tiene FK a `bank_accounts`**: la cuenta se describe con `bank_entity_name`, `account_type` y `account_last4`. El tope de montos es `Money` (±9.999.999.999,99) en `finanzas/schemas.py`.
- **Inversiones** (change `finanzas-inversiones`, ya implementado en backend y web): `InvestmentService.summary(user_id, today, rates)` y `net_worth(user_id, today)` en `backend/app/modules/inversiones/service.py`, con cotización manual del usuario en `user_preferences`.
- **Export existente**: `GET /api/v1/me/export` (JSON de todas las tablas, `backend/app/modules/cuenta/service.py`). `OWNED_TABLES` es el inventario para export/borrado; `test_account.py` falla si una tabla con `user_id` no está. `REDACTED_COLUMNS` omite columnas.
- **Límites HTTP**: `BodySizeLimitMiddleware` corta por `Content-Length` > `MAX_REQUEST_BODY_SIZE` (1 MiB) en `backend/app/core/http_security.py`; nginx `client_max_body_size 10M`. Limitadores en memoria/Redis con `_build_rate_limiter`. `python-multipart` ya está instalado (subida de archivos con `UploadFile`).
- **Imagen**: `python:3.11-slim` multi-stage (`backend/Dockerfile`), desplegada en ARM; las dependencias se fijan con `==` en `backend/requirements.txt`.
- **Guardas**: `test_infra.py::test_no_api_route_is_public_by_accident`, `test_tenant_isolation.py`, `test_account.py`.
- **Clientes**: web `frontend/` (React 19, SWR, RHF + Zod sin `z.coerce`, `apiClient` axios con `responseType: 'blob'` ya usado en `exportNotesJson`, modo mock, `src/utils/date.ts`); mobile `C:\Proyectos\vida-personal-mobile` (Expo SDK 57; `expo-file-system ~57.0.6` y `expo-sharing ~57.0.24` ya instalados y usados en `src/lib/exportFile.ts` con la API nueva `File`/`Paths`; **no** tiene `expo-document-picker`).
- **Formatos de origen verificados** (octubre 2026):
  - Mercado Pago documenta dos reportes descargables desde el panel ("Informes y facturación" → `mercadopago.com.ar/movements` → "Ir a reportes de pagos y extractos de cuenta") en **.csv o .xlsx**:
    - *Dinero disponible* (released money): columnas `DATE` (`yyyy-MM-dd'T'HH:mm:ssZ`), `SOURCE_ID`, `EXTERNAL_REFERENCE`, `RECORD_TYPE` (`initial_available_balance`, `release`, `total`, `available_balance`), `DESCRIPTION` (`payment`, `refund`, `payout`, `chargeback`, `tax_*`, `shipping`, `asset_management_gain`…), `NET_CREDIT_AMOUNT`, `NET_DEBIT_AMOUNT`, `GROSS_AMOUNT`, `BALANCE_AMOUNT`, `CURRENCY`; montos `(17,2)`.
    - *Dinero en cuenta* (account money): `TRANSACTION_DATE`, `SOURCE_ID`, `DESCRIPTION`, `TRANSACTION_TYPE` (`SETTLEMENT`, `REFUND`, `CHARGEBACK`, `DISPUTE`, `WITHDRAWAL`, `WITHDRAWAL_CANCEL`, `PAYOUT`), `TRANSACTION_AMOUNT`, `SETTLEMENT_NET_AMOUNT` (impacto real en el saldo), `TRANSACTION_CURRENCY`/`SETTLEMENT_CURRENCY`.
    - Configuración del reporte: `separator` (reemplaza la coma, ej. `;`), `report_translation` (`en`/`es`/`pt`: **traduce los encabezados**), `display_timezone` (default **GMT-04**).
  - **Galicia, Santander, Brubank, Ualá**: no se encontró documentación pública del formato de exportación de movimientos (solo menciones de terceros que dicen tener plantillas propias para Galicia/Santander, sin columnas). Brubank y Ualá ofrecen resúmenes en la app (PDF). Por eso el importador es genérico con mapeo de columnas (D7).

## Goals / Non-Goals

**Goals:**
- Export de Finanzas a .xlsx y PDF con rango, filtros y secciones (movimientos, totales por categoría y mes, balance, inversiones opcional), formato es-AR y marca Can_cen; descarga en web, archivo + compartir en mobile.
- Import de CSV/XLSX en dos pasos con presets verificados de Mercado Pago, mapeo genérico que se recuerda, parseo robusto de fechas/números es-AR, categorías sugeridas, detección de duplicados y lotes deshacibles.
- Seguridad: archivos acotados y validados por contenido, sin evaluar fórmulas, sin XML/zip bombs, escape de inyección de fórmulas en el export, aislamiento por usuario, límites de frecuencia.
- Compatibilidad Postgres/SQLite y export/borrado de cuenta.

**Non-Goals:**
- PDFs de resúmenes, OCR, `.xls`/`.ods`/OFX, open banking (ver proposal).
- Conversión de monedas en el export o en el import.
- Edición masiva de movimientos ya existentes desde el import (el import solo crea).
- Detección de transferencias entre cuentas propias (un débito en el banco y el crédito en Mercado Pago se importan como dos movimientos).

## Decisions

### D1. Ubicación: subpaquete `finanzas/transfer/` y router `finance_transfer.py`

`backend/app/modules/finanzas/transfer/` con `models.py` (`ImportBatch`), `schemas.py`, `report_data.py` (consulta y agregación compartida por los dos exportadores), `export_xlsx.py`, `export_pdf.py`, `cells.py` (escape de fórmulas y formato es-AR), `import_parse.py` (decodificación, detección de encabezado, fechas, números), `import_presets.py`, `import_rules.py` (categorías sugeridas), `import_service.py` (preview/confirm/undo). Router nuevo `backend/app/api/v1/finance_transfer.py` (`prefix="/finance"`, `tags=["finance"]`) incluido en `router.py`. Finanzas es plantilla base: sin `require_module`; todas las rutas con `get_current_user`.

*Alternativa*: sumar todo a `api/v1/finance.py`. Descartada: ya tiene 340 líneas y la lógica de archivos es autocontenida.

### D2. Librerías: openpyxl + defusedxml para Excel, reportlab para PDF

| Opción | Peso / dependencias | Veredicto |
|---|---|---|
| `openpyxl==3.1.5` (+ `et-xmlfile`) | wheel puro de 251 KB | **Elegida** para leer y escribir .xlsx (una sola librería). Escritura con `Workbook(write_only=True)`; lectura con `load_workbook(read_only=True, data_only=True)`. |
| `defusedxml==0.7.1` | puro | **Elegida**: openpyxl la usa automáticamente si está instalada y bloquea entidades XML (billion laughs / XXE). |
| `xlsxwriter` | puro, solo escribe | Descartada: obliga a tener dos librerías (no lee). |
| `pandas` | ~60 MB + numpy | Descartada por peso. |
| `reportlab==4.5.1` (+ `pillow`, `charset-normalizer`) | wheel `py3-none-any` ~2 MB; Pillow tiene wheel `cp311 manylinux aarch64` (~6 MB) | **Elegida**: Platypus da tablas con `repeatRows`, saltos de página y "Página X de Y" sin paquetes del sistema. Se fija la 4.5.x (mayo 2026) y no la 5.1.0 publicada el 22/10/2026 (demasiado nueva). |
| `fpdf2==2.8.9` (+ Pillow, fonttools, defusedxml) | similar | Alternativa válida; reportlab tiene mejor manejo de tablas largas. |
| WeasyPrint | requiere Pango, Cairo, HarfBuzz, fontconfig vía `apt` (decenas de MB) | Descartada: engorda la imagen ARM y suma superficie de CVEs del sistema. |

Las versiones exactas se confirman al implementar (`pip index versions`), se fijan con `==` y se corre la suite completa; se construye la imagen ARM (`docker buildx --platform linux/arm64`) para comprobar que no compila nada desde fuente.

**Fuente del PDF**: Helvetica estándar de reportlab (WinAnsi, cubre español completo). Los textos del usuario se sanean con `cells.pdf_safe()`: los caracteres fuera de cp1252 (emojis en nombres de categorías, por ejemplo) se quitan. *Alternativa*: embeber DejaVu Sans (~750 KB en el repo). Descartada por ahora: el beneficio es solo mostrar emojis.

### D3. Datos del reporte (`report_data.py`)

`build_report(db, user_id, filters, tz_offset_minutes) -> ReportData` con una sola consulta de movimientos (`user_id`, `is_deleted = false`, filtros, orden `transaction_date, transaction_time, created_at`) con `LEFT JOIN categories` para el nombre, y agregados calculados en Python sobre esas filas (mismas filas que la hoja de movimientos: los totales siempre cuadran con el detalle):

- `filters`: `date_from`, `date_to` (default: primer día del mes local → hoy local; `date_to >= date_from`; rango máximo 5 años), `type` (`income|expense`), `category_id` (`"none"` = sin categoría), `account_id`, `include_investments` (bool).
- **Filtro por cuenta**: como `transactions` no tiene FK a la cuenta, `account_id` se resuelve a la cuenta del usuario (404 si no es suya) y filtra por `account_type = cuenta.account_type AND account_last4 = cuenta.last4` y, si la cuenta tiene `bank_name`, `bank_entity_name = cuenta.bank_name`. Es el mismo criterio con el que el import completa esos campos (D9), así lo importado a una cuenta se puede exportar por esa cuenta. Se documenta en la UI ("según banco, tipo y últimos 4 dígitos").
- `totals_by_currency[]`: `{currency, income, expense, balance, count}` — **nunca se suman monedas distintas**.
- `by_category[]`: `{category, currency, income, expense, count}` ordenado por egreso desc; "Sin categoría" al final.
- `by_month[]`: `{month (AAAA-MM), currency, income, expense, balance}`.
- `investments` (solo si `include_investments`): `InvestmentService.summary` + `net_worth` al "hoy" local; filas de activos activos (tipo, nombre, moneda, invertido, valor efectivo, ganancia, vencimiento). Respeta la cotización vigente del usuario (manual o la que defina `finanzas-datos-mercado`).
- **Topes**: se cuenta primero (`COUNT`); si supera `FINANCE_EXPORT_MAX_ROWS_XLSX = 20000` o `FINANCE_EXPORT_MAX_ROWS_PDF = 5000` responde **422** "El reporte tiene N movimientos; el máximo para {formato} es M. Achicá el rango de fechas." sin generar nada.
- Montos como `Decimal` (SQLite devuelve `float`: `Decimal(str(x))`, mismo cuidado que `cuenta/service.py`).

### D4. Excel (`export_xlsx.py`)

`Workbook(write_only=True)` (memoria acotada) con hojas en este orden:
1. **Resumen**: título "Can_cen — Reporte de Finanzas", período "01/10/2026 al 25/10/2026", filtros aplicados en texto, "Generado el 25/10/2026 14:32 (hora local)", tabla de totales por moneda (Ingresos, Egresos, Balance, Movimientos).
2. **Movimientos**: Fecha · Hora · Tipo (Ingreso/Egreso) · Descripción · Comercio · Categoría · Medio de pago (etiqueta en español) · Cuenta · Moneda · Monto (negativo para egresos) · Notas · Importado (nombre del lote o vacío).
3. **Por categoría**: Categoría · Moneda · Ingresos · Egresos · Movimientos.
4. **Por mes**: Mes · Moneda · Ingresos · Egresos · Balance.
5. **Inversiones** (opcional): activos + bloque Patrimonio (Disponible / Inversiones / Total en ARS y USD, o "Sin cotización" si falta).

Formato: encabezado en negrita con relleno gris, `freeze_panes="A2"`, `auto_filter` en tablas, anchos de columna fijos por tipo, montos como **números** con `number_format '#,##0.00'` (Excel lo muestra con el separador del sistema del usuario: en una PC es-AR se ve "1.234,56"), fechas como `date` con `'DD/MM/YYYY'`, egresos en rojo con formato `'#,##0.00;[Red]-#,##0.00'`. Propiedades del libro: `creator = "Can_cen"`, `title`. Nombre de archivo: `cancen-finanzas-2026-10-01_2026-10-25.xlsx`.

**Inyección de fórmulas**: toda celda de **texto** pasa por `cells.safe_text()`: si empieza con `=`, `+`, `-`, `@`, `\t`, `\r` o `\n` se antepone `'` y la celda se fuerza a tipo string (`WriteOnlyCell` con `data_type = "s"`). Importante: openpyxl interpreta como **fórmula** cualquier `str` que empiece con `=` si no se fuerza el tipo. Los números se escriben como números (un monto negativo no se escapa porque no es texto). Recomendación OWASP; se aplica también a nombres de categoría, comercio, notas y nombre de lote.

### D5. PDF (`export_pdf.py`)

reportlab Platypus, A4 vertical, márgenes 15 mm:
- **Encabezado de cada página**: logotipo tipográfico "C_C" en un recuadro + "Can_cen" (con guion bajo, como la marca) + "Reporte de Finanzas" + período; **pie**: "Generado el dd/mm/aaaa hh:mm · Página X de Y" (canvas en dos pasadas para el total de páginas).
- Secciones: Resumen (totales por moneda en tarjetas), Por mes, Por categoría (top 15 + "Otras"), Movimientos (tabla con `repeatRows=1`, filas cebra, montos alineados a la derecha, ingresos en verde y egresos en rojo, descripción truncada a 60 caracteres), Inversiones/Patrimonio si se pidió.
- Formato es-AR propio (`cells.format_money_ar(Decimal, currency)` → "$ 1.234,56", "US$ 1.234,56", "€ 1.234,56"; `format_date_ar` → "25/10/2026"); **no** se usa `locale` (la imagen slim no tiene locales instalados y `setlocale` es global al proceso).
- Nombre: `cancen-finanzas-2026-10-01_2026-10-25.pdf`.

### D6. Generación, streaming y límites del export

- `GET /api/v1/finance/export?format=xlsx|pdf&date_from&date_to&type&category_id&account_id&include_investments&tz_offset_minutes`.
- La consulta es async; la construcción del archivo (CPU) corre en `starlette.concurrency.run_in_threadpool` sobre un `SpooledTemporaryFile(max_size=8 MiB)` para no bloquear el event loop ni a los demás requests del worker. Un .xlsx (zip) y un PDF no se pueden emitir antes de terminarlos, así que "streaming" = se genera completo en el archivo temporal y se devuelve con `StreamingResponse` por chunks de 64 KiB, `Content-Length`, `Content-Disposition: attachment; filename="…"`, `Cache-Control: no-store` y el `media_type` correcto (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` / `application/pdf`). Tamaño esperado: ~1,5 MB para 20.000 filas en xlsx, ~2 MB para 5.000 en PDF.
- Límite de frecuencia: `export_rate_limiter = _build_rate_limiter(10, 300)` por `user_id` (dependencia `rate_limit_finance_export`), 429 con `Retry-After`.
- Timeout de cortesía: si la generación pasa 30 s se loguea un warning (los topes de filas lo hacen improbable).

*Alternativa*: generar en el cliente (SheetJS/jsPDF). Descartada: duplicaría la lógica en web y mobile, y el móvil no tiene un buen generador de PDF sin dependencias nativas.

### D7. Importador: presets + mapeo genérico recordado

**Mapeo** (`ImportMapping`): `date` (columna), `time?`, `description` (una o varias columnas que se concatenan con " · "), `amount_mode` (`signed` | `debit_credit` | `amount_and_type`), `amount?` / `debit?` / `credit?` / `type_column?` + `type_values {income: [...], expense: [...]}`, `currency?` (columna) o `default_currency`, `reference?` (id de operación del origen), `skip_when?` (columna + valores a descartar), `date_format` (`auto` | `dd/mm/yyyy` | `mm/dd/yyyy` | `yyyy-mm-dd` | `iso_datetime`), `decimal_separator` (`auto` | `,` | `.`), `invert_sign` (bool, para archivos de tarjeta donde el consumo viene positivo).

**Presets** (`import_presets.py`), cada uno con `key`, `label`, alias de encabezado en en/es/pt y reglas fijas:
- `mercadopago_release` — "Mercado Pago · Dinero disponible": fecha `DATE` (o `DATE_SHORT`), `debit_credit` con `NET_DEBIT_AMOUNT`/`NET_CREDIT_AMOUNT`, moneda `CURRENCY`, referencia `SOURCE_ID`, descripción `DESCRIPTION` traducida (`payment`→"Cobro", `refund`→"Devolución", `payout`→"Retiro", `chargeback`→"Contracargo", `shipping`→"Envío", `tax_*`→"Impuesto / retención", `asset_management_gain`→"Rendimiento", desconocido → el código tal cual) + `EXTERNAL_REFERENCE` si existe; **solo filas `RECORD_TYPE = release`** (las de saldo inicial, total y saldo pre/pos retiro se descartan como "fila informativa").
- `mercadopago_account_money` — "Mercado Pago · Dinero en cuenta": fecha `TRANSACTION_DATE`, `signed` con `SETTLEMENT_NET_AMOUNT` (si falta, `TRANSACTION_AMOUNT` con signo por `TRANSACTION_TYPE`: `WITHDRAWAL`, `PAYOUT`, `REFUND`, `CHARGEBACK`, `DISPUTE` → egreso; `SETTLEMENT`, `WITHDRAWAL_CANCEL` → ingreso), moneda `SETTLEMENT_CURRENCY`, referencia `SOURCE_ID`.
- `generic` — sin reglas fijas: se propone un mapeo por **heurística de encabezados** en español (`fecha`, `fecha operación`, `fecha valor` → fecha; `descripción`, `concepto`, `detalle`, `movimiento`, `referencia` → descripción; `importe`, `monto`, `valor` → signed; `débito`/`debe`/`egreso` y `crédito`/`haber`/`ingreso` → débito/crédito; `moneda`/`divisa`; `saldo` se ignora; `comprobante`/`nro. operación` → referencia). Se normaliza sin tildes ni mayúsculas.
- Los alias en español/portugués de los encabezados de Mercado Pago se completan **con un archivo real** al implementar (la documentación da los identificadores en inglés y confirma que existe la traducción, pero no lista los textos traducidos). Mientras tanto el preset matchea por identificador inglés y por alias razonables; si no matchea, el usuario cae al genérico con el mapeo editable.

**Detección**: se elige el preset con más columnas requeridas presentes (umbral: todas las requeridas); si ninguno, `generic`. El usuario puede forzar otro preset o editar el mapeo en la previsualización.

**Mapeo recordado**: cada lote guarda `header_signature = sha256("|".join(encabezados normalizados))` y el `mapping` confirmado. En un preview nuevo, si hay un lote **confirmado** del mismo usuario con la misma firma, se usa su mapeo (con aviso "Usamos el mapeo de tu importación del 12/10"). No hace falta tabla de plantillas aparte. Así un usuario de Galicia mapea una vez y los siguientes archivos salen solos.

*Alternativa*: presets "adivinados" para Galicia/Santander/Brubank/Ualá. Descartada: sin un archivo real los encabezados serían inventados y fallarían en silencio; el genérico con heurística + memoria cubre el caso sin prometer lo que no está verificado.

### D8. Parseo (`import_parse.py`)

1. **Recepción**: `UploadFile` leído por chunks hasta `FINANCE_IMPORT_MAX_BYTES = 2 MiB` + 1; si se pasa, **413** (no se confía solo en `Content-Length`). `BodySizeLimitMiddleware` admite un tope por ruta: para `POST /api/v1/finance/imports/preview` usa `FINANCE_IMPORT_MAX_BYTES + 64 KiB` (overhead multipart) en vez del global de 1 MiB; el resto de rutas no cambia.
2. **Tipo por contenido**, no por extensión ni `Content-Type`: empieza con `PK\x03\x04` → xlsx; si no, se intenta texto. Cualquier otro binario (bytes `\x00` en los primeros 4 KiB, firmas de PDF/XLS OLE `D0 CF 11 E0`) → 415 "Formato no soportado: subí un .csv o .xlsx" (y para OLE: "Es un .xls viejo: abrilo en Excel y guardalo como .xlsx o .csv").
3. **XLSX seguro**: antes de openpyxl se inspecciona el zip con `zipfile`: ≤ 200 entradas, suma de `file_size` descomprimido ≤ 25 MiB y ratio ≤ 100 por entrada (zip bomb), sin rutas absolutas ni `..`; se rechazan libros con macros (`vbaProject.bin`). `load_workbook(read_only=True, data_only=True)` con defusedxml: **nunca se evalúan fórmulas**; una celda con fórmula entrega su valor cacheado y, si no lo tiene (archivo generado por un programa que no calcula), `None` → error de fila "celda con fórmula sin valor". Se lee la **primera hoja visible**; las celdas `datetime` se toman como fecha local tal cual y los números como `Decimal(str(v))`.
4. **CSV**: decodificación `utf-8-sig` y, si falla, `cp1252` (exports de bancos en Windows); separador detectado con `csv.Sniffer` sobre los primeros 8 KiB restringido a `, ; \t |` (Mercado Pago permite `;`); comillas estándar. Se quita `NUL` y se normalizan finales de línea.
5. **Límites**: ≤ 5.000 filas de datos, ≤ 50 columnas, celdas truncadas a 500 caracteres; si se pasa de filas, 422 "El archivo tiene más de 5.000 movimientos: dividilo por fechas".
6. **Encabezado**: se busca en las primeras 30 filas la que más celdas reconoce como encabezado (presets + heurística) — los home banking suelen poner datos de la cuenta arriba. El usuario puede cambiar la fila de encabezado en el preview.
7. **Fechas**: `auto` muestrea la columna: ISO con hora y zona (`2026-10-03T14:05:10-04:00`) → se convierte al huso del usuario (`tz_offset_minutes` del request) para que la fecha y la hora queden locales (Mercado Pago usa GMT-04 por defecto, Argentina es UTC-3); `yyyy-mm-dd`; `dd/mm/yyyy`, `dd-mm-yyyy`, `dd/mm/yy` (→ 20yy), `dd.mm.yyyy`; seriales de Excel (número 20000–80000 en una columna de fecha). Ambigüedad día/mes: **por defecto dd/mm** (es-AR); se pasa a mm/dd solo si alguna fila tiene "mes" > 12 en la primera posición y ninguna en la segunda. Rango válido 2000-01-01 .. hoy + 1 año.
8. **Números** (`parse_amount_ar`): se quitan espacios, `$`, `ARS`, `U$S`, `US$`, `USD`, `€`; paréntesis o `-` adelante o atrás = negativo; separadores: si hay `.` y `,`, el último es el decimal; si solo `,` → decimal; si solo `.` con exactamente 3 dígitos detrás y la columna tiene otros valores con el mismo patrón y ninguno con 1–2 decimales → miles; si no, decimal. Con `decimal_separator` explícito no se adivina. Resultado `Decimal` cuantizado a 2; tope `Money`; `0` → fila descartada ("monto cero").
9. **Signo y tipo**: `signed` → negativo = egreso; `debit_credit` → débito = egreso, crédito = ingreso (si vienen las dos con valor, error de fila); `amount_and_type` → según `type_values`. `invert_sign` invierte. El monto se guarda siempre positivo con su `type`, como hoy.
10. **Moneda**: columna (normalizando `$`→ARS, `U$S`/`US$`/`u$s`/`DOLARES`→USD, `€`/`EUR`) o `default_currency` (la de la cuenta destino o ARS). Permitidas: `ARS`, `USD`, `EUR`, `BRL`, `UYU`, `CLP`; otra → error de fila.
11. **Descripción**: trim, espacios colapsados, sin caracteres de control; `product_name` ≤ 255 (el resto va a `notes`). Vacía → "Movimiento importado". El texto se guarda tal cual (el escape contra fórmulas se hace al exportar, D4).

Cada fila del preview queda como `ParsedRow {index, source_line, date, time, description, amount, type, currency, reference, status, errors[], row_hash, duplicate_of?, suggested_category_id?, suggestion_source}`.

### D9. Categoría sugerida y datos de cuenta (`import_rules.py`)

Orden (se queda con la primera que dé resultado):
1. **Historial exacto**: entre los movimientos del usuario de los últimos 24 meses con categoría, la categoría más usada para la misma descripción normalizada (minúsculas, sin tildes, sin dígitos ni signos, espacios colapsados) y el mismo `type`. `suggestion_source = "history"`.
2. **Historial por palabra clave**: primera palabra "significativa" (≥ 4 letras, fuera de una lista de palabras vacías como `pago`, `compra`, `transferencia`, `debito`, `credito`, `mercadopago`) → categoría más usada en movimientos cuya descripción la contenga. `"history"`.
3. **Reglas por palabra clave** → `merchant_category` del enum existente: `grocery` (coto, carrefour, dia, jumbo, disco, vea, changomas, supermercado, verduleria), `transportation` (uber, cabify, didi, sube, ypf, shell, axion, peaje, estacionamiento), `utilities` (edenor, edesur, metrogas, naturgy, aysa, personal, movistar, claro, telecentro, fibertel, flow), `entertainment` (netflix, spotify, disney, hbo, max, prime video, steam, cine), `dining` (rappi, pedidosya, mcdonald, burger, cafe, resto), `healthcare` (farmacia, farmacity, osde, swiss medical, galeno), `education` (utn, universidad, curso, udemy), `shopping` (mercadolibre, mercado libre, falabella, garbarino), `services` (afip, arca, rentas, municipalidad, seguro). Se guarda como `merchant_category` del movimiento y, para `category_id`, se busca una categoría del usuario cuyo nombre normalizado coincida con sinónimos de ese rubro (`grocery` → supermercado, comida, alimentos, almacen; `transportation` → transporte, auto, nafta, viajes; etc.). `"rule"`. Sin coincidencia → `category_id = null`, `"none"`.
- La consulta de historial es una sola por preview (descripción normalizada + categoría + conteo, agrupada en Python) acotada por `user_id` y fecha.
- **Cuenta destino** (opcional, `account_id` en el preview): completa `bank_entity_name = cuenta.bank_name or cuenta.name`, `account_type = cuenta.account_type`, `account_last4 = cuenta.last4` y la moneda por defecto. Sin cuenta: `bank_entity_name` = etiqueta del preset ("Mercado Pago") o vacío, `account_type = "checking"`. `payment_method = "transfer"` en presets de Mercado Pago, `"other"` en genérico (valores válidos del enum). No se toca `bank_accounts.balance` (igual que crear un movimiento a mano hoy).

### D10. Duplicados

- **Huella de fila** `row_hash = sha256(f"{date}|{type}|{amount:.2f}|{currency}|{desc_norm}|{reference}|#{n}")` donde `n` es el número de ocurrencia de esa misma tupla **dentro del archivo** (dos cafés iguales el mismo día son dos filas legítimas: `#1` y `#2`). Re-subir el mismo archivo, o uno que se superpone en fechas, produce las mismas huellas.
- **Ya importado**: existe un movimiento del usuario, no borrado, con ese `import_row_hash` → `status = "duplicate"`, desmarcada por defecto.
- **Posible duplicado**: hay un movimiento del usuario (importado o cargado a mano, no borrado) con la misma fecha (±1 día), mismo `type`, mismo monto y moneda, y descripción parecida (una contiene a la otra o similitud de tokens Jaccard ≥ 0,5) → `status = "possible_duplicate"` con `duplicate_of` (id, fecha, descripción), **desmarcada por defecto** pero el usuario la puede incluir. Una consulta por preview: movimientos del usuario en `[min_fecha − 1, max_fecha + 1]`.
- **Mismo archivo**: `file_sha256` igual a un lote confirmado y no deshecho → aviso en el preview "Ya importaste este archivo el 12/10/2026" (no bloquea: las huellas ya lo protegen).

### D11. Modelo de datos

Tabla nueva `import_batches`:

| Columna | Tipo | Null | Notas |
|---|---|---|---|
| `id` | `String(36)` PK | no | uuid4 |
| `user_id` | `String(36)` FK `users.id` | no | index |
| `status` | `String(12)` | no | `preview` / `confirmed` / `undone`; check |
| `preset` | `String(40)` | no | `mercadopago_release`, `mercadopago_account_money`, `generic` |
| `filename` | `String(255)` | no | solo el nombre base, sin rutas, saneado |
| `file_sha256` | `String(64)` | no | |
| `header_signature` | `String(64)` | no | D7 |
| `header_row` | `Integer` | no | índice de la fila de encabezado |
| `mapping` | `JSON` | no | `ImportMapping` |
| `account_id` | `String(36)` FK `bank_accounts.id` `ondelete="SET NULL"` | sí | cuenta destino |
| `raw_table` | `JSON` | sí | celdas decodificadas (lista de listas de texto) mientras está en `preview`; se borra (`NULL`) al confirmar o descartar. Tope 4 MiB serializado (si se pasa, 413) |
| `row_count`, `imported_count`, `skipped_count`, `duplicate_count`, `error_count` | `Integer` | no | default 0 |
| `expires_at` | `DateTime(tz)` | sí | `now + 24 h` en `preview` |
| `created_at`, `confirmed_at`, `undone_at` | `DateTime(tz)` | sí/no | |

Índices: `ix_import_batches_user_created (user_id, created_at)`, `ix_import_batches_user_signature (user_id, header_signature)`.

En `transactions`: `import_batch_id String(36) NULL FK import_batches.id ondelete SET NULL` e `import_row_hash String(64) NULL`, con índice `ix_transactions_user_import_hash (user_id, import_row_hash)`. `TransactionResponse` suma `import_batch_id` (aditivo, opcional).

- `JSON` de SQLAlchemy funciona en SQLite y Postgres (en Postgres es `json`; no hace falta `jsonb` porque no se consulta por dentro).
- **Previews vencidos**: no hay scheduler nuevo. Cada `POST /imports/preview` borra los lotes `preview` del mismo usuario con `expires_at < now` y, además, si el usuario ya tiene 5 previews abiertos, borra el más viejo. Un preview vencido responde 410 "La previsualización venció: volvé a subir el archivo".
- **Export/borrado de cuenta**: `("import_batches", ImportBatch)` en `OWNED_TABLES` **después de `transactions`** (que lo referencia) y **antes de `bank_accounts`** (a la que referencia). `REDACTED_COLUMNS["import_batches"] = {"raw_table"}` (transitorio, puede pesar MB). Las columnas nuevas de `transactions` salen solas.

### D12. API

Todas bajo `/api/v1`, autenticadas, filtradas por `user_id`; un id ajeno responde 404.

| Método | Ruta | Request | Response |
|---|---|---|---|
| GET | `/finance/export` | query de D6 | archivo (200) · 422 topes/rango · 429 |
| GET | `/finance/imports/presets` | — | `[{key, label, description, required_fields}]` |
| POST | `/finance/imports/preview` | multipart: `file`, `preset?`, `account_id?`, `tz_offset_minutes?` | `ImportPreview` (201) · 413 · 415 · 422 |
| PUT | `/finance/imports/{id}/mapping` | `{preset?, header_row?, mapping?, account_id?, tz_offset_minutes?}` | `ImportPreview` recalculado desde `raw_table` (sin volver a subir) |
| POST | `/finance/imports/{id}/confirm` | `{rows: [{index, include, category_id?, type?, description?}]}` | `ImportBatchOut` (`imported_count`, `skipped_count`…) |
| GET | `/finance/imports` | `limit` (≤ 50) | `ImportBatchOut[]` (confirmados y deshechos, más nuevos primero) |
| GET | `/finance/imports/{id}` | — | `ImportBatchOut` |
| DELETE | `/finance/imports/{id}` | — | `preview` → se descarta (204); `confirmed` → **deshacer** (200 `ImportBatchOut` con `status=undone`); `undone` → 409 |

- `ImportPreview`: `batch_id`, `preset`, `detected_preset`, `mapping`, `mapping_source` (`preset|remembered|heuristic|user`), `headers[]`, `header_row`, `sample_rows` (las 5 primeras filas crudas para el editor de mapeo), `rows: ParsedRow[]` (todas, ≤ 5.000), `counts {ok, error, duplicate, possible_duplicate, skipped}`, `totals_by_currency` de las filas `ok`, `warnings[]` (archivo ya importado, fechas ambiguas, mapeo recordado), `expires_at`.
- **Confirmar**: solo filas `ok` o `possible_duplicate` con `include = true`; una fila `error` o `duplicate` con `include = true` → 422. Overrides validados: `category_id` debe ser del usuario; `type` en el enum; `description` 1–255. Todas las transacciones se insertan en **una transacción de base** junto con el cambio de estado del lote (todo o nada), en lotes de 500 `add_all`. Antes de insertar se **re-chequean las huellas** contra la base (otra pestaña pudo confirmar el mismo archivo): las que ya existen se cuentan como `duplicate` y no se insertan. `raw_table` pasa a `NULL`.
- **Deshacer**: borrado lógico (`is_deleted = true`, `deleted_at = now UTC`), igual que `DELETE /transactions/{id}`, de los movimientos del lote no borrados; `status = undone`. Incluye los que el usuario editó después de importar: la UI lo advierte con el conteo (`edited_count` = movimientos del lote con `updated_at > confirmed_at`). Como el chequeo de duplicados ignora los borrados, el archivo se puede volver a importar.
- Límites de frecuencia por usuario: `import_rate_limiter = _build_rate_limiter(20, 600)` para `preview` y `mapping`.
- Errores en español, sin trazas; nunca se devuelve contenido del archivo fuera del preview del propio usuario. El nombre de archivo se loguea, el contenido no.

### D13. Web (`frontend/`)

- `src/types`: `FinanceExportParams`, `ImportPreset`, `ImportMapping`, `ImportPreview`, `ParsedImportRow`, `ImportBatch`.
- `src/api/endpoints.ts`: `downloadFinanceExport(params)` (`responseType: 'blob'`, nombre desde `Content-Disposition` con fallback; mock: blob chico de ejemplo), `fetchImportPresets`, `previewImport(file, opts)` (`FormData`), `updateImportMapping`, `confirmImport`, `fetchImports`, `undoImport`, `discardImportPreview`, todos con mock (`MOCK_ENABLED`) que simula un preview de 8 filas con un duplicado y un error. `tz_offset_minutes: tzOffsetMinutes()`.
- `src/hooks/useFinanceImport.ts`: SWR `finance/imports`; confirmar o deshacer revalida `finance/imports`, `finance/summary`, `finance/transactions`, `finance/reports` (y `finance/net-worth` si existe la key).
- **Exportar**: botón "Exportar" junto a "Nueva transacción" → `ExportModal.tsx` (RHF + Zod sin `z.coerce`): Desde/Hasta (default mes en curso, fechas con `src/utils/date.ts`), Tipo, Categoría, Cuenta (prellenados con los filtros activos de la tabla), Formato (Excel / PDF), "Incluir inversiones y patrimonio", aviso de topes; descarga con `URL.createObjectURL` y muestra el error 422/429 del server.
- **Importar**: botón "Importar" → ruta `/finances/import` (`ImportPage.tsx`, lazy):
  1. *Subir*: zona de arrastre (`.csv,.xlsx`, valida tamaño en el cliente), selector de origen (Detectar automáticamente / Mercado Pago · Dinero disponible / Mercado Pago · Dinero en cuenta / Otro banco o billetera), cuenta destino opcional, ayuda corta de "Cómo descargar el reporte de Mercado Pago".
  2. *Previsualizar*: `MappingPanel` (fila de encabezado, columna por campo, modo de monto, formato de fecha, separador decimal, invertir signo, moneda por defecto) que llama a `PUT /mapping`; `PreviewTable` con checkbox por fila, chips de estado (OK · Error · Ya importado · Posible duplicado con tooltip del movimiento parecido), select de categoría con la sugerida marcada ("según tu historial" / "por palabra clave"), toggle ingreso/egreso, filtro por estado, totales de lo seleccionado por moneda; paginada en el cliente de a 100.
  3. *Confirmar*: resumen ("Vas a importar 142 movimientos: ingresos $ …, egresos $ …") → resultado y link a Transacciones.
  - `ImportHistory`: lotes con fecha, origen, archivo, cantidades y "Deshacer" (confirmación con el conteo de editados).
- Textos en español con voseo, dark mode con los tokens existentes, tabla usable en pantallas chicas (scroll horizontal dentro de la tarjeta, sin scroll de página).

### D14. Mobile (`C:\Proyectos\vida-personal-mobile`)

- Dependencia: `npx expo install expo-document-picker` (versión que corresponda a SDK 57). Es módulo nativo: **requiere un build nuevo** (EAS, perfiles `lan` y producción); no funciona en un APK viejo por OTA.
- `src/lib/exportFile.ts`: nueva `shareBinaryFile(bytes: Uint8Array, filename, mimeType, dialogTitle)` con `new File(Paths.cache, filename)`, `create({ overwrite: true })`, `write(bytes)` y `Sharing.shareAsync(uri, { mimeType, UTI })` (`com.microsoft.excel.xlsx` / `com.adobe.pdf`); en web, descarga por Blob como la función existente. Se verifica en el dispositivo que `File.write` acepte `Uint8Array` en la versión instalada; si no, se usa `File.downloadFileAsync` con el header `Authorization`.
- `src/api/endpoints.ts`: `downloadFinanceExport(params)` con `apiClient.get(..., { responseType: 'arraybuffer' })` (reusa el interceptor que renueva el token), `previewImport({ uri, name, mimeType })` con `FormData` (`{ uri, name, type }`), `updateImportMapping`, `confirmImport`, `fetchImports`, `undoImport`. **No** pasan por `queued(...)`: requieren conexión (sin red → mensaje "Necesitás conexión para importar/exportar").
- `FinanceScreen` (`TOOLS`): dos herramientas nuevas "Exportar" (`file-export-outline`) e "Importar" (`file-import-outline`). La grilla ya maneja cantidades impares.
- **Exportar** (`FinanceExportSheet`, `BottomSheet`): `DateField` Desde/Hasta, `FilterChips` de tipo y formato, selector de categoría y de cuenta, switch "Incluir inversiones", botón "Generar y compartir".
- **Importar** (`ImportScreen` en el stack de Finanzas): "Elegir archivo" con `DocumentPicker.getDocumentAsync({ type: ['text/csv', 'text/comma-separated-values', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel'], copyToCacheDirectory: true, multiple: false })` (Android reporta CSV con MIME distintos; el server decide por contenido), selector de origen y cuenta; preview como `FlatList` de `ImportRowItem` (checkbox, fecha, descripción, monto con color, chip de estado, categoría sugerida tocable que abre un picker), `BottomSheet` "Ajustar columnas" con el mismo `MappingPanel` simplificado, barra fija abajo con "Importar N movimientos"; historial con "Deshacer".
- Sin CTAs de compra ni precios (Finanzas es base). Tokens Stitch claro/oscuro.

### D15. Migración

`024_finance_imports` con `down_revision = "023_habit_reminders"` (head vigente al implementar; una sola cadena). `upgrade`: `create_table("import_batches", ...)` con check e índices; `batch_alter_table("transactions")` para sumar `import_batch_id` (FK con nombre explícito `fk_transactions_import_batch_id`, `ondelete="SET NULL"`) e `import_row_hash` + índice. `downgrade`: índice, FK, columnas (batch, por SQLite) y tabla. Verificado en SQLite (upgrade/downgrade/upgrade con datos) y en Postgres (PGlite).

## Dependencias

- **`finanzas-inversiones`** (implementado): el export usa `InvestmentService.summary`/`net_worth`. En mobile, las dos changes agregan herramientas a `TOOLS` de `FinanceScreen`: quien implemente segundo hace merge de la lista, no la reemplaza.
- **`finanzas-datos-mercado`** (implementado): la cotización sale de `InvestmentService.get_rates` (fuente elegida por el usuario: oficial/MEP/blue/manual; `modules/mercado`). El export de inversiones agrega un bloque "Cotizaciones" con la fuente y la fecha. Si cambia de dónde sale la cotización (`get_rates`), el export la toma igual porque pasa por `InvestmentService`; no hay que tocar nada acá.
- **`finanzas-recurrentes`** (implementado): las transacciones se vinculan a su plantilla por `transactions.recurring_parent_id` (expuesto como `recurrence_id`), sin FK; las plantillas viven en `recurring_transactions` / `recurring_occurrences` (`modules/recurrentes`). Lo importado nunca es recurrente (`is_recurring = false`, `recurring_parent_id = NULL`), y **deshacer es borrado lógico**, así que no rompe `recurring_occurrences.transaction_id` ni ninguna FK. El export de cuenta/borrado respeta el orden de `OWNED_TABLES`: `recurring_occurrences` → `transactions` → `import_batches` → `recurring_transactions` → … → `bank_accounts`.
- **`buscador-global`**: los movimientos importados aparecen en la búsqueda sin cambios (son transacciones comunes).
- Sin dependencias bloqueantes: este change se puede implementar antes o después de los otros.

## Risks / Trade-offs

- [Los encabezados reales de Mercado Pago en español no están documentados] → el preset matchea por identificador inglés + alias; cae al genérico editable si no matchea; tarea explícita de ajustar con un archivo real anonimizado y sumarlo como fixture.
- [Formatos de bancos sin documentar o que cambian sin aviso] → genérico con heurística + mapeo recordado por firma de encabezados; un cambio de columnas genera otra firma y el usuario vuelve a mapear una vez.
- [Ambigüedad dd/mm vs mm/dd y de "1.234"] → default es-AR, detección por columna con reglas explícitas, override visible en el preview y advertencia cuando la detección fue ambigua.
- [Huella con ocurrencia `#n`: si un export posterior trae una fila idéntica de más en un día ya importado, se marca como nueva] → es el comportamiento correcto (es otro movimiento); los "posibles duplicados" cubren el resto.
- [Preview con 5.000 filas pesa en la respuesta (~1,5 MB JSON)] → aceptable con gzip de nginx; la tabla del cliente pagina; mobile renderiza con `FlatList`.
- [CPU de generación en un worker de gunicorn] → threadpool + topes + rate limit; con 20.000 filas openpyxl write-only tarda pocos segundos.
- [Imagen +~20 MB, CVEs de Pillow] → versiones fijadas y actualizadas como el resto; Pillow solo se usa para el logo (o nada si es tipográfico), no procesa imágenes de usuarios.
- [Inyección de fórmulas por texto importado] → escape en el export (D4) aplicado a toda celda de texto; test con `=HYPERLINK(...)`, `+1`, `-2+3`, `@SUM`.
- [`raw_table` guarda datos financieros del archivo hasta 24 h] → aislado por usuario, se borra al confirmar/descartar/vencer y no sale en el export de cuenta; se borra con la cuenta.
- [Deshacer después de editar pierde esas ediciones] → advertencia con el conteo antes de confirmar el deshacer; es borrado lógico (recuperable por soporte).

## Migration Plan

1. Backend: agregar dependencias, construir la imagen ARM y correr la suite; deploy con `alembic upgrade head` (tabla nueva + columnas nulas en `transactions`, sin backfill). Endpoints nuevos y campos aditivos: clientes viejos no se enteran.
2. Web: deploy normal.
3. Mobile: build nuevo por `expo-document-picker` (módulo nativo).
4. **Rollback**: revertir web/mobile no requiere nada; revertir backend con `alembic downgrade` al head anterior borra lotes y huellas (los movimientos importados quedan como movimientos comunes).

## Decisiones del usuario (antes "Preguntas abiertas")

1. **Archivo real de Mercado Pago**: el usuario **no** aportó un export anonimizado. El preset de MP se construyó con el formato documentado/público (re-verificado por búsqueda web en noviembre 2026: `TRANSACTION_TYPE` incluye además `CASHBACK` y variantes `*_SHIPPING`; `SETTLEMENT_NET_AMOUNT` es el efecto real sobre el saldo; se recomienda CSV en UTF-8) y es **tolerante**: alias de encabezados en en/es/pt, separador `;` o `,`, BOM, utf-8/latin-1, decimales es-AR. El genérico con mapeo de columnas queda como respaldo. **Pendiente: validar con un archivo real** y completar los alias en español (tarea 9.4).
2. **Deshacer** borra el lote completo (incluye lo editado después), con advertencia previa y conteo de editados. **Decidido.**
3. **Posibles duplicados** vienen **destildados**. **Decidido.**
4. **PDF con emojis**: se quitan (sin fuente embebida). **Decidido.**
5. **Topes**: import 2 MiB / 5.000 filas; export 20.000 filas en xlsx, 5.000 en PDF. **Decidido.**
6. **Sin `.xls`** (se pide guardar como .xlsx/.csv). **Decidido.**
7. **Transferencias entre cuentas propias**: fuera de alcance. **Decidido.**
8. **Dinero**: `Decimal` de punta a punta (parseo, preview, JSON como string, inserción) con tope `Money` ±9.999.999.999,99. **`payment_method` y `account_type` solo toman valores del enum del backend** (`transfer` en presets de MP, `other` en genérico; `account_type` de la cuenta destino o `checking`): hubo un bug pasado donde la web mandaba "Efectivo" y daba 500.
9. **Mobile**: sin CTAs de compra, precios ni "comprar en la web".

## Alcance ampliado del export (acordado al implementar)

Con `include_investments=true` el reporte suma, además de activos y patrimonio, el bloque **Cotizaciones** (USD/EUR→ARS con fuente efectiva y fecha, de `modulos/mercado`) y las **plantillas recurrentes** del usuario (hoja/sección "Recurrentes": nombre, tipo, monto, moneda, frecuencia, próxima fecha, estado). Los movimientos generados por una recurrente salen en Movimientos como cualquier otro.
