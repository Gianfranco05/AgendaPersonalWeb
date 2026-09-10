import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { X } from 'lucide-react';
import { addProject, editProject } from '../../hooks/useProjects';
import type { Project } from '../../types';

const schema = z.object({
  name: z.string().min(1, 'El nombre es requerido').max(160),
  description: z.string().max(1000).optional(),
  status: z.enum(['activo', 'pausado', 'completado']),
});

type FormData = z.infer<typeof schema>;

interface Props {
  project: Project | null;
  onClose: () => void;
}

const inputCls =
  'w-full rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-2 text-sm focus:border-brand-projects focus:outline-none focus:ring-1 focus:ring-brand-projects';
const errorCls = 'mt-1 text-xs text-red-500';

const STATUS_LABELS: Record<FormData['status'], string> = {
  activo: 'Activo',
  pausado: 'Pausado',
  completado: 'Completado',
};

export default function ProjectForm({ project, onClose }: Props) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { name: '', description: '', status: 'activo' },
  });

  useEffect(() => {
    if (project) {
      reset({
        name: project.name,
        description: project.description ?? '',
        status: project.status,
      });
    }
  }, [project, reset]);

  async function onSubmit(data: FormData) {
    const payload: Partial<Project> = {
      name: data.name.trim(),
      description: data.description?.trim() || null,
      status: data.status,
    };
    if (project) {
      await editProject(project.id, payload);
    } else {
      await addProject(payload);
    }
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 px-4 py-8 sm:py-12">
      <div className="w-full max-w-lg rounded-2xl bg-white dark:bg-slate-800 shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-100 dark:border-slate-800 px-6 py-4">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">
            {project ? 'Editar proyecto' : 'Nuevo proyecto'}
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
            <input {...register('name')} type="text" className={inputCls} placeholder="Rediseño web" />
            {errors.name && <p className={errorCls}>{errors.name.message}</p>}
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">
              Descripción (opcional)
            </label>
            <textarea
              {...register('description')}
              rows={2}
              className={inputCls}
              placeholder="De qué se trata"
            />
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
              className="rounded-lg bg-brand-projects px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90 disabled:opacity-50"
            >
              {isSubmitting ? 'Guardando…' : project ? 'Actualizar' : 'Crear'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
