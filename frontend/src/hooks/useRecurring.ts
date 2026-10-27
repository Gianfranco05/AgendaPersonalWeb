import { mutate as globalMutate } from 'swr';
import { useApiSWR } from './useApiSWR';
import { isFinanceDataKey } from './financeKeys';
import {
  fetchRecurring,
  fetchOccurrences,
  fetchUpcomingRecurring,
  createRecurring,
  updateRecurring,
  deleteRecurring,
  pauseRecurring,
  resumeRecurring,
  confirmOccurrence,
  skipOccurrence,
} from '../api/endpoints';
import type { ConfirmOccurrenceInput, Recurring, RecurringInput } from '../types';

export type RecurringStatusFilter = 'active' | 'paused' | 'all';

export const RECURRING_KEY = 'finance/recurring';
export const OCCURRENCES_KEY = 'finance/recurring/occurrences';
export const UPCOMING_KEY = 'finance/recurring/upcoming';

export function useRecurring(status: RecurringStatusFilter = 'all') {
  return useApiSWR([RECURRING_KEY, status], () => fetchRecurring(status));
}

/** Pendientes de confirmación (montos variables). */
export function usePendingOccurrences() {
  return useApiSWR([OCCURRENCES_KEY, 'pending'], () => fetchOccurrences('pending'));
}

export function useUpcomingRecurring(days = 30) {
  return useApiSWR([UPCOMING_KEY, days], () => fetchUpcomingRecurring(days));
}

// Toda mutación de recurrentes mueve la lista, los pendientes y los próximos.
function isRecurringKey(key: unknown): boolean {
  return Array.isArray(key) && typeof key[0] === 'string' && key[0].startsWith(RECURRING_KEY);
}

async function invalidateRecurring(includeFinanceData = false) {
  await Promise.all([
    globalMutate(isRecurringKey),
    ...(includeFinanceData ? [globalMutate(isFinanceDataKey)] : []),
  ]);
}

/** Crea o edita. Crear con "registrar los anteriores", o editar la regla de una
 *  activa que vence hoy, puede generar transacciones: también se revalidan. */
export async function saveRecurring(existing: Recurring | null, data: RecurringInput) {
  if (existing) {
    await updateRecurring(existing.id, data);
  } else {
    await createRecurring(data);
  }
  await invalidateRecurring(true);
}

export async function setRecurringPaused(id: string, paused: boolean) {
  if (paused) {
    await pauseRecurring(id);
    await invalidateRecurring();
  } else {
    // Reanudar puede generar en el acto lo que toca hoy.
    await resumeRecurring(id);
    await invalidateRecurring(true);
  }
}

/** Borrar la plantilla desvincula sus transacciones (siguen en la lista). */
export async function removeRecurring(id: string) {
  await deleteRecurring(id);
  await invalidateRecurring(true);
}

export async function confirmPending(id: string, data: ConfirmOccurrenceInput) {
  await confirmOccurrence(id, data);
  await invalidateRecurring(true);
}

export async function skipPending(id: string) {
  await skipOccurrence(id);
  await invalidateRecurring();
}
