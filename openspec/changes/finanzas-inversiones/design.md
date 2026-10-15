## Context

- **Finanzas hoy**: `backend/app/api/v1/finance.py` expone `/finance/summary` (ingresos, egresos y `balance` = ingresos − egresos de todas las transacciones, sin mirar moneda: en la práctica se asume ARS), transacciones, categorías, presupuestos, reportes y cuentas (`bank_accounts`). La lógica vive en `backend/app/modules/finanzas/` (service + repository). Los montos son `Numeric(12,2)` con el tipo `Money` acotado a ±9.999.999.999,99 en `finanzas/schemas.py` (un monto fuera de rango daba 500 en Postgres, ver commit `bae6c4f`).
- **Módulos nuevos** (vehiculo, viajes, proyectos…) siguen el patrón `models.py` / `service.py` / `api_routes.py` con el router incluido en `backend/app/api/v1/router.py`. Finanzas es plantilla base (`MODULE_REGISTRY`, `is_base=True`): sus rutas no llevan `require_module`.
- **Push**: `backend/app/modules/push/service.py` (`PushService.send_to_user`, canal Android `recordatorios`, nunca levanta excepción, limpia tokens `DeviceNotRegistered`). El scheduler de recordatorios (`backend/app/modules/recordatorios/scheduler.py`) corre un loop por worker arrancado en el `lifespan` de `backend/app/main.py`, deduplica con un dict en memoria + `SET NX` en Redis (`reminder-fired:{id}:{fecha_local}`, TTL 36 h) y usa `timezone_offset_minutes` (minutos al este de UTC, Buenos Aires = −180) que el cliente manda en cada create/update.
- **Preferencias**: `user_preferences` (`backend/app/modules/ajustes/models.py`, una fila por usuario) expuesta por `GET/PUT /api/v1/settings` (`backend/app/api/v1/settings.py`), que crea la fila si no existe.
- **Guardas existentes**: `test_account.py::test_owned_tables_cubre_todos_los_modelos_con_user_id` (toda tabla con `user_id` debe estar en `OWNED_TABLES`), `test_infra.py::test_no_api_route_is_public_by_accident`, `test_tenant_isolation.py`.
- **Base de datos**: tests en SQLite, producción en Postgres (asyncpg). Hubo bugs por tipos (fechas como texto en `transactions`, ver `IsoText`). Migraciones Alembic en `backend/migrations/versions/`, head actual `017_withdrawal_requests`.
- **Clientes**: web `frontend/` (React 19, SWR, RHF + Zod sin `z.coerce`, `src/api/endpoints.ts` con modo mock, `tzOffsetMinutes()` ya existe); mobile `C:\Proyectos\vida-personal-mobile` (Expo SDK 57, `BottomSheet`, `DateField`, `PickerField`, `parseDecimal`, `queued(...)` para escrituras offline, grilla `TOOLS` 2×2 en `FinanceScreen`, `QuickCreateSheet`, `BalanceCard`).

## Goals / Non-Goals

**Goals:**
- Registrar activos de inversión por usuario con aislamiento por tenant, límites de monto y compatibilidad Postgres.
- Valuación manual con cálculo automático de plazo fijo (interés simple TNA/365) y un punto de extensión limpio para cotizaciones futuras.
- Totales en ARS y USD con la cotización que carga el usuario; degradar a subtotales por moneda si falta.
- Patrimonio = balance disponible + inversiones; preferencia "Sumar inversiones al balance" con presentación diferenciada.
- Push el día anterior y el día del vencimiento a las 9:00 locales, sin duplicados entre workers ni reinicios.
- Export/borrado de cuenta cubriendo la tabla nueva.

**Non-Goals:**
- Cotizaciones en vivo, impuestos, historial de compras/ventas (ver proposal).
- Cambiar el significado de `balance` en `/finance/summary` ni convertir monedas del balance de transacciones.
- Horario/anticipación configurables para los avisos.
- Generar transacciones automáticas al constituir o cobrar una inversión.

## Decisions

### D1. Módulo nuevo `inversiones`, rutas bajo `/api/v1/finance/investments`

`backend/app/modules/inversiones/` con `models.py`, `schemas.py`, `repository.py`, `service.py`, `valuation.py`, `scheduler.py`, `api_routes.py`. El router (`prefix="/finance/investments"`, `tags=["finance"]`) se incluye en `router.py`. Todas las rutas dependen de `get_current_user` (sin `require_module`: es parte de Finanzas base).

*Alternativa*: meterlo en `modules/finanzas/` y `api/v1/finance.py`. Descartada: ese archivo ya es grande y mezclar el scheduler y la valuación con transacciones complica el mantenimiento; el patrón de módulo propio es el que siguen los módulos recientes.

### D2. Modelo de datos: una tabla `investments` (posición, sin movimientos)

| Columna | Tipo | Null | Notas |
|---|---|---|---|
| `id` | `String(36)` PK | no | uuid4 |
| `user_id` | `String(36)` FK `users.id` | no | index |
| `asset_type` | `String(20)` | no | `stock`, `fixed_term`, `crypto`, `bond`, `fund`, `fx`, `real_estate`, `vehicle`, `other` |
| `name` | `String(120)` | no | |
| `ticker` | `String(20)` | sí | mayúsculas, `^[A-Z0-9.\-]{1,20}$` |
| `currency` | `String(5)` | no | `ARS`, `USD`, `USDT`, `EUR` (USDT tiene 4 letras: no entra en el `String(3)` del resto de finanzas) |
| `quantity` | `Numeric(20,8)` | sí | unidades (acciones, cripto con 8 decimales, USD billete) |
| `invested_amount` | `Numeric(12,2)` | no | ≥ 0 |
| `current_value` | `Numeric(12,2)` | sí | valor manual; null = calcular (D4) |
| `interest_rate_tna` | `Numeric(7,4)` | sí | % anual, 0–999,9999 (TNA argentinas superaron 100 %) |
| `start_date` | `Date` | sí | obligatoria en `fixed_term` |
| `maturity_date` | `Date` | sí | obligatoria en `fixed_term` |
| `institution` | `String(120)` | sí | banco/broker/exchange |
| `notes` | `Text` | sí | ≤ 2000 en schema |
| `status` | `String(10)` | no | `active` (default) / `closed` |
| `notify_maturity` | `Boolean` | no | default true |
| `timezone_offset_minutes` | `Integer` | sí | minutos al este de UTC, lo manda el cliente (D8) |
| `price_source` | `String(20)` | no | default `manual` (D5) |
| `last_price` | `Numeric(20,8)` | sí | precio unitario del proveedor (futuro) |
| `last_price_at` | `DateTime(timezone=True)` | sí | |
| `value_updated_at` | `DateTime(timezone=True)` | sí | se setea cuando cambia `current_value` |
| `eve_notice_for` | `Date` | sí | vencimiento para el que ya se mandó el aviso "mañana" (D8) |
| `day_notice_for` | `Date` | sí | idem aviso "hoy" |
| `created_at`, `updated_at` | `DateTime(timezone=True)` | no | `server_default=func.now()` |

- Índices: `ix_investments_user_id`, `ix_investments_user_status (user_id, status)`, `ix_investments_status_maturity (status, maturity_date)` para el scheduler.
- Checks (válidos en SQLite y Postgres): `invested_amount >= 0`, `current_value IS NULL OR current_value >= 0`, `quantity IS NULL OR quantity >= 0`, `interest_rate_tna IS NULL OR interest_rate_tna >= 0`, `start_date IS NULL OR maturity_date IS NULL OR maturity_date >= start_date`, `status IN ('active','closed')`. El `asset_type` y la moneda se validan en el schema (no en la DB) para poder sumar tipos sin migrar.
- Fechas como `Date` real y timestamps tz-aware (no repetir el `String(10)` de `transactions`).
- **Sin tabla de movimientos** (justificado en la proposal). Si se agrega, será `investment_movements` hija con FK a `investments` y la posición quedaría como agregado; `investments` no cambia.

*Alternativa*: reutilizar `bank_accounts` con `account_type="investment"`. Descartada: no tiene fechas, tasa, ticker ni valor actual separado del invertido.

### D3. Preferencias: cotización y toggle en `user_preferences`

Columnas nuevas: `fx_usd_ars Numeric(14,4) NULL`, `fx_eur_ars Numeric(14,4) NULL`, `fx_rates_updated_at DateTime(tz) NULL`, `include_investments_in_balance Boolean NOT NULL server_default false`.

`GET/PUT /api/v1/settings` suma esos campos. Validación en `SettingsUpdate`: cotizaciones `Decimal` con `gt=0`, `le=9999999.9999`, `decimal_places=4`, null permitido para borrarlas. El server setea `fx_rates_updated_at = now(UTC)` cuando alguna cotización cambia (el cliente no lo manda). Una sola cotización por par: no se guarda historial.

*Alternativa*: tabla `fx_rates` con historial. Descartada para esta etapa: el usuario pidió "la cotización que yo cargo"; un historial solo sirve con cotizaciones automáticas.

### D4. Valuación efectiva y plazo fijo

`valuation.effective_value(inv, today) -> (Decimal, value_source)` con este orden:
1. `price_source != "manual"` y `last_price` y `quantity` → `quantity × last_price` (`quote`). Hoy nunca se da (D5).
2. `current_value` no nulo → `current_value` (`manual`).
3. `fixed_term` con TNA y fechas → `invested_amount + accrued(today)` (`fixed_term_accrued`).
4. Si no → `invested_amount` (`invested`).

Fórmulas de plazo fijo (interés simple, convención argentina base 365, `P` = `invested_amount`, `r` = TNA %):
- `term_days = (maturity_date − start_date).days` (debe ser ≥ 1 para `fixed_term`)
- `interest_total = round2(P × r/100 × term_days/365)`
- `amount_at_maturity = P + interest_total`
- `elapsed = clamp((today − start_date).days, 0, term_days)`; `accrued_interest = round2(P × r/100 × elapsed/365)`
- `tea_pct = round2(((1 + r/100 × term_days/365)^(365/term_days) − 1) × 100)` — informativa.
- Ejemplo: P = 1.000.000, TNA 30 %, 30 días → interés 24.657,53; al vencimiento 1.024.657,53; TEA 34,50 %. A los 12 días el devengado es 9.863,01.

Derivados por activo: `gain = effective_value − invested_amount`; `gain_pct = round2(gain / invested_amount × 100)` (null si invertido = 0); `days_to_maturity = (maturity_date − today).days` (null sin vencimiento, 0 si vence hoy, negativo si venció); `is_matured = days_to_maturity is not None and days_to_maturity < 0`.

**"Hoy" del usuario**: los GET aceptan `tz_offset_minutes` (query, −840..840, default 0), igual que `/focus/summary` y los resúmenes arreglados en `4dd57a3`; `today = (now_utc + offset).date()`. Los clientes ya tienen `tzOffsetMinutes()`.

**Redondeo**: todo en `Decimal`, `ROUND_HALF_UP` a 2 decimales en cada monto que sale de la API; nunca `float` para dinero (la TEA, informativa, puede calcularse con `float` y cuantizarse). SQLite devuelve `float` en `Numeric`: convertir con `Decimal(str(x))` al leer (mismo cuidado que `cuenta/service.py::_serialize_value`).

### D5. Punto de extensión para cotizaciones

`valuation.py` define:
```python
class PriceQuote(NamedTuple):
    price: Decimal; currency: str; as_of: datetime

class PriceProvider(Protocol):
    key: str                      # "coingecko", "byma", ...
    supported_types: frozenset[str]
    async def quote(self, ticker: str, currency: str) -> PriceQuote | None: ...

PRICE_PROVIDERS: dict[str, PriceProvider] = {}   # vacío en esta etapa

async def refresh_quotes(db, user_id) -> int:     # no-op hoy: devuelve 0
```
El schema acepta `price_source` solo en `{"manual"} ∪ PRICE_PROVIDERS.keys()` (hoy: solo `manual`). Agregar un proveedor = implementar la clase, registrarla y (más adelante) un job que llame `refresh_quotes`, que escribe `last_price`/`last_price_at`; la regla 1 de D4 ya lo usa. No hay llamadas HTTP externas en este change.

### D6. Conversión de moneda y totales

Factor a ARS por moneda: `ARS = 1`, `USD = USDT = fx_usd_ars`, `EUR = fx_eur_ars`. USDT se asume 1:1 con USD (documentado en la UI).

1. Se suman los valores efectivos (ya redondeados) por moneda → `by_currency[c] = {invested, current_value, gain}` exactos.
2. `total_ars = round2(Σ_c subtotal_c × factor_c)`, calculable solo si todas las monedas presentes tienen factor.
3. `total_usd = round2(Σ_c subtotal_c × factor_c / fx_usd_ars)`, con USD/USDT sumando su subtotal sin pasar por ARS (factor 1/1). Calculable si hay `fx_usd_ars` (o si solo hay USD/USDT) y las demás monedas presentes tienen factor.
4. Lo que no se pueda calcular sale `null` y `missing_rates` lista los pares faltantes (`["USD"]`, `["EUR"]`). La UI muestra los subtotales y un aviso "Cargá la cotización del dólar para ver el total".

Ejemplo: 500.000 ARS + 2.000 USD, `fx_usd_ars = 1450,50` → `total_ars = 3.401.000,00`, `total_usd = 2.344,71`.

### D7. Patrimonio y `/finance/summary`

- `balance` de `/finance/summary` **no cambia** (efectivo, se asume ARS). Campos nuevos aditivos: `investments_value_ars: Decimal | null`, `net_worth_ars: Decimal | null` (= `balance + investments_value_ars`), `include_investments_in_balance: bool`, `investments_missing_rates: list[str]`. Acepta `tz_offset_minutes` opcional (para el devengado de plazos fijos). Clientes viejos ignoran los campos nuevos.
- `GET /finance/net-worth?tz_offset_minutes=` devuelve el desglose completo: `cash_balance_ars`, `cash_balance_usd`, `investments` (= resumen de D6), `net_worth_ars`, `net_worth_usd`, `rates {usd_ars, eur_ars, updated_at}`, `missing_rates`, `include_investments_in_balance`.
- Solo cuentan activos `active`; los `closed` se listan aparte y no suman.
- Toggle ON: los clientes muestran `net_worth_ars` como número grande con dos tramos (efectivo / inversiones) en colores distintos y rótulo "Balance + inversiones"; OFF: igual que hoy. La decisión de presentación es del cliente; el server solo informa el flag y los montos.

*Alternativa*: que `balance` incluya las inversiones cuando el toggle está ON. Descartada: cambia el significado de un campo que usan widgets, reportes y clientes mobile viejos (rompería sin aviso).

### D8. Avisos de vencimiento

- **Cuándo**: a las 9:00 locales del día anterior (`eve`) y del día del vencimiento (`day`), para activos `active`, `notify_maturity = true`, con `maturity_date` (cualquier tipo, no solo plazo fijo). Ventana de envío 9:00–21:59 local: si el server estuvo caído a las 9, el aviso sale en el primer ciclo dentro de la ventana; después de las 22 ya no.
- **Huso horario**: `timezone_offset_minutes` en la fila, que el cliente manda en cada create/update (mismo patrón que `reminders`, se corrige solo al tocar el activo). Si es null (cliente viejo o API directa) se usa `DEFAULT_TZ_OFFSET_MINUTES = -180` (Argentina, mercado de la app) en vez de no avisar: a diferencia de los recordatorios, no hay programación local de respaldo en el dispositivo.
- **Loop**: `run_investment_alert_scheduler()` arrancado en el `lifespan` junto al de recordatorios (y cancelado al apagar), ciclo alineado al minuto. Query barata: `status='active' AND notify_maturity AND maturity_date BETWEEN utc_today-1 AND utc_today+2` (usa `ix_investments_status_maturity`).
- **Dedup en tres capas**:
  1. Set en memoria `(id, kind, maturity_date)` (evita reprocesar en cada minuto del mismo proceso; se poda lo anterior a ayer).
  2. `SET NX` en Redis `investment-maturity:{id}:{kind}:{maturity_iso}` TTL 36 h (decisión del usuario, igual que recordatorios). El helper `_claim_in_redis` se extrae a `backend/app/core/redis_claim.py::claim_once(key, ttl)` y lo usan los dos schedulers (el de recordatorios conserva su función como wrapper para no romper tests). Sin Redis o con Redis caído devuelve True, como hoy.
  3. Marca persistente: `UPDATE investments SET eve_notice_for = :m WHERE id = :id AND (eve_notice_for IS NULL OR eve_notice_for <> :m)`; solo si `rowcount == 1` se manda. Es atómico en Postgres, cubre reinicios del proceso y despliegues sin Redis (donde con la ventana 9–22 la capa 1 sola reenviaría tras un reinicio). Guardar la fecha de vencimiento (no un booleano) hace que cambiar el vencimiento rehabilite los avisos sin resetear nada.
  - Semántica *at-most-once*: la marca se escribe antes de mandar; si Expo falla el aviso se pierde (igual que recordatorios; `send_to_user` ya loguea).
- **Contenido** (es-AR): título `Vence mañana: {name}` / `Vence hoy: {name}`; cuerpo para plazo fijo `Tu plazo fijo{ en institution} cobra $ 1.024.657,53 ARS.`; otros tipos `{name} vence {mañana|hoy}.` `data = {"type": "investment_maturity", "investment_id": id}`; canal `recordatorios` (lo pone `PushService`).

*Alternativa*: disparo exacto al minuto 9:00 como los recordatorios. Descartada: un reinicio o un ciclo atrasado justo a las 9 hace perder el aviso; con la ventana + marca persistente se garantiza uno y solo uno.

### D9. API

Todas bajo `/api/v1`, autenticadas, filtradas por `user_id` en el repository; un id de otro usuario responde 404.

| Método | Ruta | Request | Response |
|---|---|---|---|
| GET | `/finance/investments` | query `status=active\|closed\|all` (default `active`), `asset_type?`, `tz_offset_minutes?` | `InvestmentOut[]` ordenado por tipo, vencimiento asc (nulls al final), nombre |
| GET | `/finance/investments/summary` | `tz_offset_minutes?` | `InvestmentSummary` |
| GET | `/finance/investments/{id}` | `tz_offset_minutes?` | `InvestmentOut` |
| POST | `/finance/investments` | `InvestmentCreate` | 201 `InvestmentOut` |
| PUT | `/finance/investments/{id}` | `InvestmentUpdate` (parcial, `exclude_unset`; null en campo obligatorio se ignora; mismo verbo que el resto de `/finance`) | `InvestmentOut` |
| DELETE | `/finance/investments/{id}` | — | 204 |
| GET | `/finance/net-worth` | `tz_offset_minutes?` | `NetWorthOut` |
| GET/PUT | `/settings` | + `fx_usd_ars`, `fx_eur_ars`, `include_investments_in_balance` | + esos campos y `fx_rates_updated_at` |
| GET | `/finance/summary` | + `tz_offset_minutes?` | + campos de D7 |

`/summary` se declara antes de `/{id}`.

- `InvestmentCreate`: `asset_type` (enum), `name` 1–120 (trim), `ticker?`, `currency` (enum), `quantity?` (`ge=0`, `le=999999999999`, `decimal_places=8`), `invested_amount` (`Money` ≥ 0), `current_value?` (`Money` ≥ 0), `interest_rate_tna?` (0–999,9999, 4 decimales), `start_date?`, `maturity_date?` (1970-01-01..2100-12-31), `institution?` ≤ 120, `notes?` ≤ 2000, `notify_maturity=true`, `timezone_offset_minutes?` (−840..840), `price_source="manual"`. Reglas cruzadas: `maturity_date >= start_date`; `fixed_term` exige `start_date`, `maturity_date > start_date`, `interest_rate_tna` y moneda ARS o USD.
- `InvestmentUpdate`: todo opcional + `status` (`active|closed`). Las reglas cruzadas se validan en el service sobre el estado resultante (422 con mensaje en español). Cambiar `current_value` setea `value_updated_at`.
- `InvestmentOut`: columnas (sin `eve_notice_for`/`day_notice_for`) + `effective_value`, `value_source`, `gain`, `gain_pct`, `days_to_maturity`, `is_matured` y `fixed_term: {term_days, interest_total, amount_at_maturity, accrued_interest, tea_pct} | null`.
- `InvestmentSummary`: `by_currency[]`, `by_type[]` (cantidad y valor en ARS si es calculable), `total_ars`, `total_usd`, `missing_rates`, `upcoming_maturities[]` (activos con vencimiento en los próximos 30 días, máx. 5), `count_active`.

### D10. Migración `018_investments`

`revision = "018_investments"`, `down_revision = "017_withdrawal_requests"`. `upgrade`: `create_table("investments", ...)` con índices y checks; `add_column` a `user_preferences` (el booleano con `server_default=sa.false()` para filas existentes). `downgrade`: drop de la tabla y `batch_alter_table("user_preferences")` para borrar columnas (SQLite no soporta `DROP COLUMN` sin batch). Verificar con `alembic upgrade head` en SQLite **y** en Postgres (docker o PGlite) que la cadena tenga un solo head.

### D11. Export y borrado de cuenta

`("investments", Investment)` en `OWNED_TABLES` (`backend/app/modules/cuenta/service.py`), en el bloque de padres (no tiene hijos). Las columnas nuevas de `user_preferences` salen solas en el export. La guarda de `test_account.py` falla si se olvida.

### D12. Web (`frontend/`)

- `src/types`: `Investment`, `InvestmentInput`, `InvestmentSummary`, `NetWorth`, `AssetType`, `InvestmentCurrency`; `AppSettings` suma los campos de D3; `FinanceSummary` suma los de D7 (opcionales).
- `src/api/endpoints.ts`: `fetchInvestments`, `fetchInvestmentSummary`, `createInvestment`, `updateInvestment`, `deleteInvestment`, `fetchNetWorth`, todos con `tz_offset_minutes: tzOffsetMinutes()` y mocks equivalentes cuando `MOCK_ENABLED`.
- `src/hooks/useInvestments.ts`: SWR (`finance/investments`, `finance/investments/summary`, `finance/net-worth`); toda mutación revalida esas keys **y** `finance/summary`; cambiar cotización o toggle revalida además `settings`.
- `FinancePage.tsx`: nueva pestaña `inversiones` ("Inversiones") → `InvestmentsSection.tsx`:
  - `NetWorthCard`: Patrimonio en ARS y USD, barra de dos tramos (efectivo esmeralda / inversiones celeste-índigo, con leyenda), aviso de cotización faltante.
  - Editor de cotización inline ("Dólar: $ 1.450,50 · actualizada hace 3 días" → editar USD y EUR).
  - Toggle "Sumar inversiones al balance" con texto de ayuda.
  - Lista agrupada por tipo (encabezado con subtotal), fila/tarjeta con nombre, ticker, entidad, invertido, valor, ganancia (verde/rojo), TNA, chip "vence en X días" / "venció" / "vence hoy"; acciones editar, cerrar/reabrir, borrar (con confirmación). Filtro activos/cerrados.
  - `InvestmentModal.tsx` (RHF + Zod sin `z.coerce`, mismo patrón que `TransactionModal`): campos según tipo (plazo fijo muestra fechas + TNA obligatorias y una vista previa en vivo de interés y monto al vencimiento; oculta "valor actual" salvo que se quiera fijar a mano). Acepta coma decimal.
- `pages/Dashboard/FinanceWidget.tsx`: con el toggle ON muestra `net_worth_ars` y el tramo de inversiones diferenciado.
- Textos en español; soporte dark mode con los tokens existentes.

### D13. Mobile (`C:\Proyectos\vida-personal-mobile`)

- `src/types`, `src/api/endpoints.ts` (escrituras con `queued('...')` como el resto, mandando `timezone_offset_minutes: -new Date().getTimezoneOffset()`), `src/hooks/useInvestments.ts`.
- `src/screens/InvestmentsScreen.tsx` registrada en `FinanceStack` (`TabNavigator.tsx`, `FinanceStackParamList.Investments: { create?: boolean }`): tarjeta de Patrimonio, fila de cotización editable, `Switch` del toggle, `SectionList` agrupada por tipo con tarjeta por activo (valor, ganancia ±%, TNA, "vence en X días"), crear/editar en `BottomSheet` con `PickerField` (tipo, moneda), `TextField` decimal (`keyboardType="decimal-pad"` + `parseDecimal`), `DateField` (inicio/vencimiento), switch "Avisarme del vencimiento", vista previa de plazo fijo. `useCreateParam` abre el sheet al llegar con `create`.
- `FinanceScreen.tsx`: tile "Inversiones" (`chart-line`) en `TOOLS`; la grilla pasa de 2×2 a filas de 2 con la última a lo ancho (o 3 columnas) para 5 herramientas.
- `QuickCreateSheet.tsx`: opción `{ key: 'investment', label: 'Inversión', icon: 'chart-line', tab: 'FinanceTab', screen: 'Investments', create: true }`.
- `BalanceCard.tsx`: props `netWorth`/`investmentsValue`/`includeInvestments`; ON → número grande = `net_worth_ars`, rótulo "Balance + inversiones", barra de dos tramos y fila "Inversiones" en celeste/índigo (no verde/rojo, reservados a ingresos/egresos).
- Tap en la push: listener de `Notifications.addNotificationResponseReceivedListener` (y `getLastNotificationResponseAsync` en arranque en frío) que con `data.type === 'investment_maturity'` navega a `FinanceTab > Investments`. Canal `recordatorios` ya existe.

## Risks / Trade-offs

- [El balance de transacciones mezcla monedas y se asume ARS] → se documenta en la UI ("Efectivo (ARS)"); convertirlo queda fuera de alcance.
- [Cotización manual desactualizada da un patrimonio engañoso] → se muestra la fecha de actualización y se resalta si tiene más de 7 días.
- [Offset horario guardado por activo queda viejo tras un viaje o cambio de DST] → mismo trade-off aceptado en recordatorios; se corrige al editar el activo, y la ventana 9–22 tolera corrimientos de pocas horas.
- [Activos sin offset (API directa/clientes viejos) usan −180] → correcto para el mercado actual; documentado como pregunta abierta.
- [At-most-once: si Expo falla, el aviso se pierde] → igual que recordatorios; `send_to_user` loguea. Reintentos quedan fuera.
- [Otro loop por worker] → query indexada y acotada a 4 días de vencimientos; costo despreciable.
- [SQLite devuelve `float` en `Numeric` y no hace cumplir longitudes] → convertir a `Decimal(str())` al leer; tests de bordes de monto contra 422 (no 500); verificar la migración y un CRUD en Postgres.
- [`Numeric(12,2)` limita el valor por activo a 9.999.999.999,99] → consistente con el resto de finanzas; los totales se calculan en Python (sin límite de columna) y viajan como `Decimal`.
- [Toggle mal entendido como "mezclar" plata] → tramos con color y rótulo distintos, y texto de ayuda en el toggle.

## Migration Plan

1. Deploy backend con la migración `018_investments` (`entrypoint.sh` corre `alembic upgrade head`). Cambios aditivos: clientes viejos siguen funcionando (`/finance/summary` solo suma campos).
2. Deploy web.
3. Build EAS mobile (perfil habitual); hasta que se instale, los activos creados desde web reciben avisos con offset −180.
4. Rollback: `alembic downgrade 017_withdrawal_requests` borra la tabla y las columnas nuevas (se pierden los activos cargados: exportar antes si hubiera datos reales) y revertir el deploy; el scheduler nuevo desaparece con el código.

## Open Questions

1. **Offset por defecto**: ¿−180 (Argentina) para activos sin `timezone_offset_minutes`, o no avisar como hacen los recordatorios? (Propuesta: −180.)
2. **Horario del aviso**: fijo a las 9:00 locales. ¿Alcanza o se quiere configurable más adelante?
3. **Cotización EUR**: se agrega como campo opcional. ¿Se muestra siempre en la UI o solo si hay activos en EUR? (Propuesta: solo si hay activos en EUR.)
4. **Al vencer un plazo fijo** la app no lo cierra sola: sigue sumando su monto al vencimiento hasta que el usuario lo cierre o lo renueve. ¿Agregar una acción "Renovar" (crea uno nuevo con el monto cobrado y cierra el anterior)? Propuesta: fuera de este change.
5. **Cash en USD**: ¿mostrar `cash_balance_usd` (balance ARS convertido) en la tarjeta de Patrimonio o solo el total? (Propuesta: solo totales.)
