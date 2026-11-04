## Context

- **Lo que dejó `finanzas-inversiones`** (implementado, 64/69 tareas; falta la verificación manual): módulo `backend/app/modules/inversiones/` con `valuation.py` puro. `valuate()` ya da precedencia a la cotización (`price_source != "manual"` + `quantity` + `last_price` → `value_source="quote"`). `PRICE_PROVIDERS: dict[str, PriceProvider] = {}` está vacío, `PriceProvider` tiene un único `quote(ticker, currency)` y `refresh_quotes(db, user_id)` es un no-op. `schemas.py::_check_price_source` solo acepta `manual`. `InvestmentService.get_rates()` lee `fx_usd_ars`/`fx_eur_ars`/`fx_rates_updated_at` de `user_preferences` y es la única puerta de entrada de cotizaciones para el resumen, el patrimonio (`/finance/net-worth`) y `/finance/summary` (`backend/app/api/v1/finance.py`). `last_price` es `Numeric(20,8)`.
- **Clientes**: web `frontend/src/pages/Finance/{FxRatesEditor,NetWorthCard,InvestmentsSection,InvestmentModal}.tsx`; mobile `src/components/{FxRatesEditor,NetWorthCard,InvestmentFormSheet,BalanceCard,CashInvestmentsBar}.tsx` y `src/screens/InvestmentsScreen.tsx`.
- **Infra**: gunicorn con varios workers y cada uno corre los schedulers del `lifespan` (`backend/app/main.py`: recordatorios y vencimientos). Redis es opcional (`core/redis_claim.py::claim_once`). `httpx==0.28.1` ya es dependencia (lo usan `core/email.py`, `billing/mercadopago.py`). Postgres en prod, SQLite en tests (`create_all`), Alembic head `018_investments`.
- **Fuentes externas verificadas el 2026-10-25** (consultas reales):
  - **DolarAPI** (`https://dolarapi.com`, open source MIT, sin API key, detrás de Cloudflare, `Access-Control-Allow-Origin: *`). `GET /v1/dolares` devuelve en **una** respuesta `[{moneda, casa, nombre, compra, venta, fechaActualizacion}]` para `oficial`, `blue`, `bolsa` (MEP), `contadoconliqui`, `mayorista`, `cripto`, `tarjeta` (ej. MEP compra 1557,4 / venta 1563,9, `2026-10-25T20:58:00Z`). `GET /v1/cotizaciones/eur` → `{moneda:"EUR", casa:"oficial", compra, venta, fechaActualizacion}`. No publica límites de uso: se consulta poco (cada 15 min) y desde un solo worker.
  - **Bluelytics** (`https://api.bluelytics.com.ar/v2/latest`, sin key): `oficial`, `blue`, `oficial_euro`, `blue_euro` con `value_buy/value_sell/value_avg` y `last_update`. No tiene MEP. Respaldo.
  - **ArgentinaDatos** (`https://api.argentinadatos.com`, MIT, "API pública no oficial", sin key, sin límites publicados): `GET /v1/cotizaciones/dolares/{casa}` (histórico diario `{casa, compra, venta, fecha}`, incluye `bolsa`) y `GET /v1/finanzas/indices/inflacion` (`[{fecha:"2026-09-30", valor:1.9}]`, variación mensual % del IPC; al 2026-10-25 ya tenía septiembre).
  - **datos.gob.ar Series de Tiempo** (`https://apis.datos.gob.ar/series/api/series/?ids=148.3_INIVELNAL_DICI_M_26`, oficial, fuente INDEC, sin key): nivel del IPC nacional base dic-2016, mensual. Al 2026-10-25 su último dato era agosto (un mes más atrasado que ArgentinaDatos). Respaldo; con `representation_mode=percent_change` da la variación mensual.
  - **CoinGecko** (`https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,tether&vs_currencies=usd,ars&include_last_updated_at=true`). Plan **Demo**: gratis, sin tarjeta, **10.000 créditos/mes, 100 req/min** (subió de 30 a 100 el 2026-05-17 según su changelog), **atribución obligatoria**; key por header `x-cg-demo-api-key` (o query `x_cg_demo_api_key`), misma base URL. El acceso sin key también responde, pero con límites menores y variables. La página de precios marca la licencia comercial solo en los planes pagos; para Demo dice "Attribution required" (ver Preguntas abiertas).
  - **Acciones/CEDEARs**: BYMA vende sus datos de mercado; no se encontró fuente gratuita oficial con términos claros (solo endpoints no documentados y librerías comunitarias). Fuera de alcance.

## Goals / Non-Goals

**Goals:**
- Cotización del dólar (oficial, MEP, blue) y del euro (oficial, blue) automática, consultada por el server y compartida por todos los usuarios, con histórico diario mínimo, fallback y frescura visibles.
- Que cada usuario elija con qué dólar convierte (o siga con su cotización manual) sin que cambie nada para quien ya cargó una.
- Serie mensual del IPC y rendimiento real (nominal vs inflación) por activo en pesos y agregado, con estimación explícita de los meses sin publicar.
- Precio automático de cripto con CoinGecko enchufado en `PRICE_PROVIDERS`, en lote, dentro del plan gratuito.
- Cero llamadas duplicadas entre workers, cero llamadas externas por request de usuario, cero llamadas a la red real en tests, y la app funcionando igual si las APIs caen.

**Non-Goals:**
- Acciones/CEDEARs/bonos/FCI automáticos (sin fuente gratuita confiable).
- Rendimiento real de activos en USD/EUR; inflación de otros países.
- Gráficos del dólar o del IPC, alertas de precio, conversión del balance de transacciones.
- Exponer los datos de mercado sin login (los endpoints nuevos son autenticados).

## Decisions

### D1. Módulo nuevo `mercado` con tablas globales

`backend/app/modules/mercado/`: `models.py`, `schemas.py`, `repository.py`, `service.py`, `providers/` (`base.py`, `dolarapi.py`, `bluelytics.py`, `argentinadatos.py`, `datos_gob.py`, `coingecko.py`), `inflation.py` (cálculos puros), `crypto_assets.py` (mapeo), `scheduler.py`, `api_routes.py`. Los datos de mercado no pertenecen a un usuario: tablas **sin `user_id`**, no entran en `OWNED_TABLES` (la guarda de `test_account.py` solo exige tablas con `user_id`). Ningún dato del usuario se manda a las APIs externas.

*Alternativa*: Redis como caché. Descartada: Redis es opcional en el deploy y el histórico/fallback tiene que sobrevivir reinicios; la base ya está y las tablas son chicas.

### D2. Modelo de datos

**`fx_quotes`** — última cotización del día por tipo (histórico diario = cierre):

| Columna | Tipo | Notas |
|---|---|---|
| `id` | `Integer` PK autoincrement | |
| `currency` | `String(5)` | `USD`, `EUR` |
| `kind` | `String(20)` | `oficial`, `mep`, `blue`, `ccl`, `mayorista`, `cripto`, `tarjeta` (se normaliza `bolsa`→`mep`, `contadoconliqui`→`ccl`) |
| `quote_date` | `Date` | fecha de `source_updated_at` en hora de Argentina (UTC−3 fijo) |
| `buy` | `Numeric(14,4)` null | compra |
| `sell` | `Numeric(14,4)` | venta (la que se usa para convertir, D4) |
| `provider` | `String(20)` | `dolarapi`, `bluelytics`, `argentinadatos` |
| `source_updated_at` | `DateTime(tz)` | fecha que informa la fuente |
| `fetched_at` | `DateTime(tz)` | cuándo la trajimos |

`UniqueConstraint(currency, kind, quote_date)`; índice `(currency, kind, quote_date desc)`. Se guardan todos los tipos que trae `/v1/dolares` (misma respuesta, costo cero); la UI expone tres. Retención: se borran filas de más de 730 días una vez por día.

**`inflation_monthly`**: `period Date PK` (primer día del mes), `pct Numeric(7,4)` (variación mensual %, ej. `1.9000`), `provider String(20)`, `fetched_at DateTime(tz)`. Sin retención (≈ 12 filas/año).

**`market_prices`** — caché del último precio de cripto: `id Integer PK`, `provider String(20)`, `symbol String(20)` (ticker), `vs_currency String(5)` (`USD`/`ARS`/`EUR`), `price Numeric(20,8)` (mismo tipo que `investments.last_price`), `source_updated_at DateTime(tz)`, `fetched_at DateTime(tz)`; `UniqueConstraint(provider, symbol, vs_currency)`.

**`market_fetch_state`** — coordinación entre workers (D8): `source String(20) PK` (`fx`, `inflation`, `crypto`), `next_run_at DateTime(tz)`, `lease_until DateTime(tz) null`, `last_attempt_at`, `last_success_at DateTime(tz) null`, `last_error String(300) null`, `consecutive_failures Integer default 0`. La migración siembra las tres filas con `next_run_at` en el pasado (primer ciclo inmediato); `ensure_state_rows()` las crea si faltan (tests con `create_all`) atrapando `IntegrityError`, sin `ON CONFLICT` específico de un motor.

**`user_preferences`** suma `fx_usd_source String(10) NOT NULL server_default 'mep'` y `fx_eur_source String(10) NOT NULL server_default 'oficial'`. La migración pone `'manual'` donde `fx_usd_ars IS NOT NULL` (y lo mismo para EUR): quien ya cargó una cotización sigue viendo exactamente lo mismo. Los campos manuales existentes no cambian.

Upserts portables (SQLite y Postgres): select + update/insert dentro de la transacción del job; el lease (D8) garantiza un solo escritor por fuente y la unique atrapa la carrera residual (reintento como update). Fechas como `Date` y timestamps tz-aware; lectura de `Numeric` con `to_decimal` (SQLite devuelve `float`).

### D3. Providers de cotización del dólar y cadena de respaldo

Interfaz común (`providers/base.py`): `async def fetch(client: httpx.AsyncClient) -> list[FxQuote]` con `FxQuote(currency, kind, buy, sell, provider, source_updated_at)`. Cada provider parsea con un modelo Pydantic tolerante (ignora campos extra, descarta ítems inválidos sin tirar todo).

| Par | Primario | Respaldo 1 | Respaldo 2 |
|---|---|---|---|
| USD oficial | DolarAPI `/v1/dolares` | Bluelytics `oficial` | ArgentinaDatos `/v1/cotizaciones/dolares/oficial` (último) |
| USD mep | DolarAPI (`bolsa`) | ArgentinaDatos `…/bolsa` | — |
| USD blue | DolarAPI | Bluelytics `blue` | ArgentinaDatos `…/blue` |
| USD ccl/mayorista/cripto/tarjeta | DolarAPI | — | — |
| EUR oficial | DolarAPI `/v1/cotizaciones/eur` | Bluelytics `oficial_euro` | — |
| EUR blue | Bluelytics `blue_euro` | — | — |

El job llama al primario; los respaldos solo se consultan para los pares que el primario no trajo o si falló entero. Una cotización se guarda solo si su `source_updated_at` es más nueva que la guardada para ese `(currency, kind, quote_date)` (un respaldo atrasado no pisa un dato mejor). **Validación de sanidad**: `0 < sell ≤ 10.000.000`, `buy ≤ sell × 1,5` si viene, y se descarta (con log) un valor que se aparte más de 50 % de la última cotización conocida del mismo tipo. Intervalo: 15 min (`MARKET_FX_REFRESH_MINUTES`). ≈ 96 consultas/día a DolarAPI en total (no por usuario).

### D4. Cotización efectiva del usuario

`InvestmentService.get_rates()` pasa a devolver un `ResolvedRates` (compatible con el `Rates` actual) con, por moneda: `rate`, `source` pedida (`oficial|mep|blue|manual`), `effective_source`, `provider`, `as_of`, `stale`.

Resolución para USD (EUR igual con `oficial|blue|manual`):
1. `source = manual` → `fx_usd_ars` (como hoy), `as_of = fx_rates_updated_at`, `effective_source = "manual"`.
2. Automática → última fila de `fx_quotes` (`currency, kind` con mayor `quote_date`): `rate = sell`, `effective_source = kind`, `provider`, `as_of = source_updated_at`. Si la API cayó se sigue usando esa última conocida (es el fallback natural: la tabla nunca se vacía por un error).
3. Automática sin ninguna fila (deploy nuevo sin red) → si el usuario tiene `fx_usd_ars`, se usa con `effective_source = "manual_fallback"`; si no, `rate = null` y el par va a `missing_rates` como hoy.
- **Se convierte con la venta** (`sell`): es el número que se publica como "el dólar está a" y el que usa la gente; la compra se muestra al lado. Ver Preguntas abiertas.
- **`stale`** = `as_of` con más de 96 h (cubre fines de semana largos, en los que oficial y MEP no cotizan) o, para automáticas, `market_fetch_state.fx.last_success_at` con más de 6 h.
- Una sola lectura por request: las tablas son chicas y la consulta usa el índice; caché en proceso de 60 s para el "último por tipo" (se invalida al escribir el job en el mismo proceso; entre procesos alcanza con el TTL).

Todo lo que ya usa `get_rates` (resumen, patrimonio, `/finance/summary`) hereda la cotización automática sin cambios de contrato. `RatesOut` suma campos aditivos: `usd_source`, `usd_effective_source`, `usd_provider`, `usd_as_of`, `usd_stale`, `eur_source`, `eur_effective_source`, `eur_provider`, `eur_as_of`, `eur_stale`; `updated_at` pasa a ser el `as_of` de la cotización USD efectiva (con manual es el mismo `fx_rates_updated_at` de hoy, así los clientes viejos siguen mostrando "actualizada hace X" correcto).

`GET/PUT /api/v1/settings` suman `fx_usd_source` y `fx_eur_source` (enum validado, 422 si no). Cambiar la fuente no borra `fx_usd_ars`: volver a `manual` recupera la cotización propia. Editar el valor manual desde la UI manda también `fx_usd_source: "manual"`.

### D5. IPC y rendimiento real

**Serie**: job cada 6 h (`MARKET_INFLATION_REFRESH_HOURS`); primario ArgentinaDatos (`fecha` = último día del mes → `period` = día 1), respaldo datos.gob.ar (`representation_mode=percent_change`, ×100). Upsert por `period`; un respaldo no pisa un mes ya guardado por el primario salvo que difiera (revisión del INDEC: gana el primario). Sanidad: `-20 ≤ pct ≤ 100`, `period` no posterior al mes actual. Primera carga: la serie completa desde 2017-01 (una sola respuesta).

**Inflación acumulada de `[S, E)`** (`inflation.py`, puro, `Decimal` con precisión 28):
- Para cada mes `m` que se superpone con el período: `f_m = (1 + π_m/100) ^ (días_cubiertos_m / días_del_mes_m)` (prorrateo geométrico: supone inflación diaria uniforme dentro del mes). `factor = Π f_m`; `inflation_pct = (factor − 1) × 100`.
- Mes sin dato publicado (el actual siempre, y el anterior hasta ~el 12–15): `π_m` = último mes publicado; el resultado sale `estimated = true` con `estimated_months = ["2026-10"]`.
- Si `S` es anterior al primer mes de la serie → `null` con motivo `no_inflation_data`.

**Por activo** (`InvestmentOut.real_return`, null con `real_return_unavailable_reason`):
- Solo `currency = "ARS"` y `start_date` presente (motivos `currency`, `no_start_date`); `S = start_date`; `E` = hoy del usuario (`tz_offset_minutes`, como el resto), o `maturity_date` si es plazo fijo ya vencido (el devengado se frena ahí), o para activos cerrados `maturity_date` si pasó, si no la fecha de `updated_at`. `E − S < 1 día` o `S` futura → motivo `too_short`.
- `nominal_pct = (effective_value / invested − 1) × 100`; `real_pct = ((1 + nominal/100) / factor − 1) × 100`; todo redondeado a 2 decimales al salir.
- **Plazo fijo activo no vencido**: además `projected_at_maturity` con `nominal = interest_total / P` sobre `[start_date, maturity_date)`, siempre `estimated = true` si cubre meses sin publicar.
- Ejemplo: P = 1.000.000, TNA 30 %, del 2026-09-01 al 2026-10-01 (30 días), IPC sep = 1,9 % → nominal 2,47 % (24.657,53), inflación 1,90 %, real `1,0246575 / 1,019 − 1` = **0,56 %**.

**Agregado** (`InvestmentSummary.real_return_ars`): sobre los activos activos con `real_return` calculable, `nominal_pct = Σvalor/Σinvertido − 1`, `inflation_pct = Σ(invertido×factor)/Σinvertido − 1`, `real_pct = Σvalor / Σ(invertido×factor) − 1` (cuánto le ganó la cartera en pesos a la inflación ponderando por monto), `estimated`, `included_count`, `excluded_count`. `null` si no hay ninguno.

La serie se lee una vez por request (≤ 120 filas) con caché en proceso de 10 min.

### D6. Provider CoinGecko

- `crypto_assets.py`: mapeo curado `ticker → (coingecko_id, nombre)`: BTC→bitcoin, ETH→ethereum, USDT→tether, USDC→usd-coin, DAI→dai, SOL→solana, BNB→binancecoin, XRP→ripple, ADA→cardano, DOGE→dogecoin, TRX→tron, TON→the-open-network, DOT→polkadot, POL→polygon-ecosystem-token, LTC→litecoin, AVAX→avalanche-2, LINK→chainlink, XLM→stellar, BCH→bitcoin-cash, ATOM→cosmos, UNI→uniswap, SHIB→shiba-inu (lista inicial; se amplía en código). Los símbolos en CoinGecko son ambiguos (muchas monedas comparten ticker), por eso un mapeo curado y no `/search`.
- `PriceProvider` suma `def supports(ticker) -> bool` y `async def quote_many(tickers: set[str], currencies: set[str]) -> dict[tuple[str, str], PriceQuote]`; `quote()` queda como atajo sobre `quote_many`. `PRICE_PROVIDERS = {"coingecko": CoinGeckoProvider()}`.
- `quote_many` hace **un** `GET /simple/price?ids=<ids>&vs_currencies=<usd,ars,eur según uso>&include_last_updated_at=true` (la lista curada entra en una URL). Moneda del activo → `vs`: `USD`/`USDT` → `usd`, `ARS` → `ars`, `EUR` → `eur`. Sanidad: `0 < price ≤ 1e11`.
- `refresh_quotes(db) -> int` (deja de ser por usuario; el parámetro `user_id` queda opcional para tests): toma los pares `(ticker, currency)` distintos de inversiones `active` con `price_source = "coingecko"`; **si no hay ninguno no sale a la red**; consulta en lote, hace upsert en `market_prices` y un `UPDATE investments SET last_price, last_price_at WHERE price_source='coingecko' AND status='active' AND ticker=:t AND currency=:c` por par.
- Intervalo 10 min (`MARKET_CRYPTO_REFRESH_MINUTES`) → como máximo ≈ 4.320 consultas/mes, menos de la mitad de los 10.000 del Demo y lejos de 100/min. `429` → backoff respetando `Retry-After`.
- Key: `COINGECKO_API_KEY` opcional por env (header `x-cg-demo-api-key`); sin key usa el acceso público. Nunca en el repo; va en `docker-compose.prod.yml` y `.env.prod.example`.
- **Validación al crear/editar** (sobre el estado resultante, como las reglas de plazo fijo): `price_source = "coingecko"` exige `asset_type = "crypto"`, ticker soportado y `quantity > 0`; si no, 422 en español ("No tenemos cotización automática para ese ticker"). Al guardar, el service completa `last_price`/`last_price_at` desde `market_prices` si ya hay precio para ese par (sin HTTP en el request); si no, pone `market_fetch_state.crypto.next_run_at = now` para que el próximo ciclo (≤ 60 s) lo traiga. Mientras tanto la valuación cae a manual/invertido y la UI muestra "Esperando cotización".
- Pasar a `manual` conserva `last_price` pero `valuate()` ya lo ignora (regla existente). Con `coingecko` la cotización gana sobre `current_value` (precedencia de D4 de `finanzas-inversiones`); la UI oculta "valor actual".
- `InvestmentOut` suma `quote_provider` ("CoinGecko") y `quote_stale` (`last_price_at` con más de 1 h, o null).
- Atribución obligatoria: "Datos de CoinGecko" con link a coingecko.com junto a los precios automáticos (web y mobile).

### D7. API

Todas autenticadas (`get_current_user`), bajo el router `prefix="/finance/market"`, `tags=["finance"]`; sin datos por usuario salvo la preferencia.

| Método | Ruta | Response |
|---|---|---|
| GET | `/finance/market/fx` | `{usd: FxQuoteOut[], eur: FxQuoteOut[], last_success_at, degraded}`; `FxQuoteOut = {kind, label, buy, sell, provider, as_of, stale}`; `degraded = true` si el último intento falló o `last_success_at` > 6 h |
| GET | `/finance/market/inflation?months=12` (1..120) | `{series: [{period:"2026-09", pct}], last_published_period, estimate_pct}` |
| GET | `/finance/market/crypto-assets` | `[{ticker, name}]` (para el autocompletar y el switch) |
| GET/PUT | `/settings` | + `fx_usd_source`, `fx_eur_source` |
| GET | `/finance/investments*`, `/finance/net-worth`, `/finance/summary` | + campos aditivos de D4–D6 |

`schemas.py::ALLOWED_PRICE_SOURCES = {"manual"} ∪ PRICE_PROVIDERS.keys()`. El test guardia de rutas públicas no cambia (ninguna ruta nueva es pública).

### D8. Scheduler de datos de mercado y coordinación entre workers

- `run_market_data_scheduler()` en el `lifespan` (junto a los otros dos, cancelado al apagar), solo si `MARKET_DATA_ENABLED` (default `true`; los tests lo ponen en `false`). Ciclo cada 60 s; por cada fuente (`fx`, `inflation`, `crypto`) intenta tomar el **lease**:
  `UPDATE market_fetch_state SET lease_until = :now + 120s, last_attempt_at = :now WHERE source = :s AND next_run_at <= :now AND (lease_until IS NULL OR lease_until < :now)` → solo el worker con `rowcount == 1` consulta. Atómico en Postgres y SQLite, sobrevive reinicios y no depende de Redis (de N workers, uno solo sale a la red por fuente y ciclo).
- El lease se commitea **antes** de las llamadas HTTP (ninguna transacción abierta durante la red). Al terminar: éxito → `next_run_at = now + intervalo`, `lease_until = null`, `consecutive_failures = 0`, `last_success_at = now`; error → `consecutive_failures += 1`, `next_run_at = now + min(intervalo × 2^fallos, tope)` (tope 1 h para fx/cripto, 24 h para IPC), `last_error` truncado. Un worker que muere con el lease tomado lo libera solo al vencer (120 s).
- HTTP: un `httpx.AsyncClient` por ciclo, `Timeout(10, connect=5)`, `User-Agent: Can_cen/1.0`, sin reintentos inmediatos (el backoff es el reintento). Ninguna excepción sale del loop (log + sigue), igual que los otros schedulers.
- Retención de `fx_quotes` (730 días) una vez por día dentro del job `fx`.
- **Tests sin red**: los providers reciben el `httpx.AsyncClient` por parámetro y los tests usan `httpx.MockTransport` con respuestas grabadas (fixtures JSON con la forma real verificada). Un fixture `autouse` en `conftest.py` hace fallar cualquier request que no vaya por un `MockTransport`, para que ningún test pueda pegarle a la API real por accidente.

### D9. Web (`frontend/`)

- `src/types`: `FxQuote`, `MarketFx`, `InflationSeries`, `RealReturn`, `CryptoAsset`; `AppSettings` + `fx_usd_source`/`fx_eur_source`; `Investment` + `real_return`, `real_return_unavailable_reason`, `quote_provider`, `quote_stale`; `InvestmentSummary` + `real_return_ars`; `NetWorth.rates` + campos de D4.
- `src/api/endpoints.ts`: `fetchMarketFx`, `fetchInflation`, `fetchCryptoAssets` con mocks equivalentes (`VITE_MOCK_ENABLED`); los mocks de inversiones suman `real_return` y cotización automática. `src/hooks/useMarket.ts` (SWR `finance/market/fx` con `refreshInterval` 5 min). Cambiar la fuente revalida `settings`, `finance/net-worth`, `finance/investments/summary` y `finance/summary`.
- `FxRatesEditor.tsx` → tarjeta "Cotización": control segmentado **Oficial / MEP / Blue / Manual** para el dólar, las tres cotizaciones visibles (venta grande, compra chica) con "hace X · DolarAPI"; badge ámbar "desactualizada" si `stale`, aviso "Usamos tu cotización manual porque todavía no hay datos" si `manual_fallback`; en Manual, los inputs actuales. Fila de euro (Oficial / Blue / Manual) solo si hay activos en EUR.
- `NetWorthCard.tsx`: pie "Dólar MEP $ 1.563,90 · DolarAPI · hace 12 min".
- Tarjeta de activo (`InvestmentsSection.tsx`): chip "Real +0,56 %" (verde/rojo) con tooltip "Nominal 2,47 % · Inflación 1,90 % (sep 2026)"; chip "estimado" si corresponde; en plazo fijo "Al vencimiento: real ≈ +x %". Cripto automática: "Cotización automática · hace 4 min" (ámbar si `quote_stale`) y "Datos de CoinGecko". Resumen: "Tus inversiones en pesos le ganan/pierden x % a la inflación (n activos)".
- `InvestmentModal.tsx`: en cripto, switch "Cotización automática" habilitado si el ticker está en `crypto-assets` (autocompletar), exige cantidad y oculta "valor actual"; en tipos no plazo fijo, la fecha de inicio pasa a llamarse "Fecha de compra" con ayuda "para calcular el rendimiento contra la inflación".

### D10. Mobile (`C:\Proyectos\vida-personal-mobile`)

Mismo contrato: `src/types/index.ts`, `src/api/endpoints.ts` (`fetchMarketFx`, `fetchInflation`, `fetchCryptoAssets`; la preferencia se guarda con el `PUT /settings` existente vía `queued(...)`), `src/hooks/useInvestments.ts` (+ market). `FxRatesEditor.tsx` con `FilterChips` Oficial/MEP/Blue/Manual y las cotizaciones; `NetWorthCard.tsx` con el pie de fuente; tarjetas de `InvestmentsScreen.tsx` con chip de rendimiento real y de cotización automática; `InvestmentFormSheet.tsx` con el `Switch` de cotización automática. Sin textos de compra ni precios de la tienda (los "precios" acá son de mercado, no de la app).

## Dependencias

- **`finanzas-inversiones`**: este change se apoya en su código (ya implementado) y modifica dos de sus requisitos (deltas de `finance-investments` y `finance-net-worth`). Debe archivarse **antes** que este, o el archive de este fallará al no encontrar los requisitos a modificar. Sus tareas pendientes (verificación manual 10.x) no bloquean el diseño.
- **Migración**: `020_market_data` con `down_revision = "019_age_confirmation"` (el head al implementar; `registro-edad-minima` tomó el 019). Otros changes hermanos (`finanzas-recurrentes`, `registro-edad-minima`, `app-bloqueo-y-bienvenida`, …) también pueden agregar migraciones: al implementar se toma el siguiente número libre y el `down_revision` del head vigente, y se verifica un solo head.
- **`finanzas-exportar-importar`**: si importa inversiones reutilizando `InvestmentCreate`, debe aceptar `price_source = "coingecko"` (lo hereda solo) y no exportar las tablas globales de mercado. Las preferencias nuevas viajan con `user_preferences`.
- **`widgets-android`**: si muestra patrimonio o dólar, consume `/finance/net-worth` o `/finance/market/fx`; no requiere nada extra de este change.
- Sin relación con `buscador-global`, `habitos-recordatorios-inteligentes`, `app-bloqueo-y-bienvenida`, `registro-edad-minima`, `finanzas-recurrentes`.

## Risks / Trade-offs

- [APIs comunitarias sin SLA ni límites publicados (DolarAPI, ArgentinaDatos, Bluelytics)] → cadena de respaldo de tres fuentes, consultas desde un solo worker cada 15 min, última cotización conocida como fallback permanente y badge "desactualizada"; kill switch `MARKET_DATA_ENABLED`.
- [Licencia comercial del plan Demo de CoinGecko no explícita] → atribución visible, uso mínimo, provider desactivable por env; ver Pregunta abierta 3.
- [Dato erróneo de una fuente (ej. un cero o un salto de 10×)] → validación de rangos y descarte de saltos > 50 % contra la última conocida, con log.
- [Doble escritura entre workers] → lease atómico en la base; la unique de cada tabla atrapa la carrera residual.
- [El IPC del mes en curso no existe] → estimación con el último dato publicado, marcada "estimado" en la API y en la UI; se recalcula sola cuando el INDEC publica.
- [Prorrateo geométrico intra-mes es una aproximación] → documentado; el error es chico frente a la inflación mensual y es la convención habitual.
- [Rendimiento real solo para activos en pesos] → los demás muestran el motivo ("en dólares no se compara con la inflación local"); pregunta abierta para extenderlo.
- [`Numeric(20,8)` pierde precisión en monedas de precio ínfimo (ej. SHIB)] → aceptable para valuación (la cantidad multiplica); la lista curada evita la mayoría.
- [Cambio de fuente del dólar mueve el patrimonio de golpe] → es lo esperado; la tarjeta muestra qué dólar se está usando.
- [Un worker caído con el lease tomado] → el lease vence en 120 s.
- [Tests que salen a la red por error] → guarda `autouse` que falla ante cualquier request real.

## Migration Plan

1. Deploy backend con `020_market_data` (crea las 4 tablas, siembra `market_fetch_state`, agrega `fx_usd_source`/`fx_eur_source` con `manual` para quien ya tenía cotización). Cambios aditivos: clientes viejos siguen viendo los mismos campos (y `rates.updated_at` sigue teniendo sentido).
2. El primer ciclo del scheduler (≤ 60 s) carga dólar, euro y la serie del IPC completa; cripto recién cuando haya activos con `coingecko`.
3. Deploy web; build EAS mobile.
4. Rollback: `alembic downgrade 019_age_confirmation` borra las tablas de mercado y las dos columnas (los usuarios vuelven a su cotización manual, que nunca se tocó) y revertir el deploy. Las inversiones con `price_source = "coingecko"` deben pasarse a `manual` antes del downgrade (lo hace el propio `downgrade` con un `UPDATE`).

## Open Questions

1. **Dólar por defecto para usuarios nuevos** (o que nunca cargaron cotización): MEP, oficial o blue. Recomendación: **MEP** (legal, es el que usan los ahorristas para dolarizar y valuar).
2. **Precio para convertir**: venta, compra o promedio. Recomendación: **venta** (es el número público "el dólar está a"); se muestra la compra al lado.
3. **CoinGecko Demo y uso comercial**: la página de precios exige atribución en Demo y reserva la "licencia comercial" a los planes pagos; Can_cen vende plantillas aunque Inversiones es gratis. Recomendación: arrancar con Demo + atribución + key por env, consultar a CoinGecko por escrito antes del lanzamiento público y, si no lo permiten, pasar al plan pago más chico o apagar el provider con env (los activos vuelven a manual).
4. **Rendimiento real de activos en USD/EUR**: fuera de alcance. Recomendación: más adelante, pasándolos a pesos con la cotización histórica de la fecha de compra (ArgentinaDatos tiene histórico diario por tipo).
5. **Estimación de meses sin IPC**: último dato publicado vs. expectativas del REM del BCRA. Recomendación: **último dato** (simple, sin otra fuente), marcado "estimado".
6. **Otros tipos de dólar** (CCL, cripto, tarjeta, mayorista): se guardan pero la UI ofrece solo oficial/MEP/blue. Recomendación: así; sumar CCL si alguien lo pide.
7. **Lista de cripto soportadas**: recomendación: las ~22 de D6 (top por capitalización + stablecoins); ampliar a pedido.
8. **Fila de euro**: solo si hay activos en EUR (hereda la pregunta 3 de `finanzas-inversiones`). Recomendación: sí, solo con activos en EUR.

## Decisiones de producto confirmadas e implementación (2026-10-27)

Respuestas del usuario a las preguntas abiertas, tal como quedaron implementadas:

1. **Dólar por defecto**: MEP para usuarios nuevos; quien ya tenía una cotización manual queda en `manual`.
2. **Precio de conversión**: la **venta**, con la compra al lado.
3. **CoinGecko**: plan Demo + atribución "Datos de CoinGecko" + `COINGECKO_API_KEY` opcional por env. El provider se apaga con `MARKET_CRYPTO_ENABLED=false` (el scheduler no consulta cripto, `/crypto-assets` devuelve `[]` y no se aceptan altas con `coingecko`; los activos existentes conservan su último precio). `MARKET_DATA_ENABLED=false` apaga todo el scheduler. Acciones/CEDEARs fuera de alcance.
4. **Rendimiento real**: solo activos en ARS por ahora.
5. **Meses sin IPC**: se estiman con el último dato publicado y el resultado sale "estimado".
6. **Tipos de dólar**: se guardan todos, la UI muestra Oficial / MEP / Blue.
7. **Fila de euro**: solo si hay activos en EUR.

Diferencias de implementación respecto del diseño original:

- `PriceProvider.quote_many(pairs, client)` recibe los pares `{(ticker, moneda)}` y el `httpx.AsyncClient` (inyectable para tests) en vez de `(tickers, currencies)`; `refresh_quotes(db, client=None, user_id=None)`.
- `get_rates()` devuelve `(ResolvedRates, include_investments)`; `ResolvedRates` extiende `Rates` con un `RateInfo` por moneda.
- `stale` se calcula solo para cotizaciones automáticas (la manual del usuario no se marca: los clientes ya muestran su antigüedad).
- `MarketPrice`/`FxQuote` guardan `Numeric`; los jobs reciben la sesión y el cliente por parámetro (`refresh_fx(db, client, now)`).
- La fecha de inicio pasa a ser "Fecha de compra" y se acepta en todos los tipos de activo (el vencimiento sigue solo en plazo fijo, bonos, fondos y otros).
- El motivo `no_invested_amount` se suma a los motivos de `real_return_unavailable_reason`.
