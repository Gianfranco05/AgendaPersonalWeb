## 1. Pagination Infrastructure

- [x] 1.1 Crear `app/api/v1/schemas.py` con `PaginatedResponse[T]` genérico (items, total, page, page_size)
- [x] 1.2 Actualizar `GET /api/v1/finance/transactions` para usar `PaginatedResponse[TransactionResponse]`
- [x] 1.3 Verificar que los filtros (date_from, date_to, transaction_type, category_id) sigan funcionando con el nuevo response

## 2. Notes Schema Consolidation

- [x] 2.1 Reemplazar `NoteCreateRequest` inline por `NoteCreate` de `app.modules.anotaciones.schemas` en el endpoint POST
- [x] 2.2 Reemplazar `NoteUpdateRequest` inline por `NoteUpdate` de `app.modules.anotaciones.schemas` en el endpoint PUT
- [x] 2.3 Verificar que todos los campos del request original estén cubiertos (title, content, color, tag_names, is_pinned, is_archived)

## 3. Soft-Delete Verification

- [x] 3.1 Confirmar que `DELETE /api/v1/finance/transactions/{id}` usa `service.delete_transaction()` que llama a `repository.delete()` (soft-delete con is_deleted=True, deleted_at)
- [x] 3.2 Agregar test que verifique que una transacción eliminada no aparece en listado

## 4. Testing

- [x] 4.1 Escribir test para paginación de transactions (verificar items, total, page, page_size)
- [x] 4.2 Escribir test para filtros combinados en transactions list
- [x] 4.3 Escribir test para CRUD completo de notes vía API
- [x] 4.4 Escribir test para CRUD completo de events vía API con rango de fechas
- [x] 4.5 Escribir test para goals list + create + habit checkin
- [x] 4.6 Escribir test para settings get + update
