import { mutate as globalMutate } from 'swr';
import { useApiSWR } from './useApiSWR';
import {
  fetchSettings,
  updateSettings,
  syncGoogleCalendar,
  disconnectGoogleCalendar,
} from '../api/endpoints';
import type { Settings } from '../types';

const SETTINGS_KEY = 'settings';

export function useSettings() {
  return useApiSWR(SETTINGS_KEY, fetchSettings);
}

export async function saveSettings(data: Partial<Settings>) {
  await updateSettings(data);
  await globalMutate(SETTINGS_KEY);
}

export async function syncGoogle() {
  const result = await syncGoogleCalendar();
  await globalMutate(SETTINGS_KEY);
  return result;
}

export async function disconnectGoogle() {
  await disconnectGoogleCalendar();
  await globalMutate(SETTINGS_KEY);
}
