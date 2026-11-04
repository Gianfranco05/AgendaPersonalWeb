import { useState } from 'react';
import { Plus, Target } from 'lucide-react';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import { useGoals, addGoal, editGoal, removeGoal, checkInGoal } from '../../hooks/useGoals';
import type { Goal } from '../../types';
import GoalCard from './GoalCard';
import GoalForm from './GoalForm';
import { useOpenParam } from '../../hooks/useOpenParam';

export default function GoalsPage() {
  const [showForm, setShowForm] = useState(false);
  const [editingGoal, setEditingGoal] = useState<Goal | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const { data: goals, isLoading, mutate } = useGoals();

  useOpenParam({
    ready: !isLoading,
    onOpen: ({ id }) => {
      const target = goals?.find((g) => g.id === id);
      if (!target) return false;
      handleEdit(target);
      return true;
    },
  });

  function handleNew() {
    setEditingGoal(null);
    setShowForm(true);
  }

  function handleEdit(goal: Goal) {
    setEditingGoal(goal);
    setShowForm(true);
  }

  function handleDeleteClick(id: string) {
    setDeletingId(id);
  }

  async function handleConfirmDelete() {
    if (!deletingId) return;
    await removeGoal(deletingId);
    await mutate();
    setDeletingId(null);
  }

  async function handleSave(data: Omit<Goal, 'id'>, id?: string) {
    if (id) {
      await editGoal(id, data);
    } else {
      await addGoal(data);
    }
    await mutate();
  }

  async function handleCheckIn(goal: Goal) {
    const target = goal.target_value || 1;
    // progress: suma 1; binary: alterna entre completa (delta hasta target) y reset
    const delta =
      goal.goal_type === 'progress'
        ? 1
        : goal.current_value >= target
          ? -goal.current_value
          : target - goal.current_value;
    await checkInGoal(goal.id, delta);
    await mutate();
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-800 dark:text-slate-100">Metas</h2>
        <button
          onClick={handleNew}
          className="flex items-center gap-2 rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-charcoal-hover"
        >
          <Plus size={16} />
          Nueva meta
        </button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <LoadingSkeleton key={i} type="card" />
          ))}
        </div>
      ) : goals && goals.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {goals.map((goal) => (
            <GoalCard
              key={goal.id}
              goal={goal}
              onEdit={handleEdit}
              onDelete={handleDeleteClick}
              onCheckIn={handleCheckIn}
            />
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl bg-white dark:bg-slate-800 p-12 shadow-sm">
          <Target size={48} className="text-gray-300 dark:text-slate-600" />
          <p className="text-sm text-gray-500 dark:text-slate-400">No hay metas aún</p>
          <button
            onClick={handleNew}
            className="flex items-center gap-2 rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-charcoal-hover"
          >
            <Plus size={16} />
            Crear meta
          </button>
        </div>
      )}

      {showForm && (
        <GoalForm
          goal={editingGoal}
          onClose={() => { setShowForm(false); setEditingGoal(null); }}
          onSave={handleSave}
        />
      )}

      {deletingId && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 px-4 py-8 sm:py-12">
          <div className="w-full max-w-sm rounded-xl bg-white dark:bg-slate-800 p-6 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">Eliminar meta</h3>
            <p className="mt-2 text-sm text-gray-500 dark:text-slate-400">¿Estás seguro de que querés eliminar esta meta?</p>
            <div className="mt-4 flex justify-end gap-3">
              <button
                onClick={() => setDeletingId(null)}
                className="rounded-lg border border-gray-200 dark:border-slate-700 px-4 py-2 text-sm font-medium text-gray-600 dark:text-slate-300 transition-colors hover:bg-gray-50 dark:hover:bg-slate-700/50"
              >
                Cancelar
              </button>
              <button
                onClick={handleConfirmDelete}
                className="rounded-lg bg-rose-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-rose-600"
              >
                Eliminar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
