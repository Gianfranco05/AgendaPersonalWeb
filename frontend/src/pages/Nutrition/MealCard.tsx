import { Pencil, Trash2 } from 'lucide-react';
import type { Meal } from '../../types';

interface Props {
  meal: Meal;
  onEdit: (meal: Meal) => void;
  onDelete: (id: string) => void;
}

export default function MealCard({ meal, onEdit, onDelete }: Props) {
  return (
    <div className="rounded-xl bg-white dark:bg-slate-800 p-4 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex items-start justify-between">
        <h4 className="font-medium text-gray-800 dark:text-slate-100">{meal.name}</h4>
        <div className="flex gap-1">
          <button
            onClick={() => onEdit(meal)}
            className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 transition-colors hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-brand-nutrition"
            title="Editar"
          >
            <Pencil size={13} />
          </button>
          <button
            onClick={() => onDelete(meal.id)}
            className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 transition-colors hover:bg-rose-50 hover:text-rose-500"
            title="Eliminar"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>
      <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-500 dark:text-slate-400">
        <span className="font-semibold text-brand-nutrition">{meal.calories} kcal</span>
        <span>P: {meal.protein_g}g</span>
        <span>C: {meal.carbs_g}g</span>
        <span>G: {meal.fat_g}g</span>
      </div>
    </div>
  );
}
