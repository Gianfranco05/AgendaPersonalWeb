import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { X } from 'lucide-react';
import { saveSubject } from '../../hooks/useStudy';
import type { Subject, SubjectStatus } from '../../types';

const schema = z.object({
  name: z.string().min(1, 'El nombre es requerido'),
  professor: z.string(),
  status: z.enum(['cursando', 'aprobada', 'pendiente']),
});

type FormData = z.infer<typeof schema>;

interface Props {
  subject: Subject | null;
  onClose: () => void;
  onSaved: () => void;
}

const inputCls =
  'w-full rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-2 text-sm focus:border-brand-study focus:outline-none focus:ring-1 focus:ring-brand-study';
const errorCls = 'mt-1 text-xs text-red-500';

const STATUS_LABELS: Record<SubjectStatus, string> = {
  cursando: 'Cursando',
  aprobada: 'Aprobada',
  pendiente: 'Pendiente',
};

export default function SubjectForm({ subject, onClose, onSaved }: Props) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { name: '', professor: '', status: 'cursando' },
  });

  useEffect(() => {
    if (subject) {
      reset({ name: subject.name, professor: subject.professor ?? '', status: subject.status });
    }
  }, [subject, reset]);

  async function onSubmit(data: FormData) {
    await saveSubject(subject, { ...data, professor: data.professor.trim() || null });
    onSaved();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 px-4 py-8 sm:py-12">
      <div className="w-full max-w-lg rounded-2xl bg-white dark:bg-slate-800 shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-100 dark:border-slate-800 px-6 py-4">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">
            {subject ? 'Editar materia' : 'Nueva materia'}
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
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Nombre</label>
            <input {...register('name')} type="text" className={inputCls} placeholder="Álgebra II" />
            {errors.name && <p className={errorCls}>{errors.name.message}</p>}
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">
              Profesor (opcional)
            </label>
            <input {...register('professor')} type="text" className={inputCls} placeholder="Nombre del profesor" />
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
              className="rounded-lg bg-brand-study px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90 disabled:opacity-50"
            >
              {isSubmitting ? 'Guardando…' : subject ? 'Actualizar' : 'Crear'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
