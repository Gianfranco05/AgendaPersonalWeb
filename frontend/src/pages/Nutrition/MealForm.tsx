import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { X } from 'lucide-react';
import { saveMeal } from '../../hooks/useNutrition';
import type { Meal } from '../../types';
import { toLocalDateString } from '../../utils/date';

const schema = z.object({
  date: z.string().min(1, 'La fecha es requerida'),
  meal_type: z.enum(['breakfast', 'lunch', 'dinner', 'snack']),
  name: z.string().min(1, 'El nombre es requerido'),
  calories: z.number().nonnegative('Debe ser 0 o mayor'),
  protein_g: z.number().nonnegative('Debe ser 0 o mayor'),
  carbs_g: z.number().nonnegative('Debe ser 0 o mayor'),
  fat_g: z.number().nonnegative('Debe ser 0 o mayor'),
});

type FormData = z.infer<typeof schema>;

interface Props {
  meal: Meal | null;
  params?: { date_from?: string; date_to?: string };
  onClose: () => void;
  onSaved: () => void;
}

const inputCls =
  'w-full rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-2 text-sm focus:border-brand-nutrition focus:outline-none focus:ring-1 focus:ring-brand-nutrition';
const errorCls = 'mt-1 text-xs text-red-500';

const MEAL_TYPE_LABELS: Record<FormData['meal_type'], string> = {
  breakfast: 'Desayuno',
  lunch: 'Almuerzo',
  dinner: 'Cena',
  snack: 'Snack',
};

export default function MealForm({ meal, params, onClose, onSaved }: Props) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      date: toLocalDateString(),
      meal_type: 'breakfast',
      name: '',
      calories: 0,
      protein_g: 0,
      carbs_g: 0,
      fat_g: 0,
    },
  });

  useEffect(() => {
    if (meal) {
      reset({
        date: meal.date,
        meal_type: meal.meal_type,
        name: meal.name,
        calories: meal.calories,
        protein_g: meal.protein_g,
        carbs_g: meal.carbs_g,
        fat_g: meal.fat_g,
      });
    }
  }, [meal, reset]);

  async function onSubmit(data: FormData) {
    await saveMeal(meal, data, params);
    onSaved();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 px-4 py-8 sm:py-12">
      <div className="w-full max-w-lg rounded-2xl bg-white dark:bg-slate-800 shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-100 dark:border-slate-800 px-6 py-4">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">
            {meal ? 'Editar comida' : 'Nueva comida'}
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
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Tipo</label>
              <select {...register('meal_type')} className={inputCls}>
                {Object.entries(MEAL_TYPE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Nombre</label>
            <input {...register('name')} type="text" className={inputCls} placeholder="Ej: Pollo con arroz" />
            {errors.name && <p className={errorCls}>{errors.name.message}</p>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Calorías</label>
              <input
                {...register('calories', { valueAsNumber: true })}
                type="number"
                className={inputCls}
              />
              {errors.calories && <p className={errorCls}>{errors.calories.message}</p>}
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Proteína (g)</label>
              <input
                {...register('protein_g', { valueAsNumber: true })}
                type="number"
                className={inputCls}
              />
              {errors.protein_g && <p className={errorCls}>{errors.protein_g.message}</p>}
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Carbohidratos (g)</label>
              <input
                {...register('carbs_g', { valueAsNumber: true })}
                type="number"
                className={inputCls}
              />
              {errors.carbs_g && <p className={errorCls}>{errors.carbs_g.message}</p>}
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Grasas (g)</label>
              <input
                {...register('fat_g', { valueAsNumber: true })}
                type="number"
                className={inputCls}
              />
              {errors.fat_g && <p className={errorCls}>{errors.fat_g.message}</p>}
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
              className="rounded-lg bg-brand-nutrition px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90 disabled:opacity-50"
            >
              {isSubmitting ? 'Guardando…' : meal ? 'Actualizar' : 'Crear'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
