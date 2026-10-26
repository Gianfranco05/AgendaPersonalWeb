## Why

Con `finanzas-inversiones` el usuario registra plazos fijos, dólares y cripto, pero todo lo que depende del mercado lo carga a mano: la cotización del dólar (`fx_usd_ars`) envejece en días y deja un patrimonio engañoso, el precio de la cripto hay que actualizarlo activo por activo, y no hay forma de saber si un plazo fijo le ganó a la inflación, que es la pregunta que se hace cualquier ahorrista argentino. Existen hoy (2026) fuentes públicas y gratuitas para las tres cosas (DolarAPI, ArgentinaDatos, CoinGecko), y `finanzas-inversiones` ya dejó el punto de extensión (`PRICE_PROVIDERS`, `last_price`, `value_source="quote"`) pensado para enchufarlas.

## What Changes

- **Cotización del dólar automática**: el server consulta periódicamente (no por request de cada usuario) DolarAPI (`/v1/dolares` y `/v1/cotizaciones/eur`) con respaldo en Bluelytics y ArgentinaDatos, guarda la última cotización de cada tipo (oficial, MEP/bolsa, blue, más CCL/mayorista/cripto/tarjeta que vienen en la misma respuesta) y un histórico diario mínimo (cierre por día, 2 años). EUR oficial y blue también.
- **El usuario elige con qué dólar convierte sus totales**: nueva preferencia `fx_usd_source` = `oficial` | `mep` | `blue` | `manual` (y `fx_eur_source` = `oficial` | `blue` | `manual`). `manual` sigue existiendo como override con los campos actuales `fx_usd_ars`/`fx_eur_ars`. Los usuarios que ya tenían una cotización cargada quedan en `manual` (no cambia lo que ven); los demás arrancan en `mep`.
- **Transparencia y fallback**: la API informa tipo, fuente ("DolarAPI"), fecha de la cotización y si está desactualizada; la UI muestra "actualizado hace X · fuente". Si la API cae se usa la última cotización conocida; si nunca hubo una (deploy nuevo sin red) se cae a la manual del usuario si existe, y si no, al aviso actual de cotización faltante.
- **Inflación (IPC INDEC)**: el server guarda la serie mensual de variación del IPC nacional (ArgentinaDatos `/v1/finanzas/indices/inflacion`, respaldo en la API de Series de Tiempo de datos.gob.ar, serie `148.3_INIVELNAL_DICI_M_26`).
- **Rendimiento real**: para activos en ARS con fecha de inicio (plazo fijo sobre todo) la API calcula rendimiento nominal, inflación acumulada del período (prorrateando meses parciales) y rendimiento real %; para el plazo fijo además el real proyectado al vencimiento. Los meses todavía sin IPC publicado (el INDEC lo publica a mediados del mes siguiente) se estiman con el último dato y el resultado se marca "estimado". El resumen de inversiones suma un rendimiento real agregado de la cartera en pesos.
- **Cripto automática (CoinGecko)**: un provider `coingecko` registrado en `PRICE_PROVIDERS` cotiza los activos `crypto` con ticker conocido (BTC, ETH, USDT, USDC, SOL…) mediante un mapeo curado ticker→id, en **una sola consulta en lote** cada 10 minutos para todos los tickers en uso, en la moneda del activo (USD/USDT/ARS/EUR). El activo pasa a `value_source="quote"` con `last_price`/`last_price_at`. El usuario elige por activo "automática" o "manual". API key Demo opcional por variable de entorno; atribución "Datos de CoinGecko" en la UI.
- **Coordinación entre workers sin duplicar llamadas**: un único scheduler de datos de mercado por proceso, con un *lease* atómico en la base (más Redis si está) para que de N workers de gunicorn solo uno consulte cada fuente por ciclo; timeouts cortos, backoff ante errores y validación de rangos de los datos recibidos.
- **UI web y mobile**: selector de tipo de dólar en la tarjeta de cotización de Inversiones (con las tres cotizaciones a la vista), badges de fuente/actualización/desactualizado, switch "Cotización automática" en el alta/edición de cripto, rendimiento real en la tarjeta del activo y en el resumen.
- **BREAKING (solo contrato interno de `finanzas-inversiones`, sin clientes en producción)**: `price_source` pasa a aceptar `coingecko` (antes solo `manual`); `PriceProvider` suma un método de consulta en lote.

### Fuera de alcance

- **Acciones y CEDEARs automáticos**: no hay una fuente gratuita, oficial y con términos claros. BYMA vende sus datos de mercado (productos de datos pagos); las alternativas gratuitas (endpoints no documentados de BYMA Open Data, librerías comunitarias, scraping de Rava o Yahoo Finance) no tienen términos de uso ni garantía de continuidad. Siguen manuales; el punto de extensión queda listo para un provider futuro.
- Rendimiento real de activos en USD/EUR (habría que deflactar por inflación de EE.UU. o pasar a pesos con la cotización histórica de la fecha de inicio): queda como pregunta abierta.
- Gráficos de la evolución del dólar o de la inflación; alertas de precio; conversión del balance de transacciones (sigue asumido ARS).
- Cotización de USDT distinta de 1:1 con USD.

## Capabilities

### New Capabilities
- `market-fx-rates`: obtención periódica de cotizaciones del dólar (oficial, MEP, blue, y otras) y del euro desde fuentes públicas, caché e histórico diario en la base, fallback, frescura, preferencia del usuario sobre qué tipo usar y su aplicación a los totales y al patrimonio.
- `inflation-real-return`: serie mensual del IPC, inflación acumulada de un período con meses parciales y estimados, rendimiento real por activo y agregado, y su presentación en web y mobile.
- `crypto-price-quotes`: provider CoinGecko enchufado en `PRICE_PROVIDERS`, mapeo ticker→id, consulta en lote, actualización de `last_price`, elección automática/manual por activo, frescura y atribución.
- `market-data-scheduler`: el job en el lifespan que coordina las fuentes externas entre workers (lease atómico), timeouts, backoff, validación de datos, kill switch y la garantía de que los tests nunca salen a la red.

### Modified Capabilities
- `finance-investments` (delta sobre el change `finanzas-inversiones`, todavía sin archivar): el requisito "Pluggable price providers extension point" deja de exigir solo `manual` y pasa a aceptar los providers registrados (`coingecko`).
- `finance-net-worth` (delta sobre `finanzas-inversiones`): el requisito "User-managed exchange rates" pasa a ser una de las fuentes posibles de la cotización efectiva, junto a las automáticas.

## Impact

- **Backend**: nuevo módulo `backend/app/modules/mercado/` (models, schemas, repository, service, providers `dolarapi.py`/`bluelytics.py`/`argentinadatos.py`/`datos_gob.py`/`coingecko.py`, `inflation.py` con cálculos puros, `scheduler.py`, `api_routes.py` bajo `/api/v1/finance/market`); `backend/app/modules/inversiones/valuation.py` (registro del provider, `quote_many`, `refresh_quotes` real), `inversiones/schemas.py` (`price_source`, `real_return`), `inversiones/service.py` (`get_rates` resuelve la fuente efectiva, resumen con rendimiento real); `backend/app/api/v1/settings.py` + `ajustes/models.py` (`fx_usd_source`, `fx_eur_source`); `backend/app/main.py` (lifespan arranca el scheduler de mercado); `backend/app/config.py` (variables nuevas); migración `019_market_data` (o el número libre al implementar).
- **Tablas nuevas globales (sin `user_id`)**: `fx_quotes`, `inflation_monthly`, `market_prices`, `market_fetch_state`. No van en `OWNED_TABLES` (no son datos del usuario); las columnas nuevas de `user_preferences` salen solas en el export.
- **Config/infra**: `MARKET_DATA_ENABLED`, `COINGECKO_API_KEY` (opcional), intervalos configurables; agregados a `docker-compose.prod.yml` y `.env.prod.example`. Sin dependencias nuevas (`httpx` ya está). El CSP del frontend no cambia: los clientes nunca llaman a las APIs externas.
- **Tests**: nuevos `backend/tests/test_market_fx.py`, `test_market_inflation.py`, `test_market_crypto.py`, `test_market_scheduler.py`, con `httpx.MockTransport` y una guarda que falla si un test intenta salir a la red; extensiones en `test_investments*.py`, `test_ajustes.py`, `test_infra.py`.
- **Web** (`frontend/`): `FxRatesEditor.tsx`, `NetWorthCard.tsx`, `InvestmentsSection.tsx`, `InvestmentModal.tsx`, `src/api/endpoints.ts` (+ mocks), `src/hooks/useInvestments.ts` (+ `useMarket`), `src/types`.
- **Mobile** (`C:\Proyectos\vida-personal-mobile`): `src/components/FxRatesEditor.tsx`, `NetWorthCard.tsx`, `InvestmentFormSheet.tsx`, `src/screens/InvestmentsScreen.tsx`, `src/api/endpoints.ts`, `src/hooks/useInvestments.ts`, `src/types/index.ts`.
