## 1. Backend — Modelo y migración

- [x] 1.1 Crear `backend/app/modules/recurrentes/__init__.py` y `models.py` con `RecurringTransaction` y `RecurringOccurrence` (columnas, checks, índices y `UniqueConstraint(recurrence_id, occurrence_date)` de design D2; `Date` real, `DateTime(timezone=True)`, `Numeric(12,2)`; `interval_count`, nunca `interval`)
- [x] 1.2 Agregar `renewed_from_id` (FK a `investments.id`, índice único) a `Investment` en `backend/app/modules/inversiones/models.py`
- [x] 1.3 Registrar los modelos nuevos donde se importan para Alembic/`Base.metadata`
- [x] 1.4 Crear `backend/migrations/versions/021_recurring_transactions.py` (`down_revision = "020_market_data"`; renumerada desde 019 porque otros changes ocuparon 019 y 020): tablas, `ix_transactions_recurring_parent_id`, `investments.renewed_from_id` con `batch_alter_table`; `downgrade` inverso
- [x] 1.5 Verificar `alembic heads` = un solo head y `upgrade head` / `downgrade 020_market_data` / `upgrade head` en SQLite

## 2. Backend — Reglas de calendario

- [x] 2.1 `recurrentes/rules.py` (puro, sin DB): `Rule`, `compute_anchor(rule, start_date, from_date)`, `occurrence(rule, anchor, k)` desde el ancla con ajuste a último día del mes y 29/02 → 28/02, `next_after`, `first_on_or_after`, `occurrences_between` respetando `end_date`
- [x] 2.2 `rule_label(rule)` en español ("Todos los meses el día 5", "Cada 2 meses el día 10", "Todas las semanas los lunes", "Cada 15 días", "Todos los años el 15/03", sufijo "(o el último día del mes)" para día > 28)
- [x] 2.3 Helper `local_today(offset)` / `local_now(offset)` con fallback −180 (reusar el de `inversiones/valuation.py` si aplica)

## 3. Backend — Schemas, repository, service y API

- [x] 3.1 `recurrentes/schemas.py`: `RecurringCreate`/`RecurringUpdate` (reusar `Money` y `_check_enum` de `finanzas/schemas.py`; límites de `interval_count` por frecuencia; campos de regla obligatorios según frecuencia y en null los demás; `amount` null solo con `requires_confirmation`; fechas 1970–2100; offset −840..840; `generate_past`), `RecurringOut` (`state`, `rule_label`, `pending_count`, `last_amount`), `RecurringDetailOut`, `PreviewIn/Out`, `UpcomingOut`, `OccurrenceOut`, `ConfirmIn`
- [x] 3.2 Extraer de `FinanzasService.create_transaction` un builder sin `commit` (`build_transaction`) que valida enums y categoría propia; `create_transaction` lo usa y mantiene su comportamiento
- [x] 3.3 `recurrentes/repository.py`: toda query filtrada por `user_id`; `get`, `list(status)`, `create`, `update`, `delete` (borra ocurrencias y desvincula `transactions.recurring_parent_id`), `advance_cursor` (CAS con `rowcount`), `list_due(utc_today)`, ocurrencias pendientes, `claim_occurrence_status` (CAS `pending → confirmed/skipped`), última confirmada
- [x] 3.4 `recurrentes/service.py`: `materialize(rec, local_today, apply_window=False)` en una transacción (D5) con tope de 62 días/ocurrencias (D7), copia de cuenta/categoría a la transacción (D8), pendientes con `suggested_amount` (D6); crear (con `generate_past` y 422 si > 120), editar (recalcular ancla si cambia la regla), pausar, reanudar, borrar, preview, upcoming, confirmar/saltear idempotentes (200 repetido, 409 cruzado), actualizar el offset de la recurrencia en cada escritura
- [x] 3.5 `recurrentes/api_routes.py`: router `prefix="/finance/recurring"` con las rutas de design D10 (estáticas `/preview`, `/upcoming`, `/occurrences` antes de `/{id}`), todas con `get_current_user`; incluir en `backend/app/api/v1/router.py`
- [x] 3.6 `backend/app/api/v1/finance.py` + `finanzas/repository.py` + `finanzas/schemas.py`: filtro `recurrence_id` en `GET /finance/transactions` (y en `count`) y campo `recurrence_id` en `TransactionResponse`
- [x] 3.7 `CategoryRepository.delete` y `BankAccountRepository.delete`: desvincular `recurring_transactions.category_id` / `bank_account_id`
- [x] 3.8 Sumar `("recurring_occurrences", RecurringOccurrence)` y `("recurring_transactions", RecurringTransaction)` a `OWNED_TABLES` (`backend/app/modules/cuenta/service.py`) antes de `categories` y `bank_accounts`

## 4. Backend — Scheduler y push

- [ ] 4.1 `recurrentes/scheduler.py`: `_tick(now_utc)` que lista recurrencias debidas, filtra por ventana local 09:00–21:59 y fecha local, y llama a `materialize` por recurrencia atrapando y logueando errores individuales
- [ ] 4.2 `recurrentes/notifications.py`: armar los mensajes de design D9 (uno, pendiente, resumen agrupado por usuario y ciclo) con `format_money_es_ar`; enviar con `PushService.send_to_user` solo para `notify = true` y solo lo commiteado por ese worker; errores logueados
- [ ] 4.3 `run_recurring_scheduler()` alineado al minuto y arrancarlo/cancelarlo en el `lifespan` de `backend/app/main.py` junto a los otros dos

## 5. Backend — Renovación de plazo fijo

- [ ] 5.1 `inversiones/schemas.py`: `RenewFixedTermIn` (modo, TNA, `term_days` o `maturity_date` coherentes, `start_date`, `amount_collected` con `Money`, `register_interest_income`, categoría/cuenta/medio de pago del ingreso, offset), `RenewOut`, `RenewalChainOut`; `InvestmentOut` suma `renewed_from_id`, `renewed_to_id`, `can_renew`
- [ ] 5.2 `inversiones/service.py`: `renew()` atómico (precondiciones de design D11, cerrar el anterior con `current_value = amount_collected`, crear el nuevo con `renewed_from_id`, ingreso opcional por el interés vía `build_transaction`), 409 si ya se renovó (incluida la `IntegrityError` de la única), `renewals()` con tope 100, bloquear reabrir una inversión renovada, desvincular `renewed_from_id` al borrar el anterior, `renewed_to_id` calculado con una query por lista
- [ ] 5.3 `inversiones/api_routes.py`: `POST /finance/investments/{id}/renew` y `GET /finance/investments/{id}/renewals`, con `get_current_user`

## 6. Backend — Tests

- [x] 6.1 `backend/tests/test_recurring_rules.py` (puros): día 31 en abril/febrero/bisiesto, día 30 en febrero 2028, vuelta a 31 en marzo sin arrastre, bimestral anclado en el primer match, semanal por día de la semana y cada 2 semanas, cada 15 días, anual 29/02, `end_date` inclusive y cursor null, `rule_label`
- [x] 6.2 `backend/tests/test_recurring.py`: CRUD, validaciones 422 (monto 0 / > tope, enums inválidos como "Efectivo", regla incompleta, `interval_count` fuera de rango, fin < inicio, sin monto y sin confirmación), categoría/cuenta ajena → 404, creación el día debido genera en el request, `generate_past` (4 transacciones) y > 120 → 422, preview y upcoming
- [x] 6.3 Semántica: pausar/reanudar sin generar lo pausado, editar monto no toca lo generado, cambio de regla recalcula ancla, borrar plantilla conserva transacciones desvinculadas, borrar transacción generada no la regenera, borrar categoría/cuenta desvincula, filtro `recurrence_id` y campo en `TransactionResponse`
- [x] 6.4 Pendientes: `suggested_amount` (plantilla y luego último confirmado), confirmar con monto editado, confirmar dos veces → una transacción, saltear, confirmar salteada → 409, pendientes no suman al balance ni presupuestos
- [ ] 6.5 `backend/tests/test_recurring_scheduler.py`: 09:00 local genera y 08:59 no; offset −180 con fecha UTC distinta; offset +600; null → −180; fuera de ventana no genera; catch-up de 3 días (4 transacciones con fechas originales); tope de 62; plantilla pausada o terminada no genera
- [ ] 6.6 Idempotencia: dos `_tick` concurrentes (`asyncio.gather`) → una transacción; ciclos repetidos → una; "reinicio" sin Redis → no regenera; fallo a mitad (mock que levanta en la 2.ª transacción) → rollback total y reintento en el ciclo siguiente
- [ ] 6.7 Push (mock de `send_to_user`): una push por usuario y ciclo con textos y `data` correctos, resumen agrupado, `notify = false` sin push, generación por API sin push, Expo caído no afecta lo generado, usuario sin tokens
- [ ] 6.8 `backend/tests/test_fixed_term_renewal.py`: ambos modos con 1.000.000 / 30 % / 30 días (1.024.657,53), `amount_collected` editado, ingreso de 24.657,53 con y sin flag, no vencido → 422, no plazo fijo/cerrado → 422, ajeno → 404, doble renovación → 409, fechas y montos inválidos → 422, historial de 4 tramos, reabrir renovada → 422, borrar anterior/renovación, avisos de vencimiento solo para el nuevo
- [ ] 6.9 Aislamiento: sumar recurrentes, ocurrencias (confirmar/saltear) y renovación a `test_tenant_isolation.py` (→ 404) y verificar que listas, upcoming y pendientes no mezclan usuarios
- [ ] 6.10 `test_account.py`: el export incluye `recurring_transactions` y `recurring_occurrences` propios y no ajenos; el borrado no deja filas (incluida una cadena de inversiones renovadas); la guarda de `OWNED_TABLES` pasa
- [ ] 6.11 Confirmar que `test_infra.py::test_no_api_route_is_public_by_accident` pasa sin rutas públicas nuevas y correr `python -m pytest -q` completo sin regresiones

## 7. Web — API, tipos y hooks (`frontend/`)

- [ ] 7.1 Tipos en `src/types`: `Recurring`, `RecurringInput`, `RecurringRule`, `Occurrence`, `UpcomingItem`, `RenewFixedTermInput`, `RenewalChain`; `recurrence_id?` en `Transaction`; `renewed_from_id?`, `renewed_to_id?`, `can_renew?` en `Investment`
- [ ] 7.2 `src/api/endpoints.ts`: endpoints de design D14 con `tz_offset_minutes` en lecturas y `timezone_offset_minutes` en escrituras, `recurrence_id` en `fetchTransactions`; mocks con las mismas formas cuando `MOCK_ENABLED` (preview aproximada)
- [ ] 7.3 `src/hooks/useRecurring.ts` y extensión de `useInvestments.ts` con la invalidación de keys de la spec (incluye transacciones, summary, budgets y reports cuando corresponde)
- [ ] 7.4 Tests en `src/api/__tests__` y `src/hooks/__tests__`: URLs, params de tz, filtro `recurrence_id`, invalidación tras confirmar y tras renovar

## 8. Web — UI (`frontend/`)

- [ ] 8.1 `src/pages/Finance/RecurringSection.tsx`: "Para confirmar", "Próximos 30 días", lista con `rule_label`, próxima fecha, chip Activa/Pausada/Finalizada, acciones editar/pausar-reanudar/ver movimientos/borrar (confirmación "Las transacciones ya registradas se conservan"), estado vacío con ejemplos, dark mode
- [ ] 8.2 `src/pages/Finance/RecurringModal.tsx` (RHF + Zod sin `z.coerce`, patrón `TransactionModal`): campos según frecuencia, coma decimal, switches confirmación/aviso/anteriores, vista previa de 5 fechas con debounce
- [ ] 8.3 `src/pages/Finance/ConfirmOccurrenceModal.tsx`: monto sugerido editable, fecha, notas; botón Saltear
- [ ] 8.4 `FinancePage.tsx`: pestaña `recurrentes` ("Recurrentes") y banner de pendientes en Transacciones; `TransactionTable.tsx`: badge "Recurrente" con link (o "recurrencia eliminada") y acción "Hacer recurrente" que abre `RecurringModal` precargado
- [ ] 8.5 `InvestmentsSection.tsx` + `src/pages/Finance/RenewFixedTermModal.tsx`: botón "Renovar" si `can_renew`, modos con capital/interés/nuevo capital, monto cobrado editable, ingreso opcional con categoría/cuenta, TNA, plazo (chips 30/60/90/180/365 o fecha), inicio, vista previa; "Historial de renovaciones" en el detalle
- [ ] 8.6 Tests de componentes: modal de recurrente (validación, campos por frecuencia, día 31 muestra la ayuda), confirmación de pendiente, modal de renovación (1.024.657,53 y 24.657,53 en la vista previa), badge en la tabla
- [ ] 8.7 `npx vitest run --maxWorkers=2`, `npm run build` y lint sin errores

## 9. Mobile — API, tipos y hooks (`C:\Proyectos\vida-personal-mobile`)

- [ ] 9.1 [mobile] Tipos en `src/types` (recurrentes, ocurrencias, upcoming, renovación; `recurrence_id` en transacciones; `renewed_*`/`can_renew` en inversiones)
- [ ] 9.2 [mobile] `src/api/endpoints.ts`: endpoints de recurrentes y renovación; escrituras con `queued('...')` y `timezone_offset_minutes`; `preview`/`upcoming` solo online
- [ ] 9.3 [mobile] `src/hooks/useRecurring.ts` y extensión de `src/hooks/useInvestments.ts` con la misma invalidación que la web

## 10. Mobile — UI (`C:\Proyectos\vida-personal-mobile`)

- [ ] 10.1 [mobile] `src/screens/RecurringScreen.tsx`: "Para confirmar", próximos 30 días, `SectionList` Activas/Pausadas/Finalizadas, estados vacío/cargando/error, pausar/reanudar/borrar con `Alert`
- [ ] 10.2 [mobile] `src/components/RecurringFormSheet.tsx` (`BottomSheet`, `PickerField`, `NumberStepper`, `FilterChips` de días, `DateField`, `Switch`, `decimal-pad` + `parseDecimal`, vista previa con red) y `src/components/ConfirmOccurrenceSheet.tsx`
- [ ] 10.3 [mobile] Registrar `Recurring` en `FinanceStack` (`src/navigation/TabNavigator.tsx`, `FinanceStackParamList`) con `create`/`occurrenceId` y `useCreateParam`
- [ ] 10.4 [mobile] `src/screens/FinanceScreen.tsx`: tile "Recurrentes" (`repeat`) en `TOOLS` (5 tiles, último a lo ancho) y aviso de pendientes que abre Recurrentes
- [ ] 10.5 [mobile] `src/components/QuickCreateSheet.tsx`: opción "Recurrente" → `FinanceTab` › `Recurring` con `create: true`
- [ ] 10.6 [mobile] `src/lib/notifications.ts`: `recurring_generated`/`recurring_summary` → Recurrentes; `recurring_confirm` → Recurrentes con `occurrenceId` (sin error si ya se resolvió), en caliente y arranque en frío
- [ ] 10.7 [mobile] Inversiones: "Renovar" en la tarjeta / `InvestmentFormSheet` si `can_renew` → `src/components/RenewFixedTermSheet.tsx`; historial de renovaciones; badge "Recurrente" en la lista de transacciones
- [ ] 10.8 [mobile] Sin textos de compra/precios; `npx tsc --noEmit` y tests del repo mobile en verde

## 11. Verificación contra el backend real (no mock)

- [ ] 11.1 Aplicar la migración en Postgres (PGlite vía npm o docker) con `upgrade`/`downgrade`/`upgrade`, y correr por API un CRUD de recurrentes, confirmación y renovación: montos límite y enums inválidos dan 422, no 500; borrar categoría/cuenta usada por una recurrencia funciona en Postgres
- [ ] 11.2 Backend real con 2+ workers de gunicorn (con y sin Redis): recurrencia diaria con offset ajustado para caer en la ventana → una sola transacción y una sola push por ciclo; reiniciar el proceso no duplica
- [ ] 11.3 Simular caída: frenar el backend, mover `next_occurrence_date` 3 días atrás y levantar → 4 transacciones con fechas originales y una push resumen
- [ ] 11.4 Web con `VITE_MOCK_ENABLED=false`: crear sueldo mensual, alquiler, Netflix y luz con confirmación; vista previa con día 31; pausar/reanudar; confirmar la luz editando monto; badge y filtro en transacciones; borrar una plantilla y ver que sus transacciones siguen
- [ ] 11.5 Web: renovar un plazo fijo vencido en ambos modos (con ingreso del interés) y ver Patrimonio, el historial y que el anterior quedó cerrado
- [ ] 11.6 Mobile (build lan o Expo contra el backend real): tile y "+" → Recurrentes, alta con coma decimal, confirmación desde la push (tap en caliente y en frío), cola offline de una confirmación sin duplicar, "Renovar" en Inversiones
- [ ] 11.7 Export de cuenta contiene las tablas nuevas; borrar una cuenta de prueba con recurrencias, pendientes y renovaciones no deja filas
- [ ] 11.8 Correr `openspec validate finanzas-recurrentes --strict` y marcar las tareas completadas
