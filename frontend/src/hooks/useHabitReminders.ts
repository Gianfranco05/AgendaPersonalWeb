import { useEffect, useRef } from 'react';
import { mutate as globalMutate } from 'swr';
import { useApiSWR } from './useApiSWR';
import {
  fetchHabitReminderSettings,
  updateHabitReminderSettings,
  fetchHabitReminderToday,
} from '../api/endpoints';
import type { HabitReminderSettings } from '../types';

export const HABIT_REMINDER_SETTINGS_KEY = 'habit-reminders/settings';
export const HABIT_REMINDER_TODAY_KEY = 'habit-reminders/today';

export function useHabitReminderSettings() {
  return useApiSWR(HABIT_REMINDER_SETTINGS_KEY, fetchHabitReminderSettings);
}

export function useHabitReminderToday() {
  return useApiSWR(HABIT_REMINDER_TODAY_KEY, fetchHabitReminderToday);
}

/** Revalida la vista del día: lo que se avisa cambia al marcar o editar un hábito. */
export async function refreshHabitReminderToday() {
  await globalMutate(HABIT_REMINDER_TODAY_KEY);
}

export async function saveHabitReminderSettings(
  patch: Partial<Omit<HabitReminderSettings, 'has_push_devices'>>,
) {
  await updateHabitReminderSettings(patch);
  await globalMutate(HABIT_REMINDER_SETTINGS_KEY);
  await globalMutate(HABIT_REMINDER_TODAY_KEY);
}

/**
 * Resincroniza el huso horario guardado cuando el de este navegador cambió
 * (viaje, horario de verano). Solo si los avisos están encendidos y hay algún
 * dispositivo con push: si no, no hay nada que corregir. Una vez por valor.
 */
export function useSyncReminderOffset(settings: HabitReminderSettings | undefined) {
  const syncedFor = useRef<number | null>(null);
  useEffect(() => {
    if (!settings || !settings.enabled || !settings.has_push_devices) return;
    const local = -new Date().getTimezoneOffset();
    if (settings.timezone_offset_minutes === local || syncedFor.current === local) return;
    syncedFor.current = local;
    saveHabitReminderSettings({ timezone_offset_minutes: local }).catch((err) => {
      syncedFor.current = null;
      console.error('[HabitReminders] no se pudo actualizar el huso horario', err);
    });
  }, [settings]);
}
