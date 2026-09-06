import { mutate as globalMutate } from 'swr';
import { useApiSWR } from './useApiSWR';
import {
  fetchFocusSummary,
  fetchFocusSessions,
  startFocusSession,
  stopFocusSession,
  deleteFocusSession,
} from '../api/endpoints';

const SUMMARY_KEY = 'focus/summary';
const SESSIONS_KEY = 'focus/sessions';

export function useFocusSummary() {
  return useApiSWR(SUMMARY_KEY, fetchFocusSummary);
}

export function useFocusSessions() {
  return useApiSWR(SESSIONS_KEY, () => fetchFocusSessions());
}

async function revalidate() {
  await Promise.all([globalMutate(SUMMARY_KEY), globalMutate(SESSIONS_KEY)]);
}

export async function startFocus(label?: string) {
  await startFocusSession(label);
  await revalidate();
}

export async function stopFocus() {
  await stopFocusSession();
  await revalidate();
}

export async function removeFocusSession(id: string) {
  await deleteFocusSession(id);
  await revalidate();
}
