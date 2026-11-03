import { useState } from 'react';
import { BellRing } from 'lucide-react';
import Switch from '../../components/Switch';
import {
  useHabitReminderSettings,
  useHabitReminderToday,
  saveHabitReminderSettings,
  useSyncReminderOffset,
} from '../../hooks/useHabitReminders';
import type { HabitReminderSettings } from '../../types';

const inputCls =
  'rounded-lg border border-gray-200 dark:border-slate-700 bg-transparent px-3 py-1.5 text-sm focus:border-brand-indigo focus:outline-none focus:ring-1 focus:ring-brand-indigo';

export default function HabitReminderSection() {
  const { data: settings, isLoading } = useHabitReminderSettings();
  const { data: today } = useHabitReminderToday();
  const [error, setError] = useState<string | null>(null);
  useSyncReminderOffset(settings);

  async function save(patch: Partial<Omit<HabitReminderSettings, 'has_push_devices'>>) {
    setError(null);
    try {
      await saveHabitReminderSettings(patch);
    } catch {
      setError('No se pudo guardar. Probá de nuevo.');
    }
  }

  let summary: string[] = [];
  if (today?.enabled) {
    summary =
      today.pending_count === 0
        ? ['Ya marcaste todo hoy: no te vamos a avisar.']
        : today.slots
            .filter((slot) => slot.habits.length > 0)
            .map((slot) => `Hoy a las ${slot.time} te avisamos de: ${slot.habits.map((h) => h.title).join(', ')}`);
  }

  return (
    <div className="space-y-4 rounded-xl bg-white dark:bg-slate-800 p-6 shadow-sm">
      <div className="flex items-center gap-2">
        <BellRing size={18} className="text-brand-habits" />
        <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-200">Hábitos sin marcar</h3>
      </div>
      <p className="text-sm text-gray-500 dark:text-slate-400">
        Si a la hora elegida te falta marcar algún hábito, te mandamos un aviso. Si ya marcaste todo, no llega nada.
        Los avisos llegan a la app de Android donde tengas la sesión iniciada.
      </p>

      {isLoading || !settings ? (
        <p className="text-sm text-gray-400 dark:text-slate-500">Cargando…</p>
      ) : (
        <>
          {!settings.has_push_devices && (
            <p className="rounded-lg bg-amber-50 dark:bg-amber-900/20 px-3 py-2 text-sm text-amber-700 dark:text-amber-300">
              Todavía no tenés ningún celular con la sesión iniciada y las notificaciones permitidas. Instalá la
              app de Android, iniciá sesión y aceptá las notificaciones para recibir los avisos.
            </p>
          )}

          <div className="flex items-center justify-between gap-4">
            <span className="text-sm text-gray-700 dark:text-slate-200">Avisarme si me falta marcar un hábito</span>
            <Switch
              checked={settings.enabled}
              label="Avisarme si me falta marcar un hábito"
              onChange={(enabled) => void save({ enabled })}
            />
          </div>

          {settings.enabled && (
            <>
              <div className="flex items-center justify-between gap-4">
                <label htmlFor="habit-reminder-time" className="text-sm text-gray-700 dark:text-slate-200">
                  Hora del aviso
                </label>
                <input
                  id="habit-reminder-time"
                  type="time"
                  value={settings.time}
                  onChange={(e) => {
                    if (e.target.value) void save({ time: e.target.value });
                  }}
                  className={inputCls}
                />
              </div>

              <div className="flex items-center justify-between gap-4">
                <label htmlFor="habit-reminder-cap" className="text-sm text-gray-700 dark:text-slate-200">
                  Máximo de avisos por día
                </label>
                <select
                  id="habit-reminder-cap"
                  value={settings.daily_cap}
                  onChange={(e) => void save({ daily_cap: Number(e.target.value) })}
                  className={inputCls}
                >
                  {[1, 2, 3, 4, 5].map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center justify-between gap-4">
                <span className="text-sm text-gray-700 dark:text-slate-200">Destacar rachas en riesgo</span>
                <Switch
                  checked={settings.streak_alerts}
                  label="Destacar rachas en riesgo"
                  onChange={(streak_alerts) => void save({ streak_alerts })}
                />
              </div>

              {summary.length > 0 && (
                <div className="space-y-1 rounded-lg bg-gray-50 dark:bg-slate-900/40 px-3 py-2 text-sm text-gray-600 dark:text-slate-300">
                  {summary.map((line) => (
                    <p key={line}>{line}</p>
                  ))}
                </div>
              )}
            </>
          )}
          {error && <p className="text-sm text-red-500 dark:text-red-400">{error}</p>}
        </>
      )}
    </div>
  );
}
