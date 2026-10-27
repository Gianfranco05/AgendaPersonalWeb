## Why

La mayoría de los movimientos de una persona se repiten (sueldo, alquiler, expensas, suscripciones, luz, gas, internet) y hoy hay que cargarlos a mano cada mes: se olvidan, el balance queda mal y los presupuestos no reflejan lo comprometido. Además, al vencer un plazo fijo la app no ofrece "renovarlo": el usuario tiene que cerrarlo y crear otro copiando datos y calculando a mano el capital nuevo (pregunta abierta 4 del change `finanzas-inversiones`).

## What Changes

- **Movimientos recurrentes (plantillas)** dentro de Finanzas (módulo base, gratis): el usuario define tipo (ingreso/gasto), nombre, descripción, monto, moneda, categoría, cuenta, medio de pago y una regla de frecuencia — cada N días, semanal (día de la semana, cada N semanas), mensual (día X, cada N meses: cubre bimestrales como luz y gas) o anual (día y mes) —, con fecha de inicio y fin opcional.
- **Generación automática en el servidor**: un scheduler in-process (como recordatorios y vencimientos) registra la transacción real el día que corresponde, desde las 09:00 locales del usuario, de forma idempotente y sin duplicados aunque corran varios workers de gunicorn (cursor con compare-and-set + restricción única por recurrencia y fecha). Recupera las ocurrencias atrasadas si el server estuvo caído, con tope.
- **Reglas de calendario explícitas**: día 29/30/31 en meses cortos cae en el último día del mes (sin "correrse" los meses siguientes); 29 de febrero anual cae el 28 en años no bisiestos.
- **Montos variables** ("Confirmar el monto antes de registrar"): en vez de crear la transacción, se crea un **pendiente** con monto sugerido y se avisa por push; el usuario confirma (editando monto/fecha) o lo saltea. Confirmar es idempotente.
- **Pausar / reanudar** una recurrencia (las fechas que caen durante la pausa no se generan), **editarla** solo afecta lo futuro y **borrarla** no borra las transacciones ya generadas.
- **Vínculo transacción ↔ recurrencia**: se reusan las columnas existentes `transactions.is_recurring` y `transactions.recurring_parent_id` (hoy sin uso). El listado de transacciones suma el filtro `recurrence_id` y la respuesta expone el vínculo.
- **Próximos movimientos**: endpoint de próximas fechas (30 días) y vista previa de las próximas fechas al armar la regla.
- **Push opcionales** por recurrencia: "Se registró: Sueldo" y "Confirmá el monto: Luz", agrupadas si salen varias juntas; tocar la push abre Recurrentes (y el pendiente).
- **Renovar plazo fijo**: en un plazo fijo activo vencido o que vence hoy, la acción "Renovar" cierra el actual y crea uno nuevo (mismo modelo `Investment`) con capital = monto cobrado (capital + interés) o solo el capital, retirando el interés y opcionalmente registrándolo como ingreso; pide nueva TNA y plazo. El nuevo guarda `renewed_from_id` y se puede ver el historial de renovaciones. Una inversión solo se puede renovar una vez (protege la cola offline).
- **Web**: pestaña "Recurrentes" en Finanzas (pendientes arriba, lista de plantillas, modal con vista previa), badge "Recurrente" en la tabla de transacciones, "Hacer recurrente" desde una transacción, botón "Renovar" y modal de renovación en Inversiones.
- **Mobile** (`C:\Proyectos\vida-personal-mobile`): pantalla Recurrentes con tile en la grilla de herramientas de Finanzas, opción "Recurrente" en el menú "+", aviso de pendientes en Finanzas, hoja de confirmación, "Renovar" en Inversiones y navegación desde la push.
- Export y borrado de cuenta incluyen las tablas nuevas.

### Fuera de alcance

- Transferencias automáticas entre cuentas o "ahorro automático" hacia metas/inversiones.
- Saldo de `bank_accounts` actualizado por transacciones (hoy no lo hace ninguna transacción; no se cambia).
- Feriados / "último día hábil" y reglas tipo "el segundo martes del mes".
- Precancelar o renovar un plazo fijo antes del vencimiento, y renovación automática sin intervención del usuario.
- Recurrencias de inversiones (aportes periódicos a un FCI, compra mensual de dólares).

## Capabilities

### New Capabilities
- `recurring-transactions`: plantillas de movimientos recurrentes por usuario, reglas de frecuencia y calendario, generación idempotente por scheduler con zona horaria del usuario y recuperación con tope, pendientes con confirmación, pausar/reanudar, semántica de edición/borrado, vínculo con transacciones, próximos movimientos, aislamiento y export/borrado de cuenta.
- `recurring-notifications`: push opcionales al registrarse un movimiento recurrente o al quedar un pendiente para confirmar, agrupadas por usuario y sin duplicados.
- `fixed-term-renewal`: renovar un plazo fijo vencido creando uno nuevo vinculado, con capital + interés o solo capital (interés opcional como ingreso), nueva TNA y plazo, e historial de renovaciones.

### Modified Capabilities
- `real-api-finance`: se agregan las llamadas a la API de recurrentes y de renovación desde web y mobile, el vínculo/filtro de recurrencia en transacciones y la invalidación de caché correspondiente (requisitos agregados; los existentes no cambian).

## Impact

- **Backend**: nuevo módulo `backend/app/modules/recurrentes/` (models, schemas, rules, repository, service, scheduler, api_routes) con router incluido en `backend/app/api/v1/router.py`; `backend/app/main.py` (lifespan arranca el scheduler de recurrentes); `backend/app/api/v1/finance.py` (filtro `recurrence_id` y campo `recurrence_id` en transacciones); `backend/app/modules/finanzas/repository.py` (borrar categoría/cuenta desvincula recurrencias); `backend/app/modules/inversiones/` (columna `renewed_from_id`, servicio y rutas de renovación); `backend/app/modules/cuenta/service.py` (`OWNED_TABLES`); migración `backend/migrations/versions/021_recurring_transactions.py` (revisa `020_market_data`).
- **Tests**: nuevos `test_recurring_rules.py`, `test_recurring.py`, `test_recurring_scheduler.py`, `test_fixed_term_renewal.py`; extensiones en `test_tenant_isolation.py`, `test_account.py`, `test_api_finance.py`, `test_infra.py` (guarda de rutas públicas).
- **Web** (`frontend/`): `src/pages/Finance/` (`RecurringSection.tsx`, `RecurringModal.tsx`, `ConfirmOccurrenceModal.tsx`, `RenewFixedTermModal.tsx`, cambios en `FinancePage.tsx`, `TransactionTable.tsx`, `InvestmentsSection.tsx`), `src/api/endpoints.ts` (+ mock), `src/hooks/useRecurring.ts`, `src/hooks/useInvestments.ts`, `src/types`.
- **Mobile** (`C:\Proyectos\vida-personal-mobile`): `src/screens/RecurringScreen.tsx`, `src/components/RecurringFormSheet.tsx`, `ConfirmOccurrenceSheet.tsx`, `RenewFixedTermSheet.tsx`, `src/navigation/TabNavigator.tsx`, `src/screens/FinanceScreen.tsx`, `src/components/QuickCreateSheet.tsx`, `src/lib/notifications.ts`, `src/api/endpoints.ts`, `src/hooks/useRecurring.ts`, `src/types`.
- **Infra**: sin dependencias ni APIs externas nuevas; Redis no es necesario para la deduplicación (la garantiza la base). Un loop más en el lifespan por worker.
