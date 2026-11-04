import { useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { X } from 'lucide-react';
import type { Goal } from '../../types';

const schema = z
  .object({
    title: z.string().min(1, 'El título es requerido'),
    description: z.string().optional(),
    goal_type: z.enum(['progress', 'binary', 'metric', 'savings']),
    target: z.number(),
    unit: z.string().optional(),
    // Opcional: un hábito diario no tiene fecha de cierre y la API acepta end_date nulo.
    deadline: z.string(),
    color: z.string().min(1, 'El color es requerido'),
    // Aviso "no marcaste este hábito hoy" (solo binary/metric). Vacío = hora general.
    reminder_enabled: z.boolean(),
    reminder_time: z
      .string()
      .refine((v) => v === '' || /^([01]\d|2[0-3]):[0-5]\d$/.test(v), 'Ingresá una hora válida'),
  })
  .superRefine((data, ctx) => {
    if ((data.goal_type === 'progress' || data.goal_type === 'savings') && !(data.target > 0)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'El objetivo debe ser positivo',
        path: ['target'],
      });
    }
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
  initialType?: 'progress' | 'binary' | 'metric' | 'savings';
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
      reminder_enabled: true,
      reminder_time: '',
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
        reminder_enabled: goal.reminder_enabled ?? true,
        reminder_time: goal.reminder_time ?? '',
      });
    }
  }, [goal, reset]);

  const isHabit = goalType === 'binary' || goalType === 'metric';
  const reminderEnabled = watch('reminder_enabled');

  async function onSubmit(data: FormData) {
    const payload: Omit<Goal, 'id'> = {
      title: data.title,
      description: data.description || null,
      goal_type: data.goal_type,
      target_value: data.goal_type === 'binary' ? 1 : data.goal_type === 'metric' ? 0 : data.target,
      current_value: goal?.current_value ?? 0,
      unit:
        data.goal_type === 'progress' || data.goal_type === 'metric'
          ? data.unit || 'unidades'
          : data.goal_type === 'savings'
            ? data.unit || 'ARS'
            : null,
      end_date: data.deadline || null,
      color: data.color,
      icon: goal?.icon ?? 'fa-bullseye',
      is_completed: goal?.is_completed ?? false,
      // Solo los hábitos tienen aviso: una meta numérica o de ahorro no lo manda.
      ...(isHabit && {
        reminder_enabled: data.reminder_enabled,
        reminder_time: data.reminder_enabled && data.reminder_time ? data.reminder_time : null,
      }),
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
                  <button
                    type="button"
                    onClick={() => { field.onChange('metric'); setValue('target', 0); }}
                    className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                      goalType === 'metric'
                        ? 'bg-brand-charcoal text-white'
                        : 'text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-100'
                    }`}
                  >
                    Métrica diaria
                  </button>
                  <button
                    type="button"
                    onClick={() => { field.onChange('savings'); setValue('unit', 'ARS'); }}
                    className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                      goalType === 'savings'
                        ? 'bg-brand-charcoal text-white'
                        : 'text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-100'
                    }`}
                  >
                    Ahorro
                  </button>
                </div>
              )}
            />
            {goalType === 'metric' && (
              <p className="mt-1 text-xs text-gray-400 dark:text-slate-500">
                Se carga un valor distinto cada día (minutos, páginas, etc.) desde la pestaña "Registro mensual".
              </p>
            )}
            {goalType === 'savings' && (
              <p className="mt-1 text-xs text-gray-400 dark:text-slate-500">
                Se gestiona desde Finanzas → Ahorro, donde vas a poder registrar depósitos.
              </p>
            )}
          </div>

          {(goalType === 'progress' || goalType === 'metric' || goalType === 'savings') && (
            <div className="grid grid-cols-2 gap-4">
              {(goalType === 'progress' || goalType === 'savings') && (
                <div>
                  <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">
                    {goalType === 'savings' ? 'Monto objetivo' : 'Objetivo'}
                  </label>
                  <input
                    {...register('target', { valueAsNumber: true })}
                    type="number"
                    className={inputCls}
                    placeholder="100"
                  />
                  {errors.target && <p className={errorCls}>{errors.target.message}</p>}
                </div>
              )}
              <div className={goalType === 'metric' ? 'col-span-2' : ''}>
                <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">
                  {goalType === 'savings' ? 'Moneda' : 'Unidad'}
                </label>
                <input
                  {...register('unit')}
                  type="text"
                  className={inputCls}
                  placeholder={goalType === 'savings' ? 'ARS, USD, etc' : 'minutos, páginas, km, etc'}
                />
              </div>
            </div>
          )}

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Fecha límite (opcional)</label>
            <input {...register('deadline')} type="date" className={inputCls} />
            {errors.deadline && <p className={errorCls}>{errors.deadline.message}</p>}
          </div>

          {isHabit && (
            <div className="space-y-2 rounded-lg border border-gray-200 dark:border-slate-700 p-3">
              <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-slate-200">
                <input {...register('reminder_enabled')} type="checkbox" className="h-4 w-4 rounded" />
                Recordarme si no lo marqué
              </label>
              <div>
                <label
                  htmlFor="goal-reminder-time"
                  className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400"
                >
                  Hora propia (opcional)
                </label>
                <input
                  id="goal-reminder-time"
                  {...register('reminder_time')}
                  type="time"
                  disabled={!reminderEnabled}
                  className={`${inputCls} disabled:opacity-50`}
                />
                <p className="mt-1 text-xs text-gray-400 dark:text-slate-500">
                  Vacío = usa la hora general de los avisos (Configuración).
                </p>
                {errors.reminder_time && <p className={errorCls}>{errors.reminder_time.message}</p>}
              </div>
            </div>
          )}

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
