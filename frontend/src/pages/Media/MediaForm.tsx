import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { X } from 'lucide-react';
import { saveMediaItem } from '../../hooks/useMedia';
import type { MediaItem, MediaStatus, MediaType } from '../../types';

const schema = z.object({
  title: z.string().min(1, 'El título es requerido'),
  media_type: z.enum(['pelicula', 'serie']),
  status: z.enum(['pendiente', 'viendo', 'visto']),
  rating: z
    .union([z.number(), z.nan()])
    .optional()
    .refine((v) => v === undefined || Number.isNaN(v) || (v >= 0 && v <= 5), 'El puntaje debe estar entre 0 y 5'),
  year: z
    .union([z.number(), z.nan()])
    .optional()
    .refine((v) => v === undefined || Number.isNaN(v) || v >= 1878, 'Año inválido'),
});

type FormData = z.infer<typeof schema>;

interface Props {
  item: MediaItem | null;
  onClose: () => void;
  onSaved: () => void;
}

const inputCls =
  'w-full rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-2 text-sm focus:border-brand-media focus:outline-none focus:ring-1 focus:ring-brand-media';
const errorCls = 'mt-1 text-xs text-red-500';

const TYPE_LABELS: Record<MediaType, string> = { pelicula: 'Película', serie: 'Serie' };
const STATUS_LABELS: Record<MediaStatus, string> = {
  pendiente: 'Pendiente',
  viendo: 'Viendo',
  visto: 'Visto',
};

export default function MediaForm({ item, onClose, onSaved }: Props) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: '',
      media_type: 'pelicula',
      status: 'pendiente',
      rating: undefined,
      year: undefined,
    },
  });

  useEffect(() => {
    if (item) {
      reset({
        title: item.title,
        media_type: item.media_type,
        status: item.status,
        rating: item.rating ?? undefined,
        year: item.year ?? undefined,
      });
    }
  }, [item, reset]);

  async function onSubmit(data: FormData) {
    const rating = data.rating === undefined || Number.isNaN(data.rating) ? null : data.rating;
    const year = data.year === undefined || Number.isNaN(data.year) ? null : data.year;
    await saveMediaItem(item, { ...data, rating, year });
    onSaved();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 px-4 py-8 sm:py-12">
      <div className="w-full max-w-lg rounded-2xl bg-white dark:bg-slate-800 shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-100 dark:border-slate-800 px-6 py-4">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">
            {item ? 'Editar' : 'Nueva película o serie'}
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
            <input {...register('title')} type="text" className={inputCls} placeholder="Interstellar" />
            {errors.title && <p className={errorCls}>{errors.title.message}</p>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Tipo</label>
              <select {...register('media_type')} className={inputCls}>
                {Object.entries(TYPE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
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
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">
                Puntaje (0-5)
              </label>
              <input
                {...register('rating', { valueAsNumber: true })}
                type="number"
                step="0.5"
                min={0}
                max={5}
                className={inputCls}
                placeholder="4.5"
              />
              {errors.rating && <p className={errorCls}>{errors.rating.message}</p>}
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">
                Año (opcional)
              </label>
              <input
                {...register('year', { valueAsNumber: true })}
                type="number"
                className={inputCls}
                placeholder="2014"
              />
              {errors.year && <p className={errorCls}>{errors.year.message}</p>}
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
              className="rounded-lg bg-brand-media px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90 disabled:opacity-50"
            >
              {isSubmitting ? 'Guardando…' : item ? 'Actualizar' : 'Crear'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
