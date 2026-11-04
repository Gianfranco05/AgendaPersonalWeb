import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { X } from 'lucide-react';
import { saveBook } from '../../hooks/useLibrary';
import type { Book, BookStatus } from '../../types';

const schema = z.object({
  title: z.string().min(1, 'El título es requerido'),
  author: z.string(),
  status: z.enum(['pendiente', 'leyendo', 'leido']),
  rating: z
    .union([z.number(), z.nan()])
    .optional()
    .refine((v) => v === undefined || Number.isNaN(v) || (v >= 0 && v <= 5), 'El puntaje debe estar entre 0 y 5'),
  pages: z
    .union([z.number(), z.nan()])
    .optional()
    .refine((v) => v === undefined || Number.isNaN(v) || v >= 1, 'Las páginas deben ser 1 o más'),
});

type FormData = z.infer<typeof schema>;

interface Props {
  book: Book | null;
  onClose: () => void;
  onSaved: () => void;
}

const inputCls =
  'w-full rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-2 text-sm focus:border-brand-library focus:outline-none focus:ring-1 focus:ring-brand-library';
const errorCls = 'mt-1 text-xs text-red-500';

const STATUS_LABELS: Record<BookStatus, string> = {
  pendiente: 'Pendiente',
  leyendo: 'Leyendo',
  leido: 'Leído',
};

export default function BookForm({ book, onClose, onSaved }: Props) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { title: '', author: '', status: 'pendiente', rating: undefined, pages: undefined },
  });

  useEffect(() => {
    if (book) {
      reset({
        title: book.title,
        author: book.author ?? '',
        status: book.status,
        rating: book.rating ?? undefined,
        pages: book.pages ?? undefined,
      });
    }
  }, [book, reset]);

  async function onSubmit(data: FormData) {
    const rating = data.rating === undefined || Number.isNaN(data.rating) ? null : data.rating;
    const pages = data.pages === undefined || Number.isNaN(data.pages) ? null : data.pages;
    await saveBook(book, { ...data, author: data.author.trim() || null, rating, pages });
    onSaved();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 px-4 py-8 sm:py-12">
      <div className="w-full max-w-lg rounded-2xl bg-white dark:bg-slate-800 shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-100 dark:border-slate-800 px-6 py-4">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">
            {book ? 'Editar libro' : 'Nuevo libro'}
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
            <input {...register('title')} type="text" className={inputCls} placeholder="Rayuela" />
            {errors.title && <p className={errorCls}>{errors.title.message}</p>}
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">
              Autor (opcional)
            </label>
            <input {...register('author')} type="text" className={inputCls} placeholder="Julio Cortázar" />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="col-span-1">
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Estado</label>
              <select {...register('status')} className={inputCls}>
                {Object.entries(STATUS_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
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
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Páginas</label>
              <input
                {...register('pages', { valueAsNumber: true })}
                type="number"
                min={1}
                className={inputCls}
                placeholder="320"
              />
              {errors.pages && <p className={errorCls}>{errors.pages.message}</p>}
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
              className="rounded-lg bg-brand-library px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90 disabled:opacity-50"
            >
              {isSubmitting ? 'Guardando…' : book ? 'Actualizar' : 'Crear'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
