## 1. Backend — Modelo y migración

- [x] 1.1 Crear `backend/app/modules/inversiones/__init__.py` y `models.py` con `Investment` (columnas, índices y `CheckConstraint` de design D2; `Date` real y `DateTime(timezone=True)`; `Numeric` para dinero, cantidad, tasa y precio)
- [x] 1.2 Agregar a `UserPreference` (`backend/app/modules/ajustes/models.py`) `fx_usd_ars`, `fx_eur_ars` (`Numeric(14,4)` null), `fx_rates_updated_at` y `include_investments_in_balance` (`server_default=false`)
- [x] 1.3 Registrar el modelo donde se importan los modelos para Alembic/`Base.metadata` (mismo lugar que el resto de módulos)
- [x] 1.4 Crear `backend/migrations/versions/018_investments.py` (`down_revision = "017_withdrawal_requests"`): `create_table` + índices + checks; `add_column` en `user_preferences`; `downgrade` con `batch_alter_table` para SQLite
- [x] 1.5 Verificar `alembic heads` = un solo head (`018_investments`) y `alembic upgrade head` / `downgrade 017_withdrawal_requests` / `upgrade head` en SQLite

## 2. Backend — Valuación y cálculos

- [x] 2.1 `inversiones/valuation.py`: helper `round2` (`Decimal`, `ROUND_HALF_UP`) y conversión segura `Decimal(str(x))` para lo que SQLite devuelve como `float`
- [x] 2.2 Cálculo de plazo fijo: `term_days`, `interest_total`, `amount_at_maturity`, `accrued_interest(today)` (clamp a `[0, term_days]`) y `tea_pct` (D4)
- [x] 2.3 `effective_value(inv, today)` con la precedencia quote → manual → fixed_term_accrued → invested, y derivados `gain`, `gain_pct`, `days_to_maturity`, `is_matured`
- [x] 2.4 Punto de extensión: `PriceQuote`, `PriceProvider` (Protocol), `PRICE_PROVIDERS = {}` y `refresh_quotes()` no-op (sin HTTP externo)
- [x] 2.5 Conversión de totales (D6): subtotales por moneda, factores ARS/USD/USDT/EUR, `total_ars`, `total_usd`, `missing_rates`
- [x] 2.6 Helper `local_today(tz_offset_minutes)` y formateo de montos es-AR (`$ 1.024.657,53`) para las push

## 3. Backend — Schemas, repository, service y API

- [x] 3.1 `inversiones/schemas.py`: enums `AssetType` y `InvestmentCurrency`; `InvestmentCreate`/`InvestmentUpdate` con los límites de D9 (reusar `Money` de `finanzas/schemas.py`), normalización de `ticker`, `price_source` solo `manual`, reglas cruzadas de fechas y de `fixed_term`
- [x] 3.2 `InvestmentOut` (sin `eve_notice_for`/`day_notice_for`) con campos calculados y objeto `fixed_term`; `InvestmentSummary` y `NetWorthOut`
- [x] 3.3 `inversiones/repository.py`: todas las consultas filtradas por `user_id`; `get(id, user_id)`, `list(user_id, status, asset_type)` con el orden de D9, `create`, `update`, `delete`, `list_due_for_alerts(utc_today)`
- [x] 3.4 `inversiones/service.py`: crear/actualizar (validar reglas cruzadas sobre el estado resultante → 422 en español; ignorar `null` en campos obligatorios; setear `value_updated_at`), cerrar/reabrir, borrar, armar `InvestmentOut`, `summary()` (incluye `by_type` y `upcoming_maturities` ≤ 5 en 30 días) y `net_worth()` usando `FinanzasService.get_dashboard_stats` para el balance
- [x] 3.5 `inversiones/api_routes.py`: router `prefix="/finance/investments"` con GET lista, GET `/summary` (declarado antes de `/{id}`), GET/PUT/DELETE `/{id}`, POST; `tz_offset_minutes` (−840..840) en los GET; todas con `get_current_user`
- [x] 3.6 Endpoint `GET /api/v1/finance/net-worth` (en el router de inversiones o en `api/v1/finance.py`, sin dejarlo público)
- [x] 3.7 Incluir el router en `backend/app/api/v1/router.py`
- [x] 3.8 `/finance/summary` (`backend/app/api/v1/finance.py`): sumar `investments_value_ars`, `net_worth_ars`, `investments_missing_rates`, `include_investments_in_balance` y el query `tz_offset_minutes`, sin cambiar `balance`
- [x] 3.9 `/settings` (`backend/app/api/v1/settings.py`): exponer y aceptar `fx_usd_ars`, `fx_eur_ars` (>0, ≤ 9.999.999,9999, 4 decimales, null borra), `include_investments_in_balance`; devolver `fx_rates_updated_at` y setearlo en el server solo cuando cambia una cotización
- [x] 3.10 Sumar `("investments", Investment)` a `OWNED_TABLES` en `backend/app/modules/cuenta/service.py`

## 4. Backend — Avisos de vencimiento

- [x] 4.1 Extraer el `SET NX` de `recordatorios/scheduler.py` a `backend/app/core/redis_claim.py::claim_once(key, ttl_seconds)`; dejar `_claim_in_redis` como wrapper y confirmar que `test_reminders.py` sigue verde
- [x] 4.2 `inversiones/scheduler.py`: `_tick(now_utc)` que consulta activos debidos (`list_due_for_alerts`), calcula hora local con `timezone_offset_minutes` (fallback −180), decide `eve`/`day` dentro de la ventana 09:00–21:59
- [x] 4.3 Dedup en tres capas: set en memoria (con poda), `claim_once("investment-maturity:{id}:{kind}:{maturity}", 129600)` y `UPDATE ... SET eve_notice_for/day_notice_for = maturity WHERE ... IS NULL OR <> maturity` enviando solo si `rowcount == 1`
- [x] 4.4 Armar título/cuerpo en español (monto al vencimiento para plazo fijo) y `data = {type: "investment_maturity", investment_id}`; enviar con `PushService.send_to_user`, atrapando y logueando errores por activo
- [x] 4.5 `run_investment_alert_scheduler()` alineado al minuto y arrancarlo/cancelarlo en el `lifespan` de `backend/app/main.py` junto al de recordatorios

## 5. Backend — Tests

- [x] 5.1 `backend/tests/test_investments_valuation.py` (unitarios puros): plazo fijo 1.000.000 / 30 % / 30 días → 24.657,53, 1.024.657,53, TEA 34,50; devengado a 12 días 9.863,01; clamp antes del inicio y después del vencimiento; precedencia quote/manual/accrued/invested; `gain_pct` con invertido 0 → null; redondeo half-up
- [x] 5.2 Conversión: 500.000 ARS + 2.000 USD con 1450,50 → 3.401.000,00 / 2.344,71; sin cotización → nulls + `missing_rates`; solo ARS sin cotización; EUR sin `fx_eur_ars`; USDT 1:1
- [x] 5.3 `backend/tests/test_investments.py`: CRUD completo, orden de la lista, filtro `status`/`asset_type`, cerrar/reabrir, `value_updated_at`, `null` en campo obligatorio ignorado, update que rompe regla cruzada → 422 sin persistir, `days_to_maturity` con `tz_offset_minutes`
- [x] 5.4 Límites → 422 (nunca 500): monto > 9.999.999.999,99, negativos, `quantity` con 9 decimales, TNA > 999,9999, ticker inválido, moneda `BTC`, `price_source` ≠ manual, fechas fuera de rango, vencimiento < inicio, plazo fijo sin TNA / en EUR, offset fuera de ±840, textos largos
- [x] 5.5 Aislamiento: sumar inversiones a la parametrización de `test_tenant_isolation.py` (GET/PUT/DELETE de otro usuario → 404) + listas, summary y net-worth no cuentan datos ajenos
- [x] 5.6 `test_account.py`: el export incluye `investments` del usuario y no los de otro; el borrado de cuenta no deja filas; la guarda de `OWNED_TABLES` pasa
- [x] 5.7 `test_api_finance.py`: `/finance/summary` mantiene `balance` con toggle on/off y devuelve los campos nuevos (sin inversiones → `0.00`; cotización faltante → null); `/finance/net-worth` suma balance + inversiones activas
- [x] 5.8 `test_ajustes.py`: cotizaciones (set, borrar con null, 0/negativo → 422, `fx_rates_updated_at` solo cambia si cambia una cotización), toggle default false
- [x] 5.9 `backend/tests/test_investment_alerts.py`: aviso `eve` a las 09:00 locales, `day` el día del vencimiento, nada a las 08:59 ni desde las 22:00, catch-up a las 11:30, fallback −180, offset +60, `notify_maturity=false`/cerrado/sin vencimiento no avisan, usuario sin tokens no falla, Expo caído no corta el ciclo (mock de `send_to_user`)
- [x] 5.10 Dedup: dos `_tick` concurrentes sobre el mismo activo → una sola push; ciclos repetidos en la ventana → una; "reinicio" (limpiar set en memoria) sin Redis → no reenvía por la marca persistente; claim de Redis perdido → no envía; cambiar `maturity_date` rehabilita los avisos
- [x] 5.11 Confirmar que `test_infra.py::test_no_api_route_is_public_by_accident` pasa sin agregar rutas públicas
- [x] 5.12 Correr `pytest backend/tests -q` completo sin regresiones

## 6. Web — API, tipos y hooks (`frontend/`)

- [x] 6.1 Tipos en `src/types`: `AssetType`, `InvestmentCurrency`, `Investment`, `InvestmentInput`, `InvestmentSummary`, `NetWorth`; extender `AppSettings` y `FinanceSummary` (campos nuevos opcionales)
- [x] 6.2 `src/api/endpoints.ts`: `fetchInvestments`, `fetchInvestment`, `fetchInvestmentSummary`, `createInvestment`, `updateInvestment`, `deleteInvestment`, `fetchNetWorth` con `tz_offset_minutes: tzOffsetMinutes()` en lecturas y `timezone_offset_minutes` en escrituras; mocks con las mismas formas cuando `MOCK_ENABLED`
- [x] 6.3 `src/hooks/useInvestments.ts`: hooks SWR + `save`/`remove`/`close` que revalidan `finance/investments*`, `finance/net-worth` y `finance/summary`; acciones de cotización/toggle que además revalidan `settings`
- [x] 6.4 Tests de endpoints/hooks en `src/api/__tests__` y `src/hooks/__tests__` (URL, params de tz, invalidación de keys)

## 7. Web — UI (`frontend/`)

- [x] 7.1 `src/pages/Finance/NetWorthCard.tsx`: desglose Disponible / Inversiones / Total en ARS y USD (cada uno), barra de dos tramos Efectivo/Inversiones (inversiones en celeste/índigo, no verde/rojo), aviso de cotización faltante, dark mode
- [x] 7.2 Editor de cotización inline (USD siempre; EUR solo si hay activos en EUR) con "actualizada hace X días" y resaltado si tiene más de 7 días
- [x] 7.3 Toggle "Sumar inversiones al balance" con texto de ayuda
- [x] 7.4 `src/pages/Finance/InvestmentsSection.tsx`: lista agrupada por tipo con subtotal, ganancia verde/rojo, TNA, chip de vencimiento ("vence en X días" / "vence hoy" / "venció"), filtro activos/cerrados, acciones editar/cerrar-reabrir/borrar con confirmación, estado vacío y loaders
- [x] 7.5 `src/pages/Finance/InvestmentModal.tsx`: RHF + Zod sin `z.coerce` (patrón de `TransactionModal`), campos según tipo, coma decimal, vista previa de plazo fijo, errores del server en español
- [x] 7.6 Pestaña `inversiones` ("Inversiones") en `FinancePage.tsx`
- [x] 7.7 `src/pages/Dashboard/FinanceWidget.tsx`: con el toggle ON mostrar `net_worth_ars` como "Balance + inversiones" con tramos diferenciados; OFF igual que hoy
- [x] 7.8 Tests de componentes (`__tests__`): modal valida y previsualiza 24.657,53 / 1.024.657,53; NetWorthCard sin cotización muestra el aviso; widget respeta el toggle
- [x] 7.9 `npm run build` y lint sin errores

## 8. Mobile — API, tipos y hooks (`C:\Proyectos\vida-personal-mobile`)

- [x] 8.1 [mobile] Tipos en `src/types` (inversiones, net worth, settings y summary extendidos)
- [x] 8.2 [mobile] `src/api/endpoints.ts`: endpoints de inversiones y net-worth; escrituras con `queued('...')` y `timezone_offset_minutes: -new Date().getTimezoneOffset()`; lecturas con `tz_offset_minutes`
- [x] 8.3 [mobile] `src/hooks/useInvestments.ts` con revalidación de inversiones, net-worth, summary y settings (patrón de `useFinance.ts`)

## 9. Mobile — UI (`C:\Proyectos\vida-personal-mobile`)

- [x] 9.1 [mobile] `src/screens/InvestmentsScreen.tsx`: tarjeta de Patrimonio, fila de cotización editable, `Switch` "Sumar inversiones al balance", `SectionList` por tipo con tarjeta por activo (valor, ganancia ±%, TNA, "vence en X días"), estados vacío/cargando/error
- [x] 9.2 [mobile] Formulario en `BottomSheet`: `PickerField` (tipo, moneda), `TextField` con `keyboardType="decimal-pad"` + `parseDecimal`, `DateField` inicio/vencimiento, switch "Avisarme del vencimiento", vista previa de plazo fijo, editar/cerrar/borrar con `Alert` de confirmación
- [x] 9.3 [mobile] Registrar `Investments` en `FinanceStack` (`src/navigation/TabNavigator.tsx`, `FinanceStackParamList`) y abrir el sheet con `useCreateParam` cuando llega `create`
- [x] 9.4 [mobile] `src/screens/FinanceScreen.tsx`: tile "Inversiones" (`chart-line`) en `TOOLS` y ajustar la grilla 2×2 para 5 herramientas
- [x] 9.5 [mobile] `src/components/QuickCreateSheet.tsx`: opción "Inversión" → `FinanceTab` › `Investments` con `create: true`
- [x] 9.6 [mobile] `src/components/BalanceCard.tsx` + `DashboardScreen.tsx`: con el toggle ON, `net_worth_ars`, rótulo "Balance + inversiones", barra de dos tramos Efectivo/Inversiones en color distinto; aviso si falta cotización; OFF sin cambios
- [x] 9.7 [mobile] Tap en notificación: listener `addNotificationResponseReceivedListener` + `getLastNotificationResponseAsync` que con `type === 'investment_maturity'` navega a Finanzas › Inversiones
- [x] 9.8 [mobile] `npx tsc --noEmit` y tests existentes del repo mobile en verde

## 10. Verificación contra el backend real (no mock)

- [x] 10.1 Levantar backend real con la migración aplicada en Postgres (docker compose o PGlite) y correr un CRUD completo de inversiones por API: montos límite dan 422, no 500
- [ ] 10.2 Web con `VITE_MOCK_ENABLED=false`: crear un plazo fijo, una acción en USD y un activo en EUR; cargar/borrar cotizaciones; ver Patrimonio, subtotales y aviso de cotización faltante; cerrar un activo y ver que deja de sumar
- [ ] 10.3 Web: prender/apagar el toggle y comprobar Dashboard y Finanzas (`balance` igual, tramo de inversiones diferenciado)
- [ ] 10.4 Mobile (build lan o Expo contra el backend real): pantalla Inversiones, alta rápida desde "+", coma decimal, `BalanceCard` con toggle ON/OFF
- [ ] 10.5 Push: crear un activo que venza mañana con el reloj/offset ajustado para que caiga dentro de la ventana y comprobar una sola push "Vence mañana" con 2+ workers de gunicorn y Redis; repetir sin Redis reiniciando el proceso; tocar la push abre Inversiones
- [x] 10.6 Export de cuenta contiene `investments`; borrar una cuenta de prueba no deja filas
- [ ] 10.7 Correr `openspec validate finanzas-inversiones` y marcar las tareas completadas
