## Context

- **Transacciones hoy**: `backend/app/modules/finanzas/models.py::Transaction` guarda cada movimiento con la cuenta como texto (`bank_entity_name`, `account_type`, `account_last4`), `payment_method`, `category_id` (FK sin `ON DELETE`) y fechas como texto ISO (`IsoText`). El borrado es lógico (`is_deleted`). Ya existen `is_recurring` (bool) y `recurring_parent_id` (`String(36)`, sin FK) **sin ningún uso** en backend, web ni mobile: se reusan acá. `TransactionResponse` ya expone `is_recurring`.
- **Creación**: `FinanzasService.create_transaction` valida que la categoría sea del usuario y el repo hace `commit` adentro. Los borrados de categoría y cuenta (`CategoryRepository.delete`, `BankAccountRepository.delete`) desvinculan a mano lo que las apunta porque las FK no tienen `ON DELETE` (en Postgres daba 500; SQLite no aplica FKs y lo escondía).
- **Schedulers**: `recordatorios/scheduler.py` e `inversiones/scheduler.py` corren un loop por worker de gunicorn desde el `lifespan` de `backend/app/main.py`. El de inversiones usa una **ventana horaria local** (09:00–21:59) + marca persistente con `UPDATE ... WHERE` y `rowcount == 1` para que solo un worker actúe, y `claim_once` de Redis como capa barata opcional. El huso horario es `timezone_offset_minutes` por fila (minutos al este de UTC, lo manda el cliente en cada escritura; fallback −180).
- **Inversiones**: `backend/app/modules/inversiones/` (change `finanzas-inversiones`, implementado en la rama pero no archivado): `Investment` con `status active|closed`, plazo fijo calculado en `valuation.py` (`valuate(inv, today).fixed_term.amount_at_maturity`), `days_to_maturity` según `tz_offset_minutes`. Su pregunta abierta 4 dejó "Renovar" fuera; este change la resuelve.
- **Guardas**: `OWNED_TABLES` en `backend/app/modules/cuenta/service.py` (test que falla si una tabla con `user_id` no está), `test_infra.py::test_no_api_route_is_public_by_accident`, `test_tenant_isolation.py`, montos con `Money` (±9.999.999.999,99). Migraciones Alembic, head `018_investments`.
- **Clientes**: web `frontend/` (`FinancePage.tsx` con pestañas, `TransactionModal` como patrón RHF + Zod sin `z.coerce`, modo mock), mobile `C:\Proyectos\vida-personal-mobile` (`FinanceScreen` con `TOOLS`/`TOOL_ROWS` que ya maneja cantidad impar, `QuickCreateSheet`, `BottomSheet`, `DateField`, `NumberStepper`, `FilterChips`, `queued(...)` para la cola offline, `src/lib/notifications.ts::targetFromData` para el tap de push).

## Goals / Non-Goals

**Goals:**
- Plantillas de movimientos recurrentes con reglas diaria/semanal/mensual/anual (cada N), inicio y fin opcional.
- Generación en el servidor, en la fecha local del usuario, **exactamente una vez** por recurrencia y fecha aunque haya varios workers, reinicios o sin Redis; recuperación de atrasadas con tope.
- Pendientes con confirmación para montos variables; pausar/reanudar; edición solo hacia adelante; borrado que conserva lo generado; vínculo transacción ↔ recurrencia.
- Push opcionales agrupadas.
- Renovar un plazo fijo vencido con vínculo e historial, reusando `Investment`.
- Aislamiento por usuario y export/borrado de cuenta de las tablas nuevas.

**Non-Goals:**
- Feriados, "último día hábil", "segundo martes", transferencias automáticas, ahorro automático, recurrencias de inversiones.
- Actualizar `bank_accounts.balance` (ninguna transacción lo hace hoy).
- Proyectar el balance futuro en `/finance/summary` (solo se listan los próximos movimientos).
- Precancelación o renovación automática de plazos fijos.

## Decisions

### D1. Generación por scheduler del servidor (no "al abrir")

Un loop `run_recurring_scheduler()` en el `lifespan`, alineado al minuto como los otros dos, es **el único generador periódico**. Además, crear, editar la regla o reanudar una recurrencia materializa en el acto lo que ya esté vencido (sin push: el usuario está en la app).

Por qué no "al abrir la app":
- La push "Se registró tu sueldo" / "Confirmá el monto de la luz" necesita que el server sepa cuándo toca, sin cliente abierto.
- El balance, los presupuestos, el widget del Dashboard, el export y los futuros widgets de Android (change `widgets-android`) tienen que ver la transacción aunque el usuario no abra Finanzas, y desde cualquier dispositivo (web y mobile) con el mismo resultado.
- Generar dentro de un `GET` mete escrituras y carreras en lecturas que hoy son puras (y los clientes pueden pedir el resumen en paralelo).
- La infraestructura (lifespan, push, patrón de dedup) ya existe y está probada en vencimientos.

*Alternativa descartada*: generación perezosa al leer `/finance/*`. Más simple de desplegar, pero sin push, con resultados distintos según quién lea primero y con escrituras en GET.

### D2. Modelo de datos

**`recurring_transactions`** (la plantilla):

| Columna | Tipo | Null | Notas |
|---|---|---|---|
| `id` | `String(36)` PK | no | uuid4 |
| `user_id` | `String(36)` FK `users.id` | no | index |
| `type` | `String(10)` | no | `income` / `expense` |
| `name` | `String(255)` | no | → `product_name` de la transacción |
| `description` | `Text` | sí | → `product_description` (≤ 1000 en schema) |
| `notes` | `Text` | sí | → `notes` (≤ 2000) |
| `amount` | `Numeric(12,2)` | sí | `> 0`; null solo si `requires_confirmation` ("monto variable sin estimado") |
| `currency` | `String(3)` | no | default `ARS` (mismo criterio que `transactions`) |
| `category_id` | `String(36)` FK `categories.id` | sí | validada como propia |
| `bank_account_id` | `String(36)` FK `bank_accounts.id` | sí | validada como propia |
| `account_type` | `String(10)` | no | default `cash`; se usa si no hay `bank_account_id` |
| `payment_method` | `String(20)` | no | default `cash`, enum `PaymentMethod` |
| `merchant_name` | `String(255)` | no | default `""` |
| `merchant_category` | `String(20)` | no | default `other` |
| `frequency` | `String(10)` | no | `daily`, `weekly`, `monthly`, `yearly` |
| `interval_count` | `Integer` | no | default 1 ("cada N"); `interval` se evita por ser palabra clave SQL |
| `weekday` | `SmallInteger` | sí | 0 = lunes … 6 = domingo (`date.weekday()`), solo `weekly` |
| `day_of_month` | `SmallInteger` | sí | 1–31, `monthly` y `yearly` |
| `month_of_year` | `SmallInteger` | sí | 1–12, solo `yearly` |
| `start_date` | `Date` | no | |
| `end_date` | `Date` | sí | inclusive |
| `anchor_date` | `Date` | no | primera ocurrencia de la regla vigente (D3); la calcula el server |
| `next_occurrence_date` | `Date` | sí | cursor; null = terminada (pasó `end_date`) |
| `last_occurrence_date` | `Date` | sí | última fecha procesada (generada, pendiente o salteada por pausa) |
| `status` | `String(10)` | no | `active` / `paused` |
| `paused_at` | `DateTime(tz)` | sí | |
| `requires_confirmation` | `Boolean` | no | default false |
| `notify` | `Boolean` | no | default true |
| `timezone_offset_minutes` | `Integer` | sí | minutos al este de UTC; fallback −180 |
| `created_at`, `updated_at` | `DateTime(tz)` | no | `server_default=func.now()` |

Checks (válidos en SQLite y Postgres): `amount IS NULL OR amount > 0`, `amount IS NOT NULL OR requires_confirmation`, `interval_count >= 1`, `end_date IS NULL OR end_date >= start_date`, `status IN ('active','paused')`, `frequency IN (...)`. Índices: `ix_recurring_user_status (user_id, status)`, `ix_recurring_status_next (status, next_occurrence_date)` para el scheduler.

Límites de `interval_count` (schema): `daily` 1–365, `weekly` 1–52, `monthly` 1–12, `yearly` 1–10. Campos de la regla obligatorios según frecuencia (`weekly` → `weekday`; `monthly` → `day_of_month`; `yearly` → `day_of_month` + `month_of_year`, con día válido para ese mes contando el 29/2); los que no corresponden se guardan en null.

**`recurring_occurrences`** (el libro de lo que ya se procesó; da la idempotencia y la cola de pendientes):

| Columna | Tipo | Null | Notas |
|---|---|---|---|
| `id` | `String(36)` PK | no | |
| `user_id` | `String(36)` FK `users.id` | no | index; aislamiento y `OWNED_TABLES` |
| `recurrence_id` | `String(36)` FK `recurring_transactions.id` | no | |
| `occurrence_date` | `Date` | no | fecha "teórica" de la regla |
| `status` | `String(10)` | no | `generated` (automática), `pending`, `confirmed`, `skipped` |
| `suggested_amount` | `Numeric(12,2)` | sí | solo pendientes (D6) |
| `transaction_id` | `String(36)` FK `transactions.id` | sí | la transacción creada (`generated`/`confirmed`) |
| `resolved_at` | `DateTime(tz)` | sí | al confirmar/saltear |
| `created_at` | `DateTime(tz)` | no | |

`UniqueConstraint(recurrence_id, occurrence_date)` = **una sola ocurrencia por recurrencia y fecha**, a nivel base. Índice `ix_occurrences_user_status (user_id, status)`.

**`transactions`** (sin columnas nuevas): las generadas llevan `is_recurring = true` y `recurring_parent_id = recurrence.id`. Se agrega el índice `ix_transactions_recurring_parent_id`. La respuesta suma `recurrence_id` (= `recurring_parent_id`) y el listado acepta `?recurrence_id=`.

*Alternativa descartada*: idempotencia solo con una columna `recurrence_date` única en `transactions`. No sirve para los pendientes (que todavía no son transacción) ni para registrar los salteados, y `transactions` tiene fechas como texto y borrado lógico.

### D3. Reglas de calendario (`recurrentes/rules.py`, funciones puras)

- **Ancla**: `anchor_date` = primera fecha ≥ `start_date` que cumple la regla (`daily`: el propio `start_date`; `weekly`: el primer `weekday`; `monthly`: el primer mes cuyo día `day_of_month` (ajustado) sea ≥ `start_date`; `yearly`: idem con mes y día). Ej.: bimestral día 5 creado el 25/10 → 05/11, 05/01, 05/03…
- **Ocurrencia k** (k = 0, 1, 2…) se calcula **desde el ancla**, nunca desde la anterior, para que el ajuste de fin de mes no arrastre: `monthly` → mes `anchor + k·N` con día `min(day_of_month, último día del mes)`; `yearly` → año `anchor + k·N`; `weekly` → `anchor + 7·N·k` días; `daily` → `anchor + N·k` días.
- **Día 29/30/31 en meses cortos**: cae en el último día de ese mes (31 → 30/04, 28/02 o 29/02 en bisiesto) y vuelve a 31 en marzo. "Día 31" funciona así como "último día del mes" (la UI lo aclara).
- **29 de febrero anual**: 28/02 en años no bisiestos.
- `next_after(rule, anchor, d)` = menor ocurrencia > `d`; `first_on_or_after(rule, anchor, d)`; `occurrences_between(rule, anchor, desde, hasta)`. Si la siguiente supera `end_date`, el cursor queda en null (terminada).
- Las mismas funciones alimentan la vista previa (`POST /finance/recurring/preview`, próximas 5 fechas) y `GET /finance/recurring/upcoming`, así la UI nunca reimplementa la regla (el modo mock de la web usa un cálculo simplificado, documentado como aproximado).

### D4. Zona horaria y hora de generación

- "Hoy" del usuario = `(now_utc + offset).date()` con `offset = timezone_offset_minutes ?? -180`, igual que vencimientos. Los clientes mandan el offset en **toda** escritura sobre la recurrencia (crear, editar, pausar, reanudar) y al confirmar/saltear un pendiente se actualiza el de su recurrencia.
- El scheduler genera solo cuando la hora local está en la ventana **09:00–21:59** (constantes `WINDOW_START_HOUR = 9`, `WINDOW_END_HOUR = 22`, iguales a vencimientos). Así las push nunca salen de madrugada y una caída del server a las 9 se recupera en el primer ciclo dentro de la ventana o al día siguiente, **con la fecha original** (la transacción del sueldo del 5 queda fechada el 5 aunque se registre el 6).
- La query del ciclo es barata e indexada: `status = 'active' AND next_occurrence_date IS NOT NULL AND next_occurrence_date <= utc_today + 1` (el +1 cubre offsets de hasta +14 h); el filtro fino por fecha/hora local se hace en Python.
- Las materializaciones disparadas por la API (crear, cambiar regla, reanudar) ignoran la ventana y generan lo que tenga fecha ≤ hoy local.

### D5. Idempotencia y concurrencia (varios workers, reinicios, sin Redis)

`materialize(rec, local_today)`, en **una sola transacción de base**:
1. Calcula las fechas debidas: ocurrencias desde `next_occurrence_date` hasta `local_today` (inclusive), aplicando el tope (D7).
2. **Compare-and-set del cursor**: `UPDATE recurring_transactions SET next_occurrence_date = :nuevo, last_occurrence_date = :ultima WHERE id = :id AND user_id = :uid AND status = 'active' AND next_occurrence_date = :viejo`. Si `rowcount != 1`, otro worker (o una edición) ganó: rollback y seguir.
3. Inserta una fila en `recurring_occurrences` por fecha y, si no requiere confirmación, la transacción correspondiente (vía un builder sin `commit` extraído de `FinanzasService.create_transaction`, que valida enums y categoría propia).
4. `commit`. Si algo falla (incluida una violación de la restricción única, que es la red de seguridad si dos caminos calcularon el mismo día), se revierte todo —cursor incluido— y el próximo ciclo reintenta.

Resultado: exactamente una transacción/pendiente por (recurrencia, fecha), con Postgres o SQLite, con o sin Redis, ante reinicios a mitad de ciclo (nada queda a medias). Redis (`claim_once`) **no es necesario**; no se usa para no sumar una capa que acá no decide nada. La push se arma con lo que este worker efectivamente commiteó (D9), así tampoco se duplica.

Las ediciones (`PUT`) que recalculan el cursor cambian `next_occurrence_date`, por lo que un ciclo concurrente con el valor viejo pierde el CAS. Si aun así dos caminos llegaran a la misma fecha, la restricción única lo corta.

### D6. Montos variables: pendientes y confirmación

- `requires_confirmation = true` → en vez de transacción se crea una ocurrencia `pending` con `suggested_amount` = monto de la **última ocurrencia confirmada** de esa recurrencia o, si no hay, `amount` de la plantilla (puede ser null). Los pendientes no afectan balance ni presupuestos.
- `POST /finance/recurring/occurrences/{id}/confirm` `{amount, transaction_date?, notes?, timezone_offset_minutes?}`: `UPDATE ... SET status='confirmed' WHERE id AND user_id AND status='pending'`; con `rowcount == 1` crea la transacción (fecha por defecto `occurrence_date`) y guarda `transaction_id`, todo en una transacción. Repetir la confirmación (cola offline que reintenta) devuelve 200 con la misma ocurrencia y su transacción, sin crear otra; confirmar una salteada → 409.
- `POST .../skip`: `pending → skipped` (repetirlo → 200; saltear una confirmada → 409).
- Los pendientes no vencen ni se auto-saltean (ver Preguntas abiertas). Si se borra la plantilla, sus pendientes se borran con ella (nunca fueron transacciones).

### D7. Recuperación de atrasadas con tope y "registrar las anteriores"

- **Server caído**: se generan las ocurrencias con fecha en `[local_today − 62 días, local_today]`, hasta 62 por recurrencia y ciclo. Las más viejas que eso se saltean avanzando el cursor (se loguea con warning y el id). 62 días cubre dos meses de caída sin inundar el historial con una diaria.
- **Crear con fecha de inicio pasada**: por defecto no se registra el pasado: `anchor`/cursor arrancan en la primera ocurrencia ≥ `max(start_date, hoy local)`. Con `generate_past = true` se registran las ocurrencias desde `start_date` (que debe ser ≥ hoy − 366 días) hasta hoy; si superan 120 → 422 "Son demasiados movimientos para registrar de una vez (máx. 120)". Explícito en vez de truncar en silencio.

### D8. Ciclo de vida: pausar, reanudar, editar, borrar, terminar

- **Pausar** (`POST /{id}/pause`): `status = paused`, `paused_at = now`. El scheduler la ignora.
- **Reanudar** (`POST /{id}/resume`): `status = active`, cursor = primera ocurrencia ≥ hoy local; **las fechas que cayeron durante la pausa no se generan** (pausar = "este mes no se cobró"). Lo de hoy, si corresponde, se materializa en el acto.
- **Editar** (`PUT /{id}`, parcial, `exclude_unset`): nunca toca transacciones ya generadas ni pendientes existentes (estos conservan su `suggested_amount`). Campos "de contenido" (monto, nombre, categoría, cuenta, medio de pago, notas, `requires_confirmation`, `notify`) aplican desde la próxima ocurrencia. Si cambia la **regla** (`frequency`, `interval_count`, `weekday`, `day_of_month`, `month_of_year`, `start_date`): `anchor_date` = primera ocurrencia de la regla nueva ≥ `max(start_date, hoy local, last_occurrence_date + 1)` y el cursor pasa a esa fecha. La UI muestra la vista previa con las próximas fechas antes de guardar para que el usuario vea, por ejemplo, que pasar del 5 al 10 después de registrado el del 5 genera también el 10 de este mes. Cambiar `end_date` solo recorta o extiende (si estaba terminada y la nueva fecha fin lo permite, el cursor se recalcula desde `last_occurrence_date`).
- **Borrar** (`DELETE /{id}`): borra la plantilla y sus ocurrencias; las transacciones generadas **se conservan** con `is_recurring = true` y `recurring_parent_id = NULL` (se desvinculan a mano, mismo patrón que categorías). En la UI quedan como "Generada por una recurrencia eliminada".
- **Terminar**: cuando la siguiente ocurrencia supera `end_date`, el cursor queda null; la lista la muestra como "Finalizada". Editar `end_date` la puede revivir.
- **Borrar una transacción generada** (borrado lógico): la ocurrencia sigue registrada, así que **no se vuelve a generar** (borrarla es una decisión del usuario). Editarla no toca la plantilla.
- **Borrar categoría o cuenta**: `CategoryRepository.delete` y `BankAccountRepository.delete` suman `UPDATE recurring_transactions SET category_id/bank_account_id = NULL` (las FK no tienen `ON DELETE`).
- **Cuenta en la transacción generada**: si hay `bank_account_id` (y sigue siendo del usuario) se copian `bank_entity_name = bank_name or name`, `account_type`, `account_last4 = last4`; si no, `account_type` de la plantilla y textos vacíos.

### D9. Push (`recurrentes/notifications.py`)

- Por recurrencia, `notify` (default true). Se mandan **después del commit**, solo por lo que ese worker generó, una push por usuario y ciclo:
  - 1 transacción automática: título `Se registró: {name}`, cuerpo `{Ingreso|Gasto} de $ 850.000,00 ARS{ en Banco X}.` `data = {type: "recurring_generated", recurrence_id, transaction_id}`.
  - 1 pendiente: `Confirmá el monto: {name}`, cuerpo `Estimado $ 25.000,00 ARS. Tocá para confirmarlo o editarlo.` (sin estimado: `Tocá para cargar el monto.`). `data = {type: "recurring_confirm", occurrence_id, recurrence_id}`.
  - Varias: `Movimientos recurrentes`, cuerpo `Se registraron 3 movimientos y tenés 1 para confirmar.` `data = {type: "recurring_summary"}`.
- Formato de montos con `format_money_es_ar` de `inversiones/valuation.py` (se mueve o reexporta a un helper común si hace falta). Canal Android `recordatorios` (lo pone `PushService`). Errores de Expo se loguean y no afectan lo generado (la push es at-most-once; la transacción es exactly-once).
- Las materializaciones disparadas por la API no mandan push.

### D10. API de recurrentes

Router `prefix="/finance/recurring"`, `tags=["finance"]`, todas con `get_current_user`, sin `require_module` (Finanzas es base). Rutas estáticas antes de `/{id}`. Un id ajeno → 404.

| Método | Ruta | Request | Response |
|---|---|---|---|
| GET | `/finance/recurring` | `status=active\|paused\|all` (default `all`), `tz_offset_minutes?` | `RecurringOut[]` (activas primero, por `next_occurrence_date`, nombre) |
| POST | `/finance/recurring` | `RecurringCreate` (+ `generate_past`, `timezone_offset_minutes`) | 201 `RecurringOut` |
| POST | `/finance/recurring/preview` | regla + `start_date`/`end_date` + `tz_offset_minutes` | `{dates: date[5], anchor_date}` |
| GET | `/finance/recurring/upcoming` | `days` 1–90 (default 30), `tz_offset_minutes?` | `[{recurrence_id, date, name, type, amount, currency, requires_confirmation}]` + totales por tipo/moneda |
| GET | `/finance/recurring/occurrences` | `status=pending\|all` (default `pending`) | `OccurrenceOut[]` (con nombre/tipo de la recurrencia) |
| POST | `/finance/recurring/occurrences/{id}/confirm` | `{amount, transaction_date?, notes?, timezone_offset_minutes?}` | `OccurrenceOut` (+ `transaction`) |
| POST | `/finance/recurring/occurrences/{id}/skip` | `{timezone_offset_minutes?}` | `OccurrenceOut` |
| GET | `/finance/recurring/{id}` | `tz_offset_minutes?` | `RecurringOut` + `recent_occurrences` (≤ 12) + `next_dates` (3) |
| PUT | `/finance/recurring/{id}` | `RecurringUpdate` (parcial; null en obligatorio se ignora) | `RecurringOut` |
| DELETE | `/finance/recurring/{id}` | — | 204 |
| POST | `/finance/recurring/{id}/pause` · `/resume` | `{timezone_offset_minutes?}` | `RecurringOut` |
| GET | `/finance/transactions` | + `recurrence_id?` | `TransactionResponse` + `recurrence_id` |

- `RecurringOut`: columnas (sin internos) + `state` (`active|paused|finished`), `rule_label` en español ("Todos los meses el día 5", "Cada 2 meses el día 10", "Todas las semanas los lunes", "Cada 15 días", "Todos los años el 15/03", sufijo "(o el último día del mes)" para día > 28), `pending_count`, `last_amount` (última confirmada/generada).
- Validación: `amount` con `Money` y > 0 (o null si confirma), `name` 1–255 (trim), enums de `type`/`account_type`/`payment_method`/`merchant_category` reusando `_check_enum` de `finanzas/schemas.py`, fechas 1970–2100, `timezone_offset_minutes` −840..840, `category_id`/`bank_account_id` propios (404 si no). Errores 422 en español.

### D11. Renovar plazo fijo

**Modelo**: `investments.renewed_from_id String(36) NULL FK investments.id` con **índice único** (varios NULL permitidos en SQLite y Postgres): una inversión se renueva una sola vez, lo que hace idempotente la renovación ante reintentos de la cola offline (el segundo intento → 409 "Este plazo fijo ya se renovó"). `InvestmentOut` suma `renewed_from_id`, `renewed_to_id` (calculado con una query por lista) y `can_renew`.

**`POST /finance/investments/{id}/renew`** (`RenewFixedTermIn`):
- `mode`: `principal_and_interest` (reinvertir capital + interés) | `principal_only` (reinvertir el capital, retirar el interés).
- `interest_rate_tna` (> 0, ≤ 999,9999; la UI precarga la anterior), y `term_days` (1–3650) **o** `maturity_date` (si vienen los dos deben coincidir).
- `start_date?`: default hoy local; debe estar entre el vencimiento anterior y hoy local (renovar tarde = la plata no estuvo invertida esos días).
- `amount_collected?`: default `amount_at_maturity` calculado; editable porque el banco puede acreditar algo distinto (redondeos). Debe ser ≥ `invested_amount` anterior en `principal_only` (interés ≥ 0) y ≤ `Money`.
- `register_interest_income` (default false, solo `principal_only`), `income_category_id?`, `income_bank_account_id?`, `income_payment_method` (default `transfer`), `timezone_offset_minutes?`.
- Precondiciones: `asset_type = fixed_term`, `status = active`, `days_to_maturity <= 0` en la fecha local (vence hoy o ya venció), sin renovación previa. Si no → 422/409 en español.
- **Efecto atómico** (una transacción): el anterior pasa a `closed` con `current_value = amount_collected` (queda en el historial lo que pagó, no suma por estar cerrado); se crea el nuevo `fixed_term` copiando `name`, `institution`, `currency`, `notes`, `notify_maturity`, offset, con `invested_amount = amount_collected` (modo 1) o el capital anterior (modo 2), nueva TNA, `start_date`, `maturity_date`, `renewed_from_id`, marcas de aviso en null. En modo 2 con `register_interest_income`, se crea una transacción `income` por el interés (`product_name = "Interés plazo fijo: {name}"`, fecha `start_date`, categoría/cuenta elegidas). Respuesta `{closed, renewed, interest_transaction_id}`.
- **Historial**: `GET /finance/investments/{id}/renewals` devuelve la cadena completa (hacia atrás por `renewed_from_id` y hacia adelante), ordenada de la más vieja a la más nueva, tope 100, con fechas, capital, TNA e interés de cada tramo y el interés acumulado.
- **Consistencia**: reabrir una inversión que ya tiene renovación → 422 (sumaría dos veces); borrar la renovación deja el anterior cerrado (se puede reabrir); borrar el anterior desvincula `renewed_from_id` del nuevo (a mano, como el resto). Los avisos de vencimiento del anterior se apagan solos al cerrarse; el nuevo los recibe.

### D12. Export y borrado de cuenta

`OWNED_TABLES` suma, **antes** de `categories` y `bank_accounts` (por las FK) y después de `transactions` (que ya va primero): `("recurring_occurrences", RecurringOccurrence)` y luego `("recurring_transactions", RecurringTransaction)`. `investments` (FK a sí misma) se borra en un único `DELETE ... WHERE user_id` (Postgres verifica la FK al final de la sentencia; se prueba en Postgres). La guarda de `test_account.py` falla si se olvida.

### D13. Migración `019_recurring_transactions`

`down_revision = "018_investments"`. `create_table` de las dos tablas con checks, índices y la única; `create_index ix_transactions_recurring_parent_id`; `add_column investments.renewed_from_id` + FK + índice único (con `batch_alter_table` para SQLite). `downgrade` inverso. Verificar `alembic heads` = un solo head y `upgrade/downgrade/upgrade` en SQLite **y** Postgres (PGlite vía npm, como en `finanzas-inversiones`).

### D14. Web (`frontend/`)

- `src/types`: `Recurring`, `RecurringInput`, `RecurringRule`, `Occurrence`, `UpcomingItem`, `RenewFixedTermInput`, `RenewalChain`; `Transaction` suma `recurrence_id?`; `Investment` suma `renewed_from_id?`, `renewed_to_id?`, `can_renew?`.
- `src/api/endpoints.ts`: `fetchRecurring`, `fetchRecurringOne`, `createRecurring`, `updateRecurring`, `deleteRecurring`, `pauseRecurring`, `resumeRecurring`, `previewRecurring`, `fetchUpcomingRecurring`, `fetchOccurrences`, `confirmOccurrence`, `skipOccurrence`, `renewInvestment`, `fetchRenewals`; lecturas con `tz_offset_minutes: tzOffsetMinutes()`, escrituras con `timezone_offset_minutes`; mocks con las mismas formas.
- `src/hooks/useRecurring.ts`: SWR (`finance/recurring*`, `finance/recurring/occurrences`, `finance/recurring/upcoming`); toda mutación revalida esas keys y, si creó transacciones (crear con pasado, reanudar, confirmar), también `finance/transactions*`, `finance/summary`, `finance/budgets` y `finance/reports`. Renovar revalida inversiones, net-worth, summary y transacciones.
- `FinancePage.tsx`: pestaña `recurrentes` ("Recurrentes") → `RecurringSection.tsx`: tarjeta "Para confirmar" con los pendientes (botones Confirmar/Saltear → `ConfirmOccurrenceModal`), resumen "Próximos 30 días: +$ / −$", lista de plantillas (nombre, tipo en verde/rojo, monto o "Monto variable", `rule_label`, próxima fecha, cuenta/categoría, chip Activa/Pausada/Finalizada, acciones editar/pausar-reanudar/ver movimientos/borrar con confirmación "Las transacciones ya registradas se conservan"), estado vacío con ejemplos (sueldo, alquiler, Netflix).
- `RecurringModal.tsx` (RHF + Zod sin `z.coerce`, patrón `TransactionModal`): tipo, nombre, monto (coma decimal; opcional si "Confirmar el monto antes de registrar"), moneda, categoría, cuenta, medio de pago, frecuencia con campos según tipo (cada N, día de la semana, día del mes con ayuda "si el mes es más corto, el último día", mes), inicio, fin opcional, switches "Confirmar el monto antes de registrar", "Avisarme" y "Registrar también los anteriores" (solo con inicio pasado), y **vista previa** de las próximas 5 fechas (llamada a `/preview` con debounce de 400 ms).
- Banner en la pestaña Transacciones si hay pendientes; badge "Recurrente" (ícono repetir) en `TransactionTable` para `is_recurring`, con link a la plantilla; acción "Hacer recurrente" en una transacción que abre `RecurringModal` precargado.
- `InvestmentsSection.tsx`: botón "Renovar" en plazos fijos con `can_renew`; `RenewFixedTermModal.tsx` con monto cobrado editable, radios de modo (mostrando capital, interés y nuevo capital), checkbox "Registrar el interés como ingreso" (categoría/cuenta), TNA, plazo (chips 30/60/90/180/365 o fecha), inicio, vista previa del nuevo interés y monto al vencimiento; "Historial de renovaciones" en el detalle.

### D15. Mobile (`C:\Proyectos\vida-personal-mobile`)

- `src/types`, `src/api/endpoints.ts` (escrituras con `queued('...')`, `timezone_offset_minutes: -new Date().getTimezoneOffset()`; `preview` y `upcoming` solo online), `src/hooks/useRecurring.ts`.
- `src/screens/RecurringScreen.tsx` en `FinanceStack` (`FinanceStackParamList.Recurring: { create?: true; occurrenceId?: string } | undefined`): sección "Para confirmar", próximos 30 días, `SectionList` Activas / Pausadas / Finalizadas, alta/edición en `RecurringFormSheet` (`BottomSheet` con `PickerField` frecuencia/tipo/cuenta/categoría, `NumberStepper` para "cada N" y día del mes, `FilterChips` para día de la semana, `DateField` inicio/fin, `Switch` confirmación/aviso/anteriores, vista previa si hay red), `ConfirmOccurrenceSheet` (monto con `decimal-pad` + `parseDecimal`, fecha), pausar/reanudar/borrar con `Alert`.
- `FinanceScreen.tsx`: tile "Recurrentes" (`repeat`) en `TOOLS` (5 tiles: `TOOL_ROWS` ya pone el último a lo ancho) y aviso "Tenés N movimientos para confirmar" que abre Recurrentes.
- `QuickCreateSheet.tsx`: `{ key: 'recurring', label: 'Recurrente', icon: 'repeat', tab: 'FinanceTab', screen: 'Recurring', create: true }`; `useCreateParam` abre el sheet.
- `src/lib/notifications.ts`: `targetFromData` suma `recurring_generated` / `recurring_summary` → Recurrentes y `recurring_confirm` → Recurrentes con `occurrenceId` (abre `ConfirmOccurrenceSheet`).
- Inversiones: "Renovar" en la tarjeta/`InvestmentFormSheet` de un plazo fijo con `can_renew` → `RenewFixedTermSheet` (mismos campos que la web) e historial de renovaciones.
- Sin textos de compra ni precios (regla de Play).

## Risks / Trade-offs

- [Offset guardado por recurrencia queda viejo tras un viaje] → mismo trade-off aceptado en recordatorios e inversiones; se corrige en cada escritura y la ventana 9–22 tolera corrimientos de pocas horas. Si `habitos-recordatorios-inteligentes` agrega un huso a nivel usuario, se usa como fallback antes de −180.
- [Generar a las 09:00 hace que entre 00:00 y 09:00 el balance del día no incluya el sueldo] → aceptable; la transacción queda con la fecha correcta. Alternativa (medianoche) contradice no mandar push de madrugada.
- [Cambiar la regla después de una ocurrencia puede generar dos en el mismo mes] → vista previa obligatoria en la UI antes de guardar; documentado.
- [Caída de más de 62 días pierde ocurrencias] → warning en logs; caso extremo.
- [Los pendientes se acumulan si el usuario los ignora] → aviso visible en Finanzas y en la push; auto-saltear queda como pregunta abierta.
- [La push es at-most-once] → la transacción/pendiente ya está registrada; la app muestra el aviso de pendientes igual.
- [Edición concurrente con el scheduler] → CAS del cursor + restricción única; en el peor caso se pierde una edición de cursor, nunca se duplica una ocurrencia.
- [SQLite no aplica FKs ni longitudes] → desvinculación manual en borrados, tests de bordes 422 (no 500), migración y flujo completo verificados en Postgres.
- [Renovar con `amount_collected` editado distinto del calculado] → se muestra la diferencia y se valida interés ≥ 0 en `principal_only`.
- [Un loop más por worker] → query indexada; costo despreciable.

## Migration Plan

1. Deploy backend con `019_recurring_transactions` (`alembic upgrade head` en el entrypoint). Cambios aditivos: clientes viejos ignoran `recurrence_id`, `renewed_*` y `can_renew`.
2. Deploy web.
3. Build EAS mobile. Hasta que se instale, las recurrencias creadas desde la web funcionan igual (generación en el server; las push llegan a la app vieja y solo la abren).
4. Rollback: `alembic downgrade 018_investments` borra las tablas nuevas, el índice y `renewed_from_id` (las transacciones ya generadas quedan como transacciones normales con `is_recurring = true`); revertir el deploy quita el scheduler.

## Dependencias

- **`finanzas-inversiones`** (requerido): la renovación usa `Investment`, `valuation.py` y la UI de Inversiones de ese change (código ya en la rama). Conviene archivarlo antes que este para que exista la spec `finance-investments`; este change no modifica sus requisitos (agrega la capability `fixed-term-renewal`) y resuelve su pregunta abierta 4.
- **Numeración de migraciones**: si otro change hermano (`finanzas-exportar-importar`, `habitos-recordatorios-inteligentes`, `registro-edad-minima`, etc.) aterriza antes una `019_*`, esta se renumera y ajusta `down_revision` al implementar; siempre un solo head.
- **`finanzas-exportar-importar`**: su export de transacciones debería incluir `is_recurring`/`recurrence_id` como columnas informativas, y el import nunca debe setearlas ni crear recurrencias. El export de cuenta (JSON por `OWNED_TABLES`) incluye las tablas nuevas automáticamente.
- **`habitos-recordatorios-inteligentes`**: si introduce un huso horario por usuario, este change lo usa como fallback (D4); si toca `PushService` o el canal, las push de recurrentes lo heredan.
- **`widgets-android`** y **`buscador-global`**: pueden consumir `GET /finance/recurring/occurrences?status=pending` / `upcoming` o indexar plantillas por nombre; no es dependencia de este change.
- **`finanzas-datos-mercado`**: si trae TNA de referencia, el modal de renovación podría sugerirla; opcional, fuera de este change.

## Open Questions

1. **Hora de generación**: 09:00 local (ventana 9–22, como vencimientos) vs medianoche. Recomendación: 09:00.
2. **Tope de recuperación**: 62 días / 62 ocurrencias por ciclo tras una caída, y máximo 120 al "registrar los anteriores" (inicio hasta 1 año atrás). Recomendación: esos valores.
3. **Reanudar**: no generar lo que cayó durante la pausa (vs ofrecer "registrar lo pausado"). Recomendación: no generar.
4. **Push por defecto**: `notify = true` en todas (vs solo en las que piden confirmación). Recomendación: true, desactivable por recurrencia.
5. **Monto sugerido de un pendiente**: último monto confirmado de esa recurrencia (vs siempre el de la plantilla). Recomendación: último confirmado, cayendo al de la plantilla.
6. **Pendientes sin confirmar**: no vencen (vs auto-saltear a los 30 días). Recomendación: no vencen.
7. **Moneda de las recurrentes**: ARS y USD como en transacciones (el balance sigue sin convertir monedas). Recomendación: permitir ambas, default ARS.
8. **Renovación**: solo el día del vencimiento o después (no precancelación); fecha de inicio por defecto hoy (mínimo el vencimiento anterior). Recomendación: así.
9. **Interés como ingreso en `principal_only`**: checkbox apagado por defecto (vs prendido). Recomendación: apagado, porque muchos ya registran la acreditación a mano.
