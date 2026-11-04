## Why

Finanzas hoy solo conoce ingresos, egresos, presupuestos, cuentas y metas de ahorro: la plata que la persona tiene invertida (plazos fijos, acciones/CEDEARs, cripto, bonos, FCI, dólares, inmuebles) no aparece en ningún lado, así que el "balance" de la app muestra solo el efectivo y no lo que realmente tiene. En Argentina el plazo fijo y la dolarización son la forma más común de ahorrar, y los vencimientos se olvidan: hace falta registrarlos, ver cuánto rinden y que la app avise antes de que venzan.

## What Changes

- **Nueva sección "Inversiones" dentro de Finanzas** (gratis, parte del módulo base `finance`, no es una plantilla paga) para registrar activos de estos tipos: acciones/CEDEARs, plazo fijo, cripto, bonos, FCI, dólares/divisas, inmueble, vehículo y otros. Cada activo guarda: tipo, nombre, ticker (opcional), moneda, cantidad (opcional), monto invertido, valor actual, TNA % (opcional), fecha de inicio y de vencimiento (opcionales salvo en plazo fijo), entidad/broker (opcional) y notas. Un activo se puede cerrar (deja de sumar) sin borrarse.
- **Valuación manual + cálculo automático donde se puede** (decisión del usuario): el usuario carga monto invertido y valor actual. Para plazo fijo la app calcula sola el interés esperado, el monto al vencimiento y el devengado a hoy (interés simple, convención argentina TNA/365). Ganancia/pérdida y % por activo.
- **Punto de extensión para cotizaciones automáticas** (sin implementarlas): el modelo guarda `ticker`, `price_source`, `last_price` y `last_price_at`, y la valuación pasa por un servicio con proveedores enchufables (`manual` es el único en esta etapa). Sumar CoinGecko/BYMA más adelante no requiere migrar el esquema.
- **Multimoneda con cotización propia del usuario**: cada activo en su moneda (ARS, USD, USDT, EUR). Los totales se muestran en ARS y en USD usando la cotización que el usuario carga y actualiza (USD→ARS obligatoria para convertir, EUR→ARS opcional; USDT se toma 1:1 con USD). Se guarda con fecha de actualización. Sin cotización cargada se muestran solo subtotales por moneda y se invita a cargarla.
- **Patrimonio**: nuevo resumen = balance disponible + valor actual de las inversiones activas, en ARS y USD.
- **Preferencia "Sumar inversiones al balance"** (default apagada): encendida, la tarjeta de balance de Inicio (web y mobile) y de Finanzas muestra el total incluyendo inversiones, con el tramo de inversiones diferenciado (otro color + etiqueta) para distinguir efectivo de inversiones. El campo `balance` de `/finance/summary` no cambia de significado: se agregan campos nuevos (cambio aditivo, no rompe clientes viejos).
- **Avisos de vencimiento por push**: el día anterior y el día del vencimiento, a las 9:00 hora local del usuario, reutilizando la infraestructura de push remota (módulo `push` + scheduler en el lifespan) con claim `SET NX` en Redis por (activo, aviso, día) igual que los recordatorios, más una marca persistente en la fila para no repetir tras un reinicio.
- **Mobile** (`C:\Proyectos\vida-personal-mobile`): pantalla Inversiones (nueva herramienta en la grilla de Finanzas), alta rápida "Inversión" en el menú "+" de Inicio, Patrimonio en la `BalanceCard` respetando la preferencia, y tocar la push abre Inversiones.
- **Web** (`frontend/`): nueva pestaña "Inversiones" en Finanzas con tarjeta de Patrimonio, editor de cotización, lista agrupada por tipo, modal de alta/edición y el toggle; el widget de Finanzas del Dashboard respeta la preferencia.
- Export y borrado de cuenta incluyen la tabla nueva.

### Fuera de alcance

- **Cotizaciones en vivo** (cripto, acciones, dólar MEP/CCL/oficial): solo queda el punto de extensión.
- **Cálculos impositivos** (Ganancias, Bienes Personales, retenciones).
- **Historial de compras/ventas por activo (modelo de "movimientos")**: no se agrega. Con valuación manual, un activo es una posición (cantidad + invertido + valor actual) y eso alcanza para patrimonio, ganancia y vencimientos. Un modelo de movimientos obliga a resolver costo promedio/FIFO, ventas parciales y realización de ganancias, que solo tienen sentido con cotizaciones automáticas; se puede sumar después como tabla hija (`investment_movements`) sin cambiar `investments`. Recomprar o renovar un plazo fijo se registra editando el activo o creando uno nuevo y cerrando el anterior.
- Mover plata entre efectivo e inversiones como transacción automática (constituir un plazo fijo no genera un egreso; el usuario decide si lo registra).
- Notificaciones por email; aviso configurable (horario/días de anticipación) — queda fijo en 9:00, día anterior y día del vencimiento.
- Conversión multimoneda del balance de transacciones: el balance actual suma montos sin mirar moneda y se asume en ARS (comportamiento existente, no se toca).

## Capabilities

### New Capabilities
- `finance-investments`: CRUD de activos de inversión por usuario, validaciones y límites, tipos de activo, valuación (manual, plazo fijo calculado, extensión para cotizaciones), ganancia/pérdida, días al vencimiento y resumen por moneda/tipo.
- `finance-net-worth`: cotización del usuario (USD/EUR→ARS), conversión y redondeo de totales, cálculo de Patrimonio, preferencia "Sumar inversiones al balance" y su presentación diferenciada en web y mobile.
- `investment-maturity-alerts`: push el día anterior y el día del vencimiento a las 9:00 locales, deduplicada entre workers y reinicios.

### Modified Capabilities
- `real-api-finance`: `GET /api/v1/finance/summary` suma campos aditivos (valor de inversiones en ARS, preferencia de inclusión, patrimonio) sin cambiar `balance`; se agregan las llamadas e invalidación de caché de inversiones.

## Impact

- **Backend**: nuevo módulo `backend/app/modules/inversiones/` (models, schemas, repository, service, valuation, scheduler, api_routes); router incluido en `backend/app/api/v1/router.py`; `backend/app/api/v1/finance.py` (`/summary` aditivo); `backend/app/api/v1/settings.py` + `backend/app/modules/ajustes/models.py` (cotización y toggle); `backend/app/main.py` (lifespan arranca el scheduler de vencimientos); helper compartido de claim en Redis extraído de `backend/app/modules/recordatorios/scheduler.py`; `backend/app/modules/cuenta/service.py` (`OWNED_TABLES`); migración `backend/migrations/versions/018_investments.py` (revisa `017_withdrawal_requests`).
- **Tests**: nuevos `backend/tests/test_investments.py`, `test_investments_valuation.py`, `test_investment_alerts.py`; extensiones en `test_tenant_isolation.py`, `test_account.py`, `test_api_finance.py`, `test_ajustes.py`.
- **Web**: `frontend/src/pages/Finance/` (nueva `InvestmentsSection.tsx`, `InvestmentModal.tsx`, `NetWorthCard.tsx`), `FinancePage.tsx`, `pages/Dashboard/FinanceWidget.tsx`, `src/api/endpoints.ts` (+ mock), `src/hooks/useInvestments.ts`, `src/types`.
- **Mobile** (`C:\Proyectos\vida-personal-mobile`): `src/screens/InvestmentsScreen.tsx`, `src/navigation/TabNavigator.tsx`, `src/screens/FinanceScreen.tsx` (grilla de herramientas), `src/components/QuickCreateSheet.tsx`, `src/components/BalanceCard.tsx`, `src/api/endpoints.ts`, `src/hooks/useInvestments.ts`, `src/types`, manejo del tap de notificaciones.
- **Infra**: sin dependencias nuevas; Redis opcional como hoy. Un loop más en el lifespan por worker.
