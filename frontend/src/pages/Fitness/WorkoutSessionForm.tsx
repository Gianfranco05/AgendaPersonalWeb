import { useEffect } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { X, Plus, Trash2 } from 'lucide-react';
import { saveWorkoutSession } from '../../hooks/useFitness';
import type { WorkoutSession } from '../../types';

const exerciseSchema = z.object({
  name: z.string().min(1, 'Requerido'),
  sets: z.number().int().positive('Debe ser positivo'),
  reps: z.number().int().positive('Debe ser positivo'),
  weight_kg: z.number().nullable(),
});

const schema = z.object({
  date: z.string().min(1, 'La fecha es requerida'),
  name: z.string().min(1, 'El nombre es requerido'),
  duration_minutes: z.number().nullable(),
  notes: z.string().nullable(),
  exercises: z.array(exerciseSchema),
});

type FormData = z.infer<typeof schema>;

interface Props {
  session: WorkoutSession | null;
  onClose: () => void;
  onSaved: () => void;
}

const inputCls =
  'w-full rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-2 text-sm focus:border-brand-fitness focus:outline-none focus:ring-1 focus:ring-brand-fitness';
const errorCls = 'mt-1 text-xs text-red-500';

export default function WorkoutSessionForm({ session, onClose, onSaved }: Props) {
  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      date: new Date().toISOString().split('T')[0],
      name: '',
      duration_minutes: null,
      notes: null,
      exercises: [{ name: '', sets: 3, reps: 10, weight_kg: null }],
    },
  });

  const { fields, append, remove } = useFieldArray({ control, name: 'exercises' });

  useEffect(() => {
    if (session) {
      reset({
        date: session.date,
        name: session.name,
        duration_minutes: session.duration_minutes,
        notes: session.notes,
        exercises: session.exercises.length
          ? session.exercises
              .slice()
              .sort((a, b) => a.order - b.order)
              .map((ex) => ({ name: ex.name, sets: ex.sets, reps: ex.reps, weight_kg: ex.weight_kg }))
          : [{ name: '', sets: 3, reps: 10, weight_kg: null }],
      });
    }
  }, [session, reset]);

  async function onSubmit(data: FormData) {
    const payload: Omit<WorkoutSession, 'id'> = {
      date: data.date,
      name: data.name,
      duration_minutes: data.duration_minutes,
      notes: data.notes,
      exercises: data.exercises.map((ex, i) => ({ ...ex, order: i })),
    };
    await saveWorkoutSession(session, payload);
    onSaved();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 px-4 py-8 sm:py-12">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white dark:bg-slate-800 shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-100 dark:border-slate-800 px-6 py-4">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">
            {session ? 'Editar sesión' : 'Nueva sesión'}
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
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Fecha</label>
              <input {...register('date')} type="date" className={inputCls} />
              {errors.date && <p className={errorCls}>{errors.date.message}</p>}
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Duración (min)</label>
              <input
                {...register('duration_minutes', { setValueAs: (v) => (v === '' ? null : Number(v)) })}
                type="number"
                className={inputCls}
                placeholder="60"
              />
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Nombre</label>
            <input {...register('name')} type="text" className={inputCls} placeholder="Ej: Tren superior" />
            {errors.name && <p className={errorCls}>{errors.name.message}</p>}
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Notas</label>
            <textarea
              {...register('notes', { setValueAs: (v) => (v === '' ? null : v) })}
              className={inputCls}
              rows={2}
              placeholder="Opcional"
            />
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between">
              <label className="text-xs font-medium text-gray-500 dark:text-slate-400">Ejercicios</label>
              <button
                type="button"
                onClick={() => append({ name: '', sets: 3, reps: 10, weight_kg: null })}
                className="flex items-center gap-1 rounded-lg bg-brand-fitness/10 px-2 py-1 text-xs font-medium text-brand-fitness hover:bg-brand-fitness/20"
              >
                <Plus size={12} />
                Agregar
              </button>
            </div>

            <div className="space-y-2">
              {fields.map((field, i) => (
                <div key={field.id} className="flex items-end gap-2 rounded-lg border border-gray-100 dark:border-slate-800 p-2">
                  <div className="flex-1">
                    <label className="mb-1 block text-[10px] text-gray-400 dark:text-slate-500">Ejercicio</label>
                    <input {...register(`exercises.${i}.name`)} type="text" className={inputCls} placeholder="Ej: Press banca" />
                  </div>
                  <div className="w-16">
                    <label className="mb-1 block text-[10px] text-gray-400 dark:text-slate-500">Sets</label>
                    <input
                      {...register(`exercises.${i}.sets`, { valueAsNumber: true })}
                      type="number"
                      className={inputCls}
                    />
                  </div>
                  <div className="w-16">
                    <label className="mb-1 block text-[10px] text-gray-400 dark:text-slate-500">Reps</label>
                    <input
                      {...register(`exercises.${i}.reps`, { valueAsNumber: true })}
                      type="number"
                      className={inputCls}
                    />
                  </div>
                  <div className="w-20">
                    <label className="mb-1 block text-[10px] text-gray-400 dark:text-slate-500">Peso (kg)</label>
                    <input
                      {...register(`exercises.${i}.weight_kg`, {
                        setValueAs: (v) => (v === '' ? null : Number(v)),
                      })}
                      type="number"
                      className={inputCls}
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => remove(i)}
                    disabled={fields.length <= 1}
                    className="rounded-lg p-2 text-gray-400 dark:text-slate-500 hover:bg-rose-50 hover:text-rose-500 disabled:opacity-30"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
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
              className="rounded-lg bg-brand-fitness px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90 disabled:opacity-50"
            >
              {isSubmitting ? 'Guardando…' : session ? 'Actualizar' : 'Crear'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
