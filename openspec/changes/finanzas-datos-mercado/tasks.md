## 1. Backend — Modelo, migración y configuración

- [ ] 1.1 Crear `backend/app/modules/mercado/models.py` con `FxQuote` (`fx_quotes`), `InflationMonth` (`inflation_monthly`), `MarketPrice` (`market_prices`) y `MarketFetchState` (`market_fetch_state`) según D2 (uniques, índices, `Date` y timestamps tz-aware, sin `user_id`); registrarlos donde se importan los modelos para `create_all`
- [ ] 1.2 Agregar `fx_usd_source` (`server_default 'mep'`) y `fx_eur_source` (`server_default 'oficial'`) a `UserPreference` en `backend/app/modules/ajustes/models.py`
- [ ] 1.3 Migración `backend/migrations/versions/019_market_data.py` (o el siguiente número libre, `down_revision` = head vigente): crear las 4 tablas, sembrar las filas `fx`/`inflation`/`crypto` de `market_fetch_state` con `next_run_at` en el pasado, agregar las dos columnas y poner `'manual'` donde `fx_usd_ars`/`fx_eur_ars` no son nulos; `downgrade` pasa a `manual` las inversiones con `price_source='coingecko'`, borra tablas y columnas con `batch_alter_table`
- [ ] 1.4 `backend/app/config.py`: `MARKET_DATA_ENABLED` (default true), `COINGECKO_API_KEY` (opcional), `MARKET_FX_REFRESH_MINUTES=15`, `MARKET_CRYPTO_REFRESH_MINUTES=10`, `MARKET_INFLATION_REFRESH_HOURS=6`; listarlas en `docker-compose.prod.yml` (lista explícita de env) y documentarlas en `.env.prod.example` (sin valores reales)

## 2. Backend — Providers y servicios de mercado

- [ ] 2.1 `mercado/providers/base.py`: `FxQuoteIn`, parseo tolerante (ignora ítems inválidos), helper de cliente `httpx.AsyncClient(timeout=Timeout(10, connect=5), headers={"User-Agent": "Can_cen/1.0"})` inyectable
- [ ] 2.2 `providers/dolarapi.py` (`/v1/dolares`, `/v1/cotizaciones/eur`, normaliza `bolsa`→`mep`, `contadoconliqui`→`ccl`), `providers/bluelytics.py` (`/v2/latest`: oficial, blue, oficial_euro, blue_euro), `providers/argentinadatos.py` (último de `/v1/cotizaciones/dolares/{casa}` y `/v1/finanzas/indices/inflacion`), `providers/datos_gob.py` (serie `148.3_INIVELNAL_DICI_M_26`, `representation_mode=percent_change`)
- [ ] 2.3 `mercado/service.py::refresh_fx(client)`: primario + cadena de respaldo por par (D3), validación de sanidad (rangos y salto > 50 %), upsert diario por `(currency, kind, quote_date AR)` solo si `source_updated_at` es más nuevo, retención de 730 días una vez por día
- [ ] 2.4 `mercado/service.py::refresh_inflation(client)`: ArgentinaDatos con respaldo datos.gob.ar, normalizar `period` al día 1, sanidad −20..100 y no futuro, upsert (gana el primario ante revisiones)
- [ ] 2.5 `mercado/inflation.py` (puro): `accumulated_factor(series, start, end)` con prorrateo geométrico, estimación de meses sin publicar con el último dato, `estimated_months`, motivo `no_inflation_data`; `real_return(...)` y agregado de cartera (D5) con `Decimal`
- [ ] 2.6 `mercado/crypto_assets.py` con el mapeo curado ticker→(id, nombre) de D6 y `providers/coingecko.py` (`CoinGeckoProvider`: `supports`, `quote_many` en un solo `GET /simple/price`, header `x-cg-demo-api-key` si hay key, sanidad de precio, manejo de 429 con `Retry-After`)
- [ ] 2.7 `inversiones/valuation.py`: `PriceProvider` suma `supports` y `quote_many` (`quote` como atajo); registrar `PRICE_PROVIDERS["coingecko"]`; `refresh_quotes(db)` global: pares distintos en uso, sin pares no sale a la red, upsert en `market_prices` y `UPDATE` de `last_price`/`last_price_at` por par
- [ ] 2.8 `mercado/repository.py`: último quote por `(currency, kind)`, serie de IPC, precio en caché por par, operaciones del lease; caché en proceso (60 s quotes, 10 min IPC)

## 3. Backend — Scheduler

- [ ] 3.1 `mercado/scheduler.py::run_market_data_scheduler()`: ciclo de 60 s, `ensure_state_rows()` (atrapa `IntegrityError`), lease atómico por fuente con `UPDATE ... WHERE next_run_at <= now AND (lease_until IS NULL OR lease_until < now)` y `rowcount == 1`, commit antes de la red, éxito/backoff con topes (1 h fx/cripto, 24 h IPC), `last_error` truncado, nunca propaga excepciones
- [ ] 3.2 Arrancarlo en el `lifespan` de `backend/app/main.py` solo si `MARKET_DATA_ENABLED`, y cancelarlo al apagar junto con los otros schedulers

## 4. Backend — Inversiones, cotización efectiva y API

- [ ] 4.1 `inversiones/service.py::get_rates()` → `ResolvedRates` (manual / automática con última conocida / `manual_fallback` / faltante, `stale` por 96 h o 6 h sin éxito) usando la venta; `RatesOut` suma los campos aditivos de D4 y `updated_at` = `as_of` del USD efectivo
- [ ] 4.2 `inversiones/schemas.py`: `ALLOWED_PRICE_SOURCES = {"manual"} ∪ PRICE_PROVIDERS`; validación sobre el estado resultante (create y update) de `coingecko` → `crypto` + ticker soportado + `quantity > 0`, 422 en español; `stock`/`bond`/`fund` solo `manual`
- [ ] 4.3 `inversiones/service.py`: al crear/editar con `coingecko`, completar `last_price`/`last_price_at` desde `market_prices` o poner `market_fetch_state.crypto.next_run_at = now`; `InvestmentOut` suma `quote_provider`, `quote_stale`, `real_return`, `real_return_unavailable_reason`; `InvestmentSummary` suma `real_return_ars` (fecha de fin según D5, usando el "hoy" del usuario)
- [ ] 4.4 `backend/app/api/v1/settings.py`: `fx_usd_source`/`fx_eur_source` en GET y PUT con enum validado (422); cambiar la fuente no toca `fx_usd_ars`
- [ ] 4.5 `mercado/api_routes.py` (`prefix="/finance/market"`, autenticado): `GET /fx`, `GET /inflation?months=` (1..120), `GET /crypto-assets`; incluir el router en `backend/app/api/v1/router.py`; ninguna ruta llama a la red

## 5. Web (`frontend/`)

- [ ] 5.1 `src/types`: `FxQuote`, `MarketFx`, `InflationSeries`, `RealReturn`, `CryptoAsset`; campos nuevos en `AppSettings`, `Investment`, `InvestmentSummary` y `NetWorth.rates`
- [ ] 5.2 `src/api/endpoints.ts`: `fetchMarketFx`, `fetchInflation`, `fetchCryptoAssets` y mocks equivalentes (`VITE_MOCK_ENABLED`), mocks de inversiones con `real_return` y cripto automática; `src/hooks/useMarket.ts` (SWR, `refreshInterval` 5 min) e invalidaciones al cambiar la fuente (`settings`, `finance/net-worth`, `finance/investments/summary`, `finance/summary`)
- [ ] 5.3 `src/pages/Finance/FxRatesEditor.tsx`: control segmentado Oficial/MEP/Blue/Manual, las tres cotizaciones con compra/venta, "hace X · DolarAPI", badge "desactualizada", aviso de `manual_fallback`, inputs manuales que mandan `fx_usd_source: "manual"`; fila de euro solo con activos en EUR
- [ ] 5.4 `NetWorthCard.tsx`: pie con dólar usado, valor, fuente y antigüedad
- [ ] 5.5 `InvestmentsSection.tsx`: chip "Real ±x %" con tooltip nominal/inflación, marca "estimado", proyección al vencimiento en plazo fijo, motivo cuando no hay rendimiento real, "Cotización automática · hace X" + "Datos de CoinGecko" en cripto, resumen de rendimiento real en pesos
- [ ] 5.6 `InvestmentModal.tsx` (RHF + Zod sin `z.coerce`): switch "Cotización automática" para cripto con autocompletar de tickers soportados, cantidad obligatoria y "valor actual" oculto; "Fecha de compra" con ayuda en tipos no plazo fijo

## 6. Mobile (`C:\Proyectos\vida-personal-mobile`)

- [ ] 6.1 [mobile] `src/types/index.ts` y `src/api/endpoints.ts`: tipos y `fetchMarketFx`, `fetchInflation`, `fetchCryptoAssets`; la fuente se guarda con el `PUT /settings` existente (`queued(...)`)
- [ ] 6.2 [mobile] `src/hooks/useInvestments.ts`: hooks de mercado y revalidación de net worth/resumen/settings al cambiar la fuente
- [ ] 6.3 [mobile] `src/components/FxRatesEditor.tsx`: `FilterChips` Oficial/MEP/Blue/Manual, cotizaciones con "hace X · DolarAPI", badge desactualizada, aviso de fallback, euro solo con activos en EUR
- [ ] 6.4 [mobile] `src/components/NetWorthCard.tsx`: pie de dólar usado y fuente
- [ ] 6.5 [mobile] `src/screens/InvestmentsScreen.tsx`: chips de rendimiento real (estimado, proyección, motivo), cotización automática y "Datos de CoinGecko"; resumen con rendimiento real en pesos
- [ ] 6.6 [mobile] `src/components/InvestmentFormSheet.tsx`: `Switch` "Cotización automática" para cripto (tickers soportados, cantidad obligatoria, oculta valor actual) y "Fecha de compra"; sin CTAs ni textos de compra

## 7. Tests

- [ ] 7.1 `backend/tests/conftest.py`: `MARKET_DATA_ENABLED=false` y fixture `autouse` que hace fallar cualquier request HTTP saliente que no vaya por `httpx.MockTransport`; fixtures JSON con las respuestas reales grabadas de DolarAPI, Bluelytics, ArgentinaDatos, datos.gob.ar y CoinGecko
- [ ] 7.2 `backend/tests/test_market_fx.py`: parseo y normalización de DolarAPI; respaldo Bluelytics/ArgentinaDatos ante timeout o par faltante; respaldo viejo no pisa dato nuevo; sanidad (cero, salto > 50 %, ítem malformado); una fila por día; retención 730 días
- [ ] 7.3 `test_market_fx.py` (cotización efectiva): manual, automática, última conocida con API caída, `manual_fallback`, faltante en `missing_rates`, `stale`; totales con MEP (500.000 ARS + 2.000 USD a 1563,90 = 3.627.800,00); `/finance/summary` y `/finance/net-worth` usan la fuente elegida
- [ ] 7.4 `backend/tests/test_market_inflation.py`: serie (normalización, sanidad, respaldo); factor de mes completo, mes parcial (`1,019^(15/30)` → 0,95 %), meses estimados, inicio anterior a la serie; real por activo (ejemplo plazo fijo 2,47 / 1,90 / 0,56), pérdida (−1,94), motivos `currency`/`no_start_date`/`too_short`, proyección al vencimiento estimada, agregado de cartera
- [ ] 7.5 `backend/tests/test_market_crypto.py`: un solo request en lote para varios usuarios y monedas; sin pares no hay request; 429 con `Retry-After`; validación 422 (ticker desconocido, sin cantidad, tipo `stock`, fuente no registrada); creación con precio en caché (0,5 BTC × 79.509 = 39.754,50, `value_source="quote"`); sin precio en caché agenda el job; volver a manual; `quote_stale`; header de API key
- [ ] 7.6 `backend/tests/test_market_scheduler.py`: lease con varios workers simulados (uno solo consulta), lease vencido se retoma, backoff (15 → 60 min tras dos fallos) y topes, `ensure_state_rows`, excepción de provider no corta el loop, scheduler no arranca con `MARKET_DATA_ENABLED=false`
- [ ] 7.7 `test_ajustes.py`: `fx_usd_source`/`fx_eur_source` válidos e inválidos (422), cambiar la fuente no borra la cotización manual; `test_investments*.py`: regresión del CRUD y la valuación manual existentes
- [ ] 7.8 Aislamiento: `test_tenant_isolation.py` — la preferencia de fuente y el rendimiento real son por usuario; un usuario no ve ni modifica inversiones ajenas por el camino de `coingecko`; `test_infra.py::test_no_api_route_is_public_by_accident` cubre las rutas nuevas (401 sin sesión); `test_account.py` sigue pasando (tablas de mercado sin `user_id`, preferencias nuevas en el export)
- [ ] 7.9 Web: tests de `FxRatesEditor` (cambio de fuente manda el PUT e invalida keys, manual manda `fx_usd_source: "manual"`, badge desactualizada), `InvestmentsSection` (chips de rendimiento real y CoinGecko) e `InvestmentModal` (switch automático), con `npx vitest run --maxWorkers=2`
- [ ] 7.10 Correr la suite completa del backend (`cd backend && python -m pytest -q`) y del web sin regresiones

## 8. Verificación contra backend real (no mock)

- [ ] 8.1 Migración en SQLite y en Postgres (PGlite vía npm o docker): `alembic upgrade head` con un solo head, usuarios con cotización manual quedan en `manual`, `downgrade` y `upgrade` de nuevo
- [ ] 8.2 Levantar el backend con `MARKET_DATA_ENABLED=true` y 2+ workers de gunicorn: comprobar en logs y en `market_fetch_state` que cada fuente se consulta una sola vez por ciclo, que se cargan dólar, euro y la serie del IPC, y que con la red cortada la app sigue sirviendo la última cotización con `stale`/`degraded`
- [ ] 8.3 Web con `VITE_MOCK_ENABLED=false`: cambiar Oficial/MEP/Blue/Manual y ver patrimonio y totales recalculados; crear un plazo fijo con fecha pasada y ver el rendimiento real (y "estimado" en el mes en curso); crear 0,01 BTC automático y ver la cotización dentro de un ciclo con "Datos de CoinGecko"
- [ ] 8.4 Mobile (build lan o Expo contra el backend real): selector de dólar, pie de fuente, chips de rendimiento real y cripto automática; sin textos de compra
- [ ] 8.5 Correr `openspec validate finanzas-datos-mercado --strict` y marcar las tareas completadas
