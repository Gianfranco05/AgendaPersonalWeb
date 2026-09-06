import { useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { X } from 'lucide-react';
import { saveReminder } from '../../hooks/useReminders';
import type { Reminder } from '../../types';

const EMOJIS = ['🔔', '⏰', '💊', '🏋️', '📚', '💧', '🧘', '🍎', '💰', '📝'];
const HOURS = Array.from({ length: 24 }, (_, i) => i);
const MINUTES = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55];

function pad(value: number): string {
  return String(value).padStart(2, '0');
}

const schema = z.object({
  message: z.string().min(1, 'El mensaje es requerido').max(200),
  icon: z.string().min(1).max(8),
  hour: z.number().min(0).max(23),
  minute: z.number().min(0).max(59),
  enabled: z.boolean(),
});

type FormData = z.infer<typeof schema>;

interface Props {
  reminder: Reminder | null;
  onClose: () => void;
  onSaved: () => void;
}

const inputCls =
  'w-full rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-2 text-sm focus:border-brand-indigo focus:outline-none focus:ring-1 focus:ring-brand-indigo';
const errorCls = 'mt-1 text-xs text-red-500';

export default function ReminderModal({ reminder, onClose, onSaved }: Props) {
  const {
    register,
    handleSubmit,
    control,
    reset,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormData, unknown, FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      message: '',
      icon: '🔔',
      hour: 9,
      minute: 0,
      enabled: true,
    },
  });

  const icon = watch('icon');
  const hour = watch('hour');
  const minute = watch('minute');

  useEffect(() => {
    if (reminder) {
      reset({
        message: reminder.message,
        icon: reminder.icon,
        hour: reminder.hour,
        minute: reminder.minute,
        enabled: reminder.enabled,
      });
    }
  }, [reminder, reset]);

  async function onSubmit(data: FormData) {
    await saveReminder(reminder, data);
    onSaved();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 px-4 py-8 sm:py-12">
      <div className="w-full max-w-lg rounded-xl bg-white dark:bg-slate-800 shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-100 dark:border-slate-800 px-6 py-4">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">
            {reminder ? 'Editar recordatorio' : 'Nuevo recordatorio'}
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-gray-400 dark:text-slate-500 hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-gray-600 dark:hover:text-slate-200"
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 px-6 py-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Mensaje</label>
            <input
              {...register('message')}
              type="text"
              maxLength={200}
              className={inputCls}
              placeholder="¿Cargaste tus hábitos de hoy?"
            />
            {errors.message && <p className={errorCls}>{errors.message.message}</p>}
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Ícono</label>
            <Controller
              name="icon"
              control={control}
              render={({ field }) => (
                <div className="flex flex-wrap gap-2">
                  {EMOJIS.map((e) => (
                    <button
                      key={e}
                      type="button"
                      onClick={() => field.onChange(e)}
                      className={`flex h-9 w-9 items-center justify-center rounded-lg text-lg transition-colors ${
                        icon === e
                          ? 'bg-brand-charcoal'
                          : 'bg-gray-50 dark:bg-slate-700/50 hover:bg-gray-100 dark:hover:bg-slate-700'
                      }`}
                    >
                      {e}
                    </button>
                  ))}
                </div>
              )}
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Hora</label>
            <Controller
              name="hour"
              control={control}
              render={({ field }) => (
                <div className="flex max-h-32 flex-wrap gap-2 overflow-y-auto">
                  {HOURS.map((h) => (
                    <button
                      key={h}
                      type="button"
                      onClick={() => field.onChange(h)}
                      className={`flex h-8 w-9 items-center justify-center rounded-lg text-xs font-medium transition-colors ${
                        hour === h
                          ? 'bg-brand-charcoal text-white'
                          : 'bg-gray-50 dark:bg-slate-700/50 text-gray-600 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-700'
                      }`}
                    >
                      {pad(h)}
                    </button>
                  ))}
                </div>
              )}
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Minuto</label>
            <Controller
              name="minute"
              control={control}
              render={({ field }) => (
                <div className="flex flex-wrap gap-2">
                  {MINUTES.map((m) => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => field.onChange(m)}
                      className={`flex h-8 w-10 items-center justify-center rounded-lg text-xs font-medium transition-colors ${
                        minute === m
                          ? 'bg-brand-charcoal text-white'
                          : 'bg-gray-50 dark:bg-slate-700/50 text-gray-600 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-700'
                      }`}
                    >
                      {pad(m)}
                    </button>
                  ))}
                </div>
              )}
            />
          </div>

          <p className="text-center text-sm text-gray-500 dark:text-slate-400">
            Suena todos los días a las {pad(hour)}:{pad(minute)}
          </p>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-gray-200 dark:border-slate-700 px-4 py-2 text-sm font-medium text-gray-600 dark:text-slate-300 transition-colors hover:bg-gray-50 dark:hover:bg-slate-700/50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-charcoal-hover disabled:opacity-50"
            >
              {isSubmitting ? 'Guardando…' : reminder ? 'Actualizar' : 'Crear'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
