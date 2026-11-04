import { useState } from 'react';
import { Bell, Loader2, Plus, Trash2 } from 'lucide-react';
import { useReminders, useReminderNotifications, toggleReminder, removeReminder } from '../../hooks/useReminders';
import type { Reminder } from '../../types';
import ReminderModal from './ReminderModal';

function pad(value: number): string {
  return String(value).padStart(2, '0');
}

export default function ReminderSection() {
  const { data: reminders, isLoading } = useReminders();
  const { permission, requestPermission } = useReminderNotifications(reminders);
  const [modal, setModal] = useState<{ open: boolean; reminder: Reminder | null }>({
    open: false,
    reminder: null,
  });
  const [busyId, setBusyId] = useState<string | null>(null);
  const [requesting, setRequesting] = useState(false);

  const notificationsSupported = typeof Notification !== 'undefined';

  async function handleToggle(reminder: Reminder, enabled: boolean) {
    setBusyId(reminder.id);
    try {
      await toggleReminder(reminder, enabled);
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(reminder: Reminder) {
    if (!window.confirm(`¿Borrar "${reminder.message}"?`)) return;
    setBusyId(reminder.id);
    try {
      await removeReminder(reminder.id);
    } finally {
      setBusyId(null);
    }
  }

  async function handleRequestPermission() {
    setRequesting(true);
    try {
      await requestPermission();
    } finally {
      setRequesting(false);
    }
  }

  return (
    <div className="space-y-4 rounded-xl bg-white dark:bg-slate-800 p-6 shadow-sm">
      <div className="flex items-center gap-2">
        <Bell size={18} className="text-brand-indigo" />
        <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-200">Recordatorios</h3>
      </div>
      <p className="text-sm text-gray-500 dark:text-slate-400">
        Recordatorios diarios recurrentes: elegís el mensaje, el ícono y la hora.
      </p>

      {isLoading ? (
        <p className="text-sm text-gray-400 dark:text-slate-500">Cargando…</p>
      ) : !reminders || reminders.length === 0 ? (
        <p className="text-sm text-gray-400 dark:text-slate-500">Todavía no tenés recordatorios.</p>
      ) : (
        <div className="space-y-2">
          {reminders.map((r) => (
            <div
              key={r.id}
              className="flex items-center justify-between rounded-lg border border-gray-200 dark:border-slate-700 px-4 py-3"
            >
              <button
                type="button"
                onClick={() => setModal({ open: true, reminder: r })}
                className="flex flex-1 items-center gap-3 text-left"
              >
                <span className="text-xl">{r.icon}</span>
                <div>
                  <p className="text-sm text-gray-700 dark:text-slate-200">{r.message}</p>
                  <p className="text-xs text-gray-500 dark:text-slate-400">
                    {pad(r.hour)}:{pad(r.minute)} · todos los días
                  </p>
                </div>
              </button>
              <div className="flex items-center gap-2">
                <label className="relative inline-flex cursor-pointer items-center">
                  <input
                    type="checkbox"
                    checked={r.enabled}
                    disabled={busyId === r.id}
                    onChange={(e) => handleToggle(r, e.target.checked)}
                    className="peer sr-only"
                  />
                  <div className="h-5 w-9 rounded-full bg-gray-200 dark:bg-slate-600 transition-colors peer-checked:bg-brand-charcoal peer-disabled:opacity-50" />
                  <div className="absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-white transition-transform peer-checked:translate-x-4" />
                </label>
                <button
                  type="button"
                  onClick={() => handleDelete(r)}
                  disabled={busyId === r.id}
                  className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 transition-colors hover:bg-rose-50 hover:text-rose-500 dark:hover:bg-rose-900/20 disabled:opacity-50"
                >
                  {busyId === r.id ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <Trash2 size={16} />
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <button
        type="button"
        onClick={() => setModal({ open: true, reminder: null })}
        className="flex items-center gap-2 rounded-lg border border-gray-200 dark:border-slate-700 px-4 py-2 text-sm text-gray-700 dark:text-slate-200 transition-colors hover:bg-gray-50 dark:hover:bg-slate-700/50"
      >
        <Plus size={16} />
        Agregar recordatorio
      </button>

      <div className="border-t border-gray-100 dark:border-slate-700 pt-4">
        {!notificationsSupported ? (
          <p className="text-sm text-gray-500 dark:text-slate-400">
            Este navegador no soporta notificaciones.
          </p>
        ) : permission === 'granted' ? (
          <p className="text-sm text-emerald-600 dark:text-emerald-400">Avisos activados en este navegador</p>
        ) : permission === 'denied' ? (
          <p className="text-sm text-rose-500">
            Bloqueaste las notificaciones para este sitio. Habilitalas desde la configuración del
            navegador para volver a activarlas.
          </p>
        ) : (
          <button
            type="button"
            onClick={handleRequestPermission}
            disabled={requesting}
            className="flex items-center gap-2 rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-charcoal-hover disabled:opacity-50"
          >
            {requesting ? <Loader2 size={16} className="animate-spin" /> : <Bell size={16} />}
            Activar avisos en este navegador
          </button>
        )}
        <p className="mt-2 text-xs text-gray-400 dark:text-slate-500">
          Los avisos solo suenan mientras esta pestaña esté abierta en el navegador. Para
          recordatorios confiables en cualquier momento, usá la app del celular.
        </p>
      </div>

      {modal.open && (
        <ReminderModal
          reminder={modal.reminder}
          onClose={() => setModal({ open: false, reminder: null })}
          onSaved={() => setModal({ open: false, reminder: null })}
        />
      )}
    </div>
  );
}
