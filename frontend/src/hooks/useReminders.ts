import { useEffect, useRef, useState } from 'react';
import { mutate as globalMutate } from 'swr';
import { useApiSWR } from './useApiSWR';
import {
  fetchReminders,
  createReminder,
  updateReminder,
  deleteReminder,
} from '../api/endpoints';
import type { Reminder } from '../types';

const REMINDERS_KEY = 'reminders';

export function useReminders() {
  return useApiSWR(REMINDERS_KEY, fetchReminders);
}

export async function saveReminder(
  reminder: Reminder | null,
  data: Omit<Reminder, 'id'>,
) {
  if (reminder) {
    await updateReminder(reminder.id, data);
  } else {
    await createReminder(data);
  }
  await globalMutate(REMINDERS_KEY);
}

export async function toggleReminder(reminder: Reminder, enabled: boolean) {
  await updateReminder(reminder.id, { enabled });
  await globalMutate(REMINDERS_KEY);
}

export async function removeReminder(id: string) {
  await deleteReminder(id);
  await globalMutate(REMINDERS_KEY);
}

/**
 * Best-effort: dispara `Notification` del navegador mientras esta pestaña
 * está abierta, comparando la hora actual contra los recordatorios
 * habilitados cada vez que cambia el minuto. No es un reemplazo de push/OS
 * notifications — si se cierra la pestaña o el navegador, no suena nada.
 * Por eso mobile usa expo-notifications (notificación local del SO) y esto
 * es solo la mejor aproximación posible en web sin Service Worker + Web Push.
 */
export function useReminderNotifications(reminders: Reminder[] | undefined) {
  const [permission, setPermission] = useState<NotificationPermission>(
    typeof Notification !== 'undefined' ? Notification.permission : 'denied',
  );
  // Evita disparar el mismo recordatorio más de una vez dentro del mismo
  // minuto (el interval puede correr varias veces si el tick cae justo en
  // el borde, o si el usuario tiene la pestaña con foco/blur alternando).
  const lastFiredMinuteRef = useRef<string | null>(null);

  async function requestPermission() {
    if (typeof Notification === 'undefined') return;
    const result = await Notification.requestPermission();
    setPermission(result);
  }

  useEffect(() => {
    if (typeof Notification === 'undefined') return;
    if (permission !== 'granted') return;
    if (!reminders || reminders.length === 0) return;

    function checkReminders() {
      const now = new Date();
      const currentKey = `${now.getFullYear()}-${now.getMonth()}-${now.getDate()}-${now.getHours()}-${now.getMinutes()}`;
      if (currentKey === lastFiredMinuteRef.current) return;
      lastFiredMinuteRef.current = currentKey;

      for (const reminder of reminders ?? []) {
        if (!reminder.enabled) continue;
        if (reminder.hour === now.getHours() && reminder.minute === now.getMinutes()) {
          new Notification(`${reminder.icon} ${reminder.message}`);
        }
      }
    }

    checkReminders();
    const interval = setInterval(checkReminders, 30_000);
    return () => clearInterval(interval);
  }, [reminders, permission]);

  return { permission, requestPermission };
}
