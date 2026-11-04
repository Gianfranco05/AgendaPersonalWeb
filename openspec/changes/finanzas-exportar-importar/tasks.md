## 1. Backend — Dependencias y configuración

- [x] 1.1 Confirmar versiones con `pip index versions` y agregar a `backend/requirements.txt` con `==` y comentario: `openpyxl==3.1.5`, `et-xmlfile`, `defusedxml==0.7.1`, `reportlab` 4.5.x (no la 5.1.0 recién publicada), `pillow` y `charset-normalizer` en las versiones que pida reportlab (design D2)
- [ ] 1.2 Construir la imagen del backend para `linux/arm64` (`docker buildx build --platform linux/arm64 backend/`) y verificar que ninguna dependencia compila desde fuente ni pide paquetes `apt`; anotar el aumento de tamaño
- [x] 1.3 `backend/app/config.py`: `FINANCE_EXPORT_MAX_ROWS_XLSX=20000`, `FINANCE_EXPORT_MAX_ROWS_PDF=5000`, `FINANCE_IMPORT_MAX_BYTES=2 MiB`, `FINANCE_IMPORT_MAX_ROWS=5000`, `FINANCE_IMPORT_MAX_COLUMNS=50`, `FINANCE_IMPORT_PREVIEW_TTL_HOURS=24` (todos con default; sin variables obligatorias en `docker-compose.prod.yml`)
- [x] 1.4 `backend/app/core/http_security.py`: `export_rate_limiter` (10/300 s) e `import_rate_limiter` (20/600 s) por `user_id` con dependencias `rate_limit_finance_export` / `rate_limit_finance_import`; `BodySizeLimitMiddleware` con tope por ruta para `POST /api/v1/finance/imports/preview` (`FINANCE_IMPORT_MAX_BYTES + 64 KiB`), sin cambiar el global de 1 MiB

## 2. Backend — Modelo y migración

- [x] 2.1 Crear `backend/app/modules/finanzas/transfer/__init__.py` y `models.py` con `ImportBatch` (columnas, checks e índices de design D11; `JSON` de SQLAlchemy; FK `account_id` con `ondelete="SET NULL"`)
- [x] 2.2 `backend/app/modules/finanzas/models.py`: sumar a `Transaction` `import_batch_id` (FK nombrada, `ondelete="SET NULL"`) e `import_row_hash` (`String(64)`) con índice `(user_id, import_row_hash)`; registrar el modelo nuevo donde se importan los modelos para `Base.metadata`
- [x] 2.3 Migración `backend/migrations/versions/024_finance_imports.py` con `down_revision = "023_habit_reminders"`: `create_table`, `batch_alter_table("transactions")` para columnas + FK + índice; `downgrade` simétrico con batch
- [x] 2.4 Verificar `alembic heads` = un solo head y `upgrade head` / `downgrade -1` / `upgrade head` en SQLite
- [x] 2.5 `TransactionResponse` (`finanzas/schemas.py`) suma `import_batch_id: Optional[UUID] = None` (aditivo)
- [x] 2.6 `backend/app/modules/cuenta/service.py`: `("import_batches", ImportBatch)` en `OWNED_TABLES` después de `transactions` y antes de `bank_accounts`; `REDACTED_COLUMNS["import_batches"] = {"raw_table"}`

## 3. Backend — Export

- [x] 3.1 `transfer/cells.py`: `safe_text()` (prefijo `'` para `= + - @ \t \r \n`), `pdf_safe()` (quita lo que no entra en cp1252), `format_money_ar(Decimal, currency)`, `format_date_ar`, etiquetas en español de tipo y medio de pago; sin `locale`
- [x] 3.2 `transfer/report_data.py`: `ReportFilters` (defaults de rango con `local_today`, `date_to >= date_from`, máximo 5 años, `category_id="none"`), resolución de `account_id` a (tipo, últimos 4, banco) con 404 si es ajena, `COUNT` previo con topes → 422, consulta única con `LEFT JOIN categories`, agregados por moneda/categoría/mes en `Decimal`, bloque de inversiones vía `InvestmentService.summary`/`net_worth`, cotizaciones vigentes (`get_rates`) y plantillas recurrentes del usuario
- [x] 3.3 `transfer/export_xlsx.py`: `Workbook(write_only=True)`, hojas Resumen/Movimientos/Por categoría/Por mes/Inversiones/Recurrentes (D4), `WriteOnlyCell` con `data_type="s"` + `safe_text` en todo texto, números con formato y egresos en rojo, fechas `DD/MM/YYYY`, encabezado fijo y autofiltro, `creator="Can_cen"`
- [x] 3.4 `transfer/export_pdf.py`: Platypus A4, encabezado con logotipo "C_C" + "Can_cen" + período, pie "Generado el … · Página X de Y" (canvas de dos pasadas), tablas con `repeatRows=1`, colores de ingreso/egreso, top 15 categorías + "Otras", sección de inversiones/patrimonio
- [x] 3.5 Router `backend/app/api/v1/finance_transfer.py` (`prefix="/finance"`) con `GET /export`: validación de query, rate limit, generación en `run_in_threadpool` sobre `SpooledTemporaryFile`, `StreamingResponse` por chunks con `Content-Length`, `Content-Disposition`, `Cache-Control: no-store`; incluirlo en `backend/app/api/v1/router.py`

## 4. Backend — Import: parseo

- [x] 4.1 `transfer/import_parse.py` — recepción: lectura del `UploadFile` por chunks con corte en `FINANCE_IMPORT_MAX_BYTES` (413), detección de tipo por contenido (zip `PK\x03\x04`, OLE `D0 CF 11 E0` → 415 con mensaje de `.xls`, binario → 415), nombre de archivo saneado (solo base, ≤ 255)
- [x] 4.2 XLSX seguro: inspección previa con `zipfile` (≤ 200 entradas, ≤ 25 MiB descomprimido, ratio ≤ 100, sin `..`/rutas absolutas, sin `vbaProject.bin`); `load_workbook(read_only=True, data_only=True)` con defusedxml instalado; primera hoja visible; fórmula sin valor cacheado → error de fila
- [x] 4.3 CSV: `utf-8-sig` con fallback `cp1252`, `csv.Sniffer` limitado a `, ; \t |`, limpieza de `NUL`; topes de filas (5.000 → 422), columnas (50) y celdas (500 caracteres)
- [x] 4.4 Detección de fila de encabezado en las primeras 30 filas y normalización de encabezados (minúsculas, sin tildes, espacios colapsados); `header_signature`
- [x] 4.5 Fechas (D8.7): ISO con offset → huso del usuario (fecha y hora locales), `yyyy-mm-dd`, `dd/mm/yyyy`, `dd-mm-yyyy`, `dd.mm.yyyy`, `dd/mm/yy`, celdas `datetime`, seriales de Excel; default día-primero con detección por columna; rango 2000-01-01..hoy+1 año
- [x] 4.6 Números `parse_amount_ar` (D8.8): símbolos, paréntesis y signo adelante/atrás, separadores con detección por columna u override, cuantizado a 2, tope `Money`, cero → `skipped`
- [x] 4.7 Signo/tipo según `amount_mode` e `invert_sign`; moneda normalizada y permitida; descripción saneada (≤ 255 en `product_name`, resto a `notes`, vacía → "Movimiento importado")
- [x] 4.8 `transfer/import_presets.py`: `mercadopago_release`, `mercadopago_account_money` (alias en/es/pt, filas informativas → `skipped`, traducción de códigos `DESCRIPTION`, signo por `TRANSACTION_TYPE`) y `generic` con heurística de encabezados en español; elección automática por columnas requeridas

## 5. Backend — Import: sugerencias, duplicados, lotes y API

- [x] 5.1 `transfer/import_rules.py`: normalización de descripción, historial exacto y por palabra clave (una consulta por preview, 24 meses, solo el usuario), reglas por palabra clave → `merchant_category` y sinónimos → categoría del usuario; `suggestion_source`
- [x] 5.2 Huella de fila con ocurrencia `#n`, estados `duplicate` (huella existente no borrada) y `possible_duplicate` (±1 día, mismo tipo/monto/moneda, descripción parecida) con una consulta por rango; aviso por `file_sha256` de lote confirmado
- [x] 5.3 `transfer/import_service.py` — `preview()`: limpieza de previews vencidos y tope de 5 abiertos, mapeo recordado por firma (solo lotes `confirmed` del usuario), `raw_table` con tope de 4 MiB, armado de `ImportPreview` (D12)
- [x] 5.4 `remap()` desde `raw_table` (410 vencido, 409 si no está en `preview`), `confirm()` (validación de overrides, 422 por filas `error`/`duplicate` incluidas, re-chequeo de huellas, inserción en una transacción en tandas de 500, datos de cuenta destino, `payment_method` por preset, limpiar `raw_table`), `undo()` (borrado lógico con `deleted_at` UTC, `edited_count`, 409 si ya deshecho), `discard()`
- [x] 5.5 `transfer/schemas.py` (`ImportMapping`, `ParsedRow`, `ImportPreview`, `ImportConfirmRequest`, `ImportBatchOut`, `ImportPresetOut`) y rutas en `finance_transfer.py`: `GET /imports/presets`, `POST /imports/preview` (multipart), `PUT /imports/{id}/mapping`, `POST /imports/{id}/confirm`, `GET /imports`, `GET /imports/{id}`, `DELETE /imports/{id}`; todas con `get_current_user`, rate limit en preview/mapping, errores en español, sin loguear contenido

## 6. Tests backend

- [x] 6.1 Fixtures ficticios en `backend/tests/fixtures/finanzas_import/`: `mp_release_en.csv` (coma, con filas informativas), `mp_release_es_punto_y_coma.csv`, `mp_account_money.csv` (fechas `-04:00`), `banco_generico_cp1252.csv` (preámbulo, `Fecha;Concepto;Débito;Crédito;Saldo`, "1.234,56"), `billetera_monto_signo.xlsx` + `make_fixtures.py` que lo regenera, `inyeccion_formulas.csv`; los casos maliciosos (zip bomb, macro, fórmula sin caché, OLE) se generan en el test
- [x] 6.2 `backend/tests/test_finance_import_parse.py`: fechas (ISO con offset → local, día-primero, mes-primero detectado, seriales), números es-AR/en con y sin override, paréntesis, cero, tope, débito y crédito a la vez, monedas, encabezado con preámbulo, cp1252, separadores, límites de filas/columnas/celdas, zip bomb, macro, `.xls` OLE, fórmula sin valor cacheado (sin evaluar)
- [x] 6.3 `backend/tests/test_finance_import_api.py`: preview de cada preset, remap, confirm (cuenta destino, categorías, `import_batch_id`), duplicados al re-subir, dos filas idénticas en un archivo, posible duplicado contra un movimiento manual, confirm concurrente, 422/409/410/413/415, mapeo recordado por usuario, deshacer (balance, editados, re-importar después), limpieza de previews, rate limit
- [x] 6.4 `backend/tests/test_finance_export.py`: xlsx leído con openpyxl (hojas, números, fechas, sin celdas fórmula, escape de `=HYPERLINK`, `+1`, `-2+3`, `@SUM`, montos negativos intactos), totales que cuadran por moneda, filtros (tipo, categoría, `none`, cuenta), inversiones on/off, PDF válido (`%PDF`, varias páginas, "$ 1.234,50", emoji sin fallar), topes 422, rango inválido, rate limit 429, headers de la respuesta
- [x] 6.5 Aislamiento: extender `test_tenant_isolation.py` (lotes, export con `category_id`/`account_id` ajenos, sugerencias y duplicados sin datos de otro usuario); `test_account.py` (export sin `raw_table`, borrado con lotes y transacciones importadas); `test_infra.py` sin rutas públicas nuevas
- [ ] 6.6 Regresión: suite completa `cd backend && python -m pytest -q` en verde (~777 + nuevos)

## 7. Web (`frontend/`)

- [x] 7.1 `src/types`: `FinanceExportParams`, `ImportPreset`, `ImportMapping`, `ImportPreview`, `ParsedImportRow`, `ImportBatch`; `Transaction.import_batch_id?`
- [x] 7.2 `src/api/endpoints.ts`: `downloadFinanceExport` (blob + filename de `Content-Disposition`), `fetchImportPresets`, `previewImport` (`FormData`), `updateImportMapping`, `confirmImport`, `fetchImports`, `undoImport`, `discardImportPreview`, con `tz_offset_minutes` y mocks (`MOCK_ENABLED`) con un duplicado y un error
- [x] 7.3 `src/hooks/useFinanceImport.ts`: SWR `finance/imports` y revalidación de `finance/summary`, `finance/transactions`, `finance/reports` (y `finance/net-worth`) tras confirmar o deshacer
- [x] 7.4 `src/pages/Finance/ExportModal.tsx` (RHF + Zod sin `z.coerce`, fechas con `src/utils/date.ts`, prellenado con filtros activos, formato, inversiones, errores 422/429) y botones "Exportar" e "Importar" en `FinancePage.tsx`
- [x] 7.5 `src/pages/Finance/Import/ImportPage.tsx` + ruta lazy `/finances/import` en `App.tsx`: `UploadStep` (drop zone `.csv,.xlsx`, tamaño en cliente, origen, cuenta, ayuda de Mercado Pago), `MappingPanel`, `PreviewTable` (checkbox, chips, categoría sugerida con origen, tipo, filtro, totales, paginado de a 100), paso de confirmación y resultado
- [x] 7.6 `ImportHistory.tsx` con "Deshacer" y advertencia de editados; dark mode, voseo, sin scroll horizontal de página en móvil
- [x] 7.7 Tests vitest: endpoints (multipart, blob + filename, mocks), `ExportModal` (defaults y validación), `PreviewTable` (armado del request de confirmación con exclusiones y overrides), invalidación de caché; `npx vitest run --maxWorkers=2` y `npm run build` en verde

## 8. Mobile (`C:\Proyectos\vida-personal-mobile`)

- [ ] 8.1 [mobile] `npx expo install expo-document-picker` (versión de SDK 57) en `package.json`; anotar que requiere build nativo nuevo
- [ ] 8.2 [mobile] `src/lib/exportFile.ts`: `shareBinaryFile(bytes, filename, mimeType, dialogTitle)` con `File`/`Paths.cache` y `Sharing.shareAsync` (UTI xlsx/pdf), fallback Blob en web; verificar en dispositivo que `File.write` acepta `Uint8Array` (si no, `File.downloadFileAsync` con `Authorization`)
- [ ] 8.3 [mobile] `src/types` y `src/api/endpoints.ts`: `downloadFinanceExport` (`responseType: 'arraybuffer'`), `previewImport` (`FormData` con `{ uri, name, type }`), `updateImportMapping`, `confirmImport`, `fetchImports`, `undoImport`, sin `queued(...)`; `src/hooks/useFinanceImport.ts` con la misma invalidación que web
- [ ] 8.4 [mobile] `src/screens/FinanceScreen.tsx`: herramientas "Exportar" e "Importar" en `TOOLS` (merge con las de `finanzas-inversiones`/`finanzas-recurrentes` si ya están) y registro de `ImportScreen` en el stack de Finanzas
- [ ] 8.5 [mobile] `FinanceExportSheet` (`BottomSheet`, `DateField`, `FilterChips`, categoría, cuenta, switch inversiones, "Generar y compartir", aviso sin conexión)
- [ ] 8.6 [mobile] `src/screens/ImportScreen.tsx` + `src/components/ImportRowItem.tsx`: elegir archivo (MIME CSV/XLSX variados), origen y cuenta, preview en `FlatList`, picker de categoría, sheet "Ajustar columnas", barra "Importar N movimientos", historial con "Deshacer"; tokens Stitch claro/oscuro, sin textos de compra
- [ ] 8.7 [mobile] `npx tsc --noEmit` y tests existentes en verde

## 9. Verificación contra backend real (no mock)

- [ ] 9.1 Postgres: `alembic upgrade head` / `downgrade -1` / `upgrade head` en PGlite (o Postgres en Docker) con datos previos en `transactions`; confirmar un import y borrar la cuenta sin errores de FK
- [ ] 9.2 Web contra el backend real (`VITE_MOCK_ENABLED=false`): exportar xlsx y PDF de un mes con datos, abrir el .xlsx en Excel/LibreOffice (números sumables, fechas, sin fórmulas activas) y el PDF (marca, es-AR, paginado)
- [ ] 9.3 Web: importar cada fixture, ajustar mapeo, confirmar, ver movimientos y balance actualizados, re-subir (todo "Ya importado"), deshacer y re-importar
- [ ] 9.4 Con un export real anonimizado de Mercado Pago (y del banco/billetera del usuario si lo comparte): ajustar alias en español de los presets, sumarlo como fixture y repetir 9.3
- [ ] 9.5 Mobile (build `lan` con `expo-document-picker`): exportar y compartir xlsx/PDF a Drive/WhatsApp, importar un CSV desde Descargas, deshacer desde el historial; probar en modo claro y oscuro
- [ ] 9.6 Imagen ARM de producción: build y arranque con las dependencias nuevas, export PDF dentro del contenedor
