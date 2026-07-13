import { useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { X } from 'lucide-react';
import type { Goal } from '../../types';

const schema = z.object({
  title: z.string().min(1, 'El título es requerido'),
  description: z.string().optional(),
  goal_type: z.enum(['progress', 'binary']),
  target: z.number().positive('El objetivo debe ser positivo'),
  unit: z.string().optional(),
  deadline: z.string().min(1, 'La fecha límite es requerida'),
  color: z.string().min(1, 'El color es requerido'),
});

type FormData = z.infer<typeof schema>;

const COLORS = ['#7C3AED', '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#EC4899', '#6366F1'];

const inputCls =
  'w-full rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-2 text-sm focus:border-brand-indigo focus:outline-none focus:ring-1 focus:ring-brand-indigo';
const errorCls = 'mt-1 text-xs text-red-500';

interface Props {
  goal: Goal | null;
  onClose: () => void;
  onSave: (data: Omit<Goal, 'id'>, id?: string) => Promise<void>;
  /** Tipo inicial para una entrada nueva (por defecto 'progress'). */
  initialType?: 'progress' | 'binary';
  /** Oculta el selector de tipo (útil para hábitos, siempre binarios). */
  lockType?: boolean;
  titleNew?: string;
  titleEdit?: string;
}

export default function GoalForm({
  goal,
  onClose,
  onSave,
  initialType = 'progress',
  lockType = false,
  titleNew = 'Nueva meta',
  titleEdit = 'Editar meta',
}: Props) {
  const {
    register,
    handleSubmit,
    control,
    watch,
    reset,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: '',
      description: '',
      goal_type: initialType,
      target: initialType === 'binary' ? 1 : 0,
      unit: '',
      deadline: '',
      color: '#7C3AED',
    },
  });

  const goalType = watch('goal_type');

  useEffect(() => {
    if (goal) {
      reset({
        title: goal.title,
        description: goal.description ?? '',
        goal_type: goal.goal_type,
        target: goal.target_value,
        unit: goal.unit ?? '',
        deadline: goal.end_date ?? '',
        color: goal.color,
      });
    }
  }, [goal, reset]);

  async function onSubmit(data: FormData) {
    const payload: Omit<Goal, 'id'> = {
      title: data.title,
      description: data.description || null,
      goal_type: data.goal_type,
      target_value: data.goal_type === 'binary' ? 1 : data.target,
      current_value: goal?.current_value ?? 0,
      unit: data.goal_type === 'progress' ? data.unit || 'unidades' : null,
      end_date: data.deadline,
      color: data.color,
      icon: goal?.icon ?? 'fa-bullseye',
      is_completed: goal?.is_completed ?? false,
    };
    await onSave(payload, goal?.id);
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 px-4 py-8 sm:py-12">
      <div className="w-full max-w-lg rounded-xl bg-white dark:bg-slate-800 shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-100 dark:border-slate-800 px-6 py-4">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">
            {goal ? titleEdit : titleNew}
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
            <input {...register('title')} type="text" className={inputCls} placeholder="Ej: Leer 12 libros" />
            {errors.title && <p className={errorCls}>{errors.title.message}</p>}
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Descripción</label>
            <textarea {...register('description')} className={inputCls} rows={2} placeholder="Opcional" />
          </div>

          <div className={lockType ? 'hidden' : ''}>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Tipo de meta</label>
            <Controller
              name="goal_type"
              control={control}
              render={({ field }) => (
                <div className="flex rounded-lg border border-gray-200 dark:border-slate-700 p-0.5">
                  <button
                    type="button"
                    onClick={() => field.onChange('progress')}
                    className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                      goalType === 'progress'
                        ? 'bg-brand-charcoal text-white'
                        : 'text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-100'
                    }`}
                  >
                    Numérica
                  </button>
                  <button
                    type="button"
                    onClick={() => { field.onChange('binary'); setValue('target', 1); }}
                    className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                      goalType === 'binary'
                        ? 'bg-brand-charcoal text-white'
                        : 'text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-100'
                    }`}
                  >
                    Binaria
                  </button>
                </div>
              )}
            />
          </div>

          {goalType === 'progress' && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Objetivo</label>
                <input
                  {...register('target', { valueAsNumber: true })}
                  type="number"
                  className={inputCls}
                  placeholder="100"
                />
                {errors.target && <p className={errorCls}>{errors.target.message}</p>}
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Unidad</label>
                <input
                  {...register('unit')}
                  type="text"
                  className={inputCls}
                  placeholder="km, libros, etc"
                />
              </div>
            </div>
          )}

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Fecha límite</label>
            <input {...register('deadline')} type="date" className={inputCls} />
            {errors.deadline && <p className={errorCls}>{errors.deadline.message}</p>}
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
              {isSubmitting ? 'Guardando…' : goal ? 'Actualizar' : 'Crear'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
