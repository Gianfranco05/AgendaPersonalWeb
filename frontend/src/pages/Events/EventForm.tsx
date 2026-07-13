import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { X } from 'lucide-react';
import type { CalendarEvent } from '../../types';

const schema = z.object({
  title: z.string().min(1, 'El título es requerido'),
  description: z.string().optional(),
  date: z.string().min(1, 'La fecha es requerida'),
  time: z.string().optional(),
  all_day: z.boolean(),
  location: z.string().optional(),
  color: z.string().min(1, 'El color es requerido'),
});

type FormData = z.infer<typeof schema>;

const COLORS = ['#7C3AED', '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#EC4899', '#6366F1'];

const inputCls =
  'w-full rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-2 text-sm focus:border-brand-indigo focus:outline-none focus:ring-1 focus:ring-brand-indigo';
const errorCls = 'mt-1 text-xs text-red-500';

interface Props {
  event: CalendarEvent | null;
  onClose: () => void;
  onSave: (data: Omit<CalendarEvent, 'id'>, id?: string) => Promise<void>;
}

export default function EventForm({ event, onClose, onSave }: Props) {
  const {
    register,
    handleSubmit,
    watch,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: '',
      description: '',
      date: new Date().toISOString().split('T')[0],
      time: '',
      all_day: false,
      location: '',
      color: '#7C3AED',
    },
  });

  const allDay = watch('all_day');

  useEffect(() => {
    if (event) {
      const d = new Date(event.start_datetime);
      reset({
        title: event.title,
        description: event.description ?? '',
        date: d.toISOString().split('T')[0],
        time: event.is_all_day ? '' : `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`,
        all_day: event.is_all_day,
        location: event.location ?? '',
        color: event.color,
      });
    }
  }, [event, reset]);

  async function onSubmit(data: FormData) {
    const start_datetime = data.all_day
      ? `${data.date}T00:00:00`
      : `${data.date}T${data.time || '00:00'}:00`;
    const payload: Omit<CalendarEvent, 'id'> = {
      title: data.title,
      description: data.description || undefined,
      start_datetime,
      is_all_day: data.all_day,
      color: data.color,
      location: data.location || undefined,
    };
    await onSave(payload, event?.id);
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 px-4 py-8 sm:py-12">
      <div className="w-full max-w-lg rounded-xl bg-white dark:bg-slate-800 shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-100 dark:border-slate-800 px-6 py-4">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">
            {event ? 'Editar evento' : 'Nuevo evento'}
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
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Título</label>
            <input {...register('title')} type="text" className={inputCls} placeholder="Ej: Reunión de equipo" />
            {errors.title && <p className={errorCls}>{errors.title.message}</p>}
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Descripción</label>
            <textarea {...register('description')} className={inputCls} rows={3} placeholder="Opcional" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Fecha</label>
              <input {...register('date')} type="date" className={inputCls} />
              {errors.date && <p className={errorCls}>{errors.date.message}</p>}
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Hora</label>
              <input {...register('time')} type="time" className={inputCls} disabled={allDay} />
            </div>
          </div>

          <label className="flex items-center gap-2">
            <input {...register('all_day')} type="checkbox" className="rounded border-gray-300 dark:border-slate-600 text-brand-indigo focus:ring-brand-indigo" />
            <span className="text-sm text-gray-600 dark:text-slate-300">Todo el día</span>
          </label>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Ubicación</label>
            <input {...register('location')} type="text" className={inputCls} placeholder="Opcional" />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Color</label>
            <div className="flex gap-2">
              {COLORS.map((c) => (
                <label key={c} className="flex cursor-pointer items-center">
                  <input
                    {...register('color')}
                    type="radio"
                    value={c}
                    className="sr-only"
                  />
                  <span
                    className={`inline-block h-7 w-7 rounded-full border-2 transition-colors ${
                      watch('color') === c ? 'border-gray-800' : 'border-transparent'
                    }`}
                    style={{ backgroundColor: c }}
                  />
                </label>
              ))}
            </div>
          </div>

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
              {isSubmitting ? 'Guardando…' : event ? 'Actualizar' : 'Crear'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
