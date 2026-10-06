import { useState } from 'react';
import { Plus, Flame, Beef, Wheat, Droplet, Apple } from 'lucide-react';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import { useNutritionSummary, useMeals, removeMeal } from '../../hooks/useNutrition';
import type { Meal, MealType } from '../../types';
import MealCard from './MealCard';
import MealForm from './MealForm';
import { toLocalDateString } from '../../utils/date';

const MEAL_GROUPS: { type: MealType; label: string }[] = [
  { type: 'breakfast', label: 'Desayuno' },
  { type: 'lunch', label: 'Almuerzo' },
  { type: 'dinner', label: 'Cena' },
  { type: 'snack', label: 'Snack' },
];

export default function NutritionPage() {
  const [showForm, setShowForm] = useState(false);
  const [editingMeal, setEditingMeal] = useState<Meal | null>(null);

  const today = toLocalDateString();
  const params = { date_from: today, date_to: today };

  const { data: summary, isLoading: summaryLoading } = useNutritionSummary();
  const { data: meals, isLoading: mealsLoading } = useMeals(params);

  function handleNew() {
    setEditingMeal(null);
    setShowForm(true);
  }

  function handleEdit(meal: Meal) {
    setEditingMeal(meal);
    setShowForm(true);
  }

  async function handleDelete(id: string) {
    if (!window.confirm('¿Eliminar esta comida?')) return;
    await removeMeal(id, params);
  }

  function handleSaved() {
    setShowForm(false);
    setEditingMeal(null);
  }

  const groupedMeals = MEAL_GROUPS.map((group) => ({
    ...group,
    meals: (meals ?? []).filter((m) => m.meal_type === group.type),
  }));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-800 dark:text-slate-100">Nutrición</h2>
        <button
          onClick={handleNew}
          className="flex items-center gap-2 rounded-lg bg-brand-nutrition px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90"
        >
          <Plus size={16} />
          Nueva comida
        </button>
      </div>

      {summaryLoading && !summary ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <LoadingSkeleton type="card" />
          <LoadingSkeleton type="card" />
          <LoadingSkeleton type="card" />
          <LoadingSkeleton type="card" />
        </div>
      ) : summary ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
              <Flame size={16} className="text-brand-nutrition" />
              Calorías hoy
            </div>
            <p className="mt-1 text-2xl font-bold text-brand-nutrition">{summary.today_calories}</p>
          </div>
          <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
              <Beef size={16} className="text-brand-nutrition" />
              Proteína
            </div>
            <p className="mt-1 text-2xl font-bold text-brand-nutrition">{summary.today_protein_g}g</p>
          </div>
          <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
              <Wheat size={16} className="text-brand-nutrition" />
              Carbohidratos
            </div>
            <p className="mt-1 text-2xl font-bold text-brand-nutrition">{summary.today_carbs_g}g</p>
          </div>
          <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
              <Droplet size={16} className="text-brand-nutrition" />
              Grasas
            </div>
            <p className="mt-1 text-2xl font-bold text-brand-nutrition">{summary.today_fat_g}g</p>
          </div>
        </div>
      ) : null}

      {mealsLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {[1, 2, 3, 4].map((i) => (
            <LoadingSkeleton key={i} type="card" />
          ))}
        </div>
      ) : meals && meals.length > 0 ? (
        <div className="space-y-6">
          {groupedMeals.map((group) => (
            group.meals.length > 0 && (
              <div key={group.type}>
                <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-slate-400">
                  {group.label}
                </h3>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  {group.meals.map((meal) => (
                    <MealCard key={meal.id} meal={meal} onEdit={handleEdit} onDelete={handleDelete} />
                  ))}
                </div>
              </div>
            )
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl bg-white dark:bg-slate-800 p-12 shadow-sm">
          <Apple size={48} className="text-gray-300 dark:text-slate-600" />
          <p className="text-sm text-gray-500 dark:text-slate-400">No hay comidas registradas hoy</p>
          <button
            onClick={handleNew}
            className="flex items-center gap-2 rounded-lg bg-brand-nutrition px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90"
          >
            <Plus size={16} />
            Agregar comida
          </button>
        </div>
      )}

      {showForm && (
        <MealForm
          meal={editingMeal}
          params={params}
          onClose={() => { setShowForm(false); setEditingMeal(null); }}
          onSaved={handleSaved}
        />
      )}
    </div>
  );
}
