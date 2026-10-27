// Claves SWR de Finanzas que se mueven cuando se crean movimientos por una vía
// que no es el formulario de transacciones (recurrentes confirmadas o
// generadas, interés de una renovación): lista de transacciones, resumen,
// presupuestos y reportes.
export function isFinanceDataKey(key: unknown): boolean {
  if (Array.isArray(key)) {
    return key[0] === 'finance/transactions' || key[0] === 'finance/budgets';
  }
  return key === 'finance/summary' || key === 'finance/reports';
}
