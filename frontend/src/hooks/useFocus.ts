import { createResourceHooks } from './createResourceHooks';
import {
  fetchFocusSummary,
  fetchFocusSessions,
  startFocusSession,
  stopFocusSession,
  deleteFocusSession,
} from '../api/endpoints';
import type { FocusSession, FocusSummary } from '../types';

// Sin params y sin save() genérico: `startFocus`/`stopFocus` reemplazan al
// create/update habitual, así que sólo se reutilizan list+summary+revalidate+remove.
const focus = createResourceHooks<FocusSession, FocusSummary, Parameters<typeof fetchFocusSessions>[0]>({
  listKey: 'focus/sessions',
  summaryKey: 'focus/summary',
  fetchList: fetchFocusSessions,
  fetchSummary: fetchFocusSummary,
  deleteItem: deleteFocusSession,
  paramsInKey: false,
});

export const useFocusSummary = focus.useSummary;

export function useFocusSessions() {
  return focus.useList();
}

export async function startFocus(label?: string) {
  await startFocusSession(label);
  await focus.revalidate();
}

export async function stopFocus() {
  await stopFocusSession();
  await focus.revalidate();
}

export const removeFocusSession = focus.remove;
