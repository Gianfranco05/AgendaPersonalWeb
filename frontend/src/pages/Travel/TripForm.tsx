import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { X } from 'lucide-react';
import { addTrip, editTrip } from '../../hooks/useTravel';
import type { Trip } from '../../types';

const schema = z.object({
  destination: z.string().min(1, 'El destino es requerido').max(160),
  status: z.enum(['planeado', 'en_curso', 'completado']),
  start_date: z.string().optional(),
  end_date: z.string().optional(),
  budget: z.string().optional(),
  notes: z.string().optional(),
});

type FormData = z.infer<typeof schema>;

interface Props {
  trip: Trip | null;
  onClose: () => void;
}

const inputCls =
  'w-full rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-2 text-sm focus:border-brand-travel focus:outline-none focus:ring-1 focus:ring-brand-travel';
const errorCls = 'mt-1 text-xs text-red-500';

const STATUS_LABELS: Record<FormData['status'], string> = {
  planeado: 'Planeado',
  en_curso: 'En curso',
  completado: 'Completado',
};

export default function TripForm({ trip, onClose }: Props) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      destination: '',
      status: 'planeado',
      start_date: '',
      end_date: '',
      budget: '',
      notes: '',
    },
  });

  useEffect(() => {
    if (trip) {
      reset({
        destination: trip.destination,
        status: trip.status,
        start_date: trip.start_date ?? '',
        end_date: trip.end_date ?? '',
        budget: trip.budget != null ? String(trip.budget) : '',
        notes: trip.notes ?? '',
      });
    }
  }, [trip, reset]);

  async function onSubmit(data: FormData) {
    const payload: Partial<Trip> = {
      destination: data.destination.trim(),
      status: data.status,
      start_date: data.start_date?.trim() || null,
      end_date: data.end_date?.trim() || null,
      budget: data.budget?.trim() ? Number(data.budget) : null,
      notes: data.notes?.trim() || null,
    };
    if (trip) {
      await editTrip(trip.id, payload);
    } else {
      await addTrip(payload);
    }
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 px-4 py-8 sm:py-12">
      <div className="w-full max-w-lg rounded-2xl bg-white dark:bg-slate-800 shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-100 dark:border-slate-800 px-6 py-4">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">
            {trip ? 'Editar viaje' : 'Nuevo viaje'}
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
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Destino</label>
            <input {...register('destination')} type="text" className={inputCls} placeholder="Bariloche" />
            {errors.destination && <p className={errorCls}>{errors.destination.message}</p>}
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Estado</label>
            <select {...register('status')} className={inputCls}>
              {Object.entries(STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">
                Fecha de inicio
              </label>
              <input {...register('start_date')} type="date" className={inputCls} />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">
                Fecha de fin
              </label>
              <input {...register('end_date')} type="date" className={inputCls} />
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">
              Presupuesto (opcional)
            </label>
            <input {...register('budget')} type="number" min="0" step="0.01" className={inputCls} placeholder="0" />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">
              Notas (opcional)
            </label>
            <textarea {...register('notes')} rows={2} className={inputCls} placeholder="Detalles del viaje" />
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
              className="rounded-lg bg-brand-travel px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90 disabled:opacity-50"
            >
              {isSubmitting ? 'Guardando…' : trip ? 'Actualizar' : 'Crear'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
