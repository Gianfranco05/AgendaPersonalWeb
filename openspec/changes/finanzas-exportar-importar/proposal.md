## Why

Finanzas guarda los movimientos pero no deja sacarlos de la app de forma útil (el único export es el JSON crudo de "Exportar mis datos", que no sirve para el contador ni para revisar un mes) ni cargarlos en bloque: quien usa Mercado Pago o el home banking tiene que tipear movimiento por movimiento lo que ya está en un archivo. Exportar a Excel/PDF y importar CSV/XLSX resuelven las dos puntas y hacen que la app sea usable como registro real de gastos.

## What Changes

- **Exportar Finanzas a Excel (.xlsx) o PDF**, generado en el server con un rango de fechas (default: mes en curso) y filtros opcionales (tipo, categoría, cuenta):
  - **Excel**: una hoja por sección — *Resumen* (período, filtros, ingresos/egresos/balance por moneda), *Movimientos*, *Por categoría*, *Por mes* y, opcional, *Inversiones* (activos activos + patrimonio). Montos como números reales con formato, fechas como fechas, encabezado fijo y autofiltro.
  - **PDF**: reporte A4 legible en es-AR ("$ 1.234,56", "25/10/2026") con la marca **Can_cen**, las mismas secciones, encabezado de tabla repetido en cada página y "Página X de Y".
  - Topes: 20.000 movimientos en Excel y 5.000 en PDF (si se pasan, se pide achicar el rango); generación fuera del event loop y límite de frecuencia por usuario.
  - **Escape de celdas** que empiezan con `=`, `+`, `-`, `@`, tabulador o retorno (inyección de fórmulas al abrir en Excel/Sheets).
- **Importar movimientos desde CSV/XLSX** en dos pasos (subir → previsualizar → confirmar):
  - **Presets verificados de Mercado Pago** (reportes "Dinero disponible" y "Dinero en cuenta" que se descargan desde el panel en .csv o .xlsx, con encabezados en inglés, español o portugués y separador configurable). Para **bancos y billeteras (Galicia, Santander, Brubank, Ualá)** no hay formato público documentado: se resuelven con un **importador genérico con mapeo de columnas** (fecha, descripción, monto con signo o débito/crédito, moneda, referencia), detección automática del encabezado y **el mapeo se recuerda** para el próximo archivo con las mismas columnas.
  - Previsualización con detección de formato de fecha (dd/mm/aaaa por defecto), números es-AR ("1.234,56", "(1.234,56)", "$ -1.234,56") e inglés, signo, filas con error explicadas, **categoría sugerida** (historial del usuario primero, después reglas por palabras clave) y **detección de duplicados** (ya importado = misma huella de fila; posible duplicado = misma fecha y monto con descripción parecida a un movimiento existente).
  - Confirmar crea los movimientos de una vez y guarda un **lote de importación** que se puede **deshacer** desde el historial.
  - Validación estricta: tamaño máximo 2 MiB, 5.000 filas, 50 columnas, solo `.csv`/`.xlsx` verificados por contenido, protección contra XML/zip bombs, **ninguna fórmula se evalúa** (solo valores cacheados).
- **Web** (`frontend/`): botón "Exportar" en Finanzas (modal con rango, filtros, formato e "Incluir inversiones"), y página **Importar movimientos** (`/finances/import`) con asistente de 3 pasos e historial con "Deshacer". Modo mock mantenido.
- **Mobile** (`C:\Proyectos\vida-personal-mobile`): herramientas "Exportar" e "Importar" en la grilla de Finanzas; el export se guarda en un archivo y se abre la hoja de compartir (`expo-file-system` + `expo-sharing`, ya instalados); el import elige el archivo con `expo-document-picker` (dependencia nueva, requiere build nativo).
- Export y borrado de cuenta incluyen la tabla nueva de lotes.

### Fuera de alcance

- Importar PDFs de resúmenes (Mercado Pago, bancos, tarjetas) u OCR de comprobantes.
- Formatos `.xls` (Excel 97-2003), `.ods`, OFX/QIF y los ".xls" que en realidad son HTML (frecuentes en home banking): se pide guardarlos como .csv/.xlsx. Se puede sumar después como preset sin cambiar el flujo.
- Conexión directa a APIs de bancos o de Mercado Pago (OAuth/open banking): todo es por archivo que descarga el usuario.
- Presets de Galicia/Santander/Brubank/Ualá: quedan como mapeos recordados por usuario hasta tener un archivo real anonimizado para fijarlos (ver Preguntas abiertas en el design).
- Export programado/enviado por mail al contador; export CSV (el .xlsx lo cubre).
- Conversión de moneda en los totales del export: se informan por moneda, igual que hoy el balance asume ARS.

## Capabilities

### New Capabilities
- `finance-export`: export de movimientos, totales por categoría y por mes, balance y opcionalmente inversiones/patrimonio a .xlsx y PDF, con rango, filtros, topes, formato es-AR, marca Can_cen, escape de fórmulas, límite de frecuencia y descarga/compartir en web y mobile.
- `finance-import`: importación de movimientos desde CSV/XLSX en dos pasos con presets de Mercado Pago y mapeo genérico recordado, parseo de fechas/números es-AR, categorías sugeridas, detección de duplicados, lotes deshacibles, límites y validación de seguridad del archivo, UI web y mobile.

### Modified Capabilities
- `real-api-finance`: se agregan las llamadas de export (descarga binaria) e import (preview/confirm/historial/deshacer), y confirmar o deshacer una importación invalida las mismas keys de caché que crear o borrar un movimiento.

## Impact

- **Backend**: nuevo paquete `backend/app/modules/finanzas/transfer/` (`export_xlsx.py`, `export_pdf.py`, `report_data.py`, `import_parse.py`, `import_presets.py`, `import_rules.py`, `import_service.py`, `models.py`, `schemas.py`) y router `backend/app/api/v1/finance_transfer.py` (prefijo `/finance`) incluido en `backend/app/api/v1/router.py`; `backend/app/modules/finanzas/models.py` (columnas `import_batch_id`, `import_row_hash` en `transactions`); `backend/app/core/http_security.py` (limitadores de export/import y tope de body específico para la subida); `backend/app/config.py` (topes con default, sin variables obligatorias); `backend/app/modules/cuenta/service.py` (`OWNED_TABLES`, columna `raw_table` redactada); migración nueva (`0NN_finance_imports`, revisa el head vigente al implementar).
- **Dependencias Python nuevas** (`backend/requirements.txt`, todas con wheel para Python 3.11 en linux/arm64, sin paquetes de sistema): `openpyxl==3.1.5` (+ `et-xmlfile`), `defusedxml==0.7.1`, `reportlab==4.5.1` (+ `pillow`, `charset-normalizer`). Se descarta WeasyPrint por requerir Pango/Cairo en la imagen.
- **Tests**: `backend/tests/test_finance_export.py`, `test_finance_import_parse.py`, `test_finance_import_api.py`; archivos ficticios en `backend/tests/fixtures/finanzas_import/`; extensiones en `test_tenant_isolation.py`, `test_account.py`, `test_infra.py` (rutas nuevas autenticadas).
- **Web**: `frontend/src/pages/Finance/ExportModal.tsx`, `frontend/src/pages/Finance/Import/` (`ImportPage.tsx`, `UploadStep.tsx`, `MappingPanel.tsx`, `PreviewTable.tsx`, `ImportHistory.tsx`), `FinancePage.tsx`, `App.tsx` (ruta), `src/api/endpoints.ts` (+ mock), `src/hooks/useFinanceImport.ts`, `src/types`.
- **Mobile**: `src/screens/FinanceExportSheet.tsx`, `src/screens/ImportScreen.tsx`, `src/components/ImportRowItem.tsx`, `src/screens/FinanceScreen.tsx` (`TOOLS`), navegación de Finanzas, `src/lib/exportFile.ts` (archivos binarios), `src/api/endpoints.ts`, `src/hooks/useFinanceImport.ts`, `src/types`; `package.json` (`expo-document-picker`).
- **Infra**: imagen Docker algo más grande (~20 MB instalados por reportlab + Pillow); nginx ya admite 10 MB de body, no cambia.
