import { mutate as globalMutate } from 'swr';
import { useApiSWR } from './useApiSWR';
import { isFinanceDataKey } from './financeKeys';
import { confirmImport, fetchImportPresets, fetchImports, undoImport } from '../api/endpoints';
import type { ImportConfirmRow } from '../types';

const IMPORTS_KEY = 'finance/imports';
const PRESETS_KEY = 'finance/import-presets';

export function useImportPresets() {
  return useApiSWR(PRESETS_KEY, fetchImportPresets);
}

export function useImports() {
  return useApiSWR(IMPORTS_KEY, fetchImports);
}

// Confirmar o deshacer una importación mueve lo mismo que crear o borrar un
// movimiento: lista, resumen, reportes, presupuestos y patrimonio, más el historial.
async function invalidateAfterImportChange() {
  await Promise.all([
    globalMutate(IMPORTS_KEY),
    globalMutate(isFinanceDataKey),
    globalMutate('finance/net-worth'),
  ]);
}

export async function confirmImportBatch(batchId: string, rows: ImportConfirmRow[]) {
  const batch = await confirmImport(batchId, rows);
  await invalidateAfterImportChange();
  return batch;
}

export async function undoImportBatch(batchId: string) {
  const batch = await undoImport(batchId);
  await invalidateAfterImportChange();
  return batch;
}
