import { useState } from 'react';
import { Repeat, CheckCircle2, Plus } from 'lucide-react';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import { useHabits, addHabit, editHabit } from '../../hooks/useHabits';
import { checkInGoal } from '../../hooks/useGoals';
import type { Goal } from '../../types';
import CheckInButton from '../Goals/CheckInButton';
import GoalForm from '../Goals/GoalForm';

export default function HabitsPage() {
  const { data: habits, isLoading, mutate } = useHabits();
  const [showForm, setShowForm] = useState(false);
  const [editingHabit, setEditingHabit] = useState<Goal | null>(null);

  function handleNew() {
    setEditingHabit(null);
    setShowForm(true);
  }

  async function handleSave(data: Omit<Goal, 'id'>, id?: string) {
    if (id) {
      await editHabit(id, data);
    } else {
      await addHabit(data);
    }
    await mutate();
  }

  async function handleCheckIn(goal: Goal) {
    const target = goal.target_value || 1;
    const delta = goal.current_value >= target ? -goal.current_value : target - goal.current_value;
    await checkInGoal(goal.id, delta);
    await mutate();
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-800 dark:text-slate-100">Hábitos</h2>
        <button
          onClick={handleNew}
          className="flex items-center gap-2 rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-charcoal-hover"
        >
          <Plus size={16} />
          Nuevo hábito
        </button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <LoadingSkeleton key={i} type="card" />
          ))}
        </div>
      ) : habits && habits.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {habits.map((habit) => {
            const isComplete = habit.current_value >= (habit.target_value || 1);
            return (
              <div key={habit.id} className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm transition-shadow hover:shadow-md">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-habits/10">
                    <Repeat size={18} className="text-brand-habits" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="truncate font-semibold text-gray-800 dark:text-slate-100">{habit.title}</h3>
                    {habit.description && (
                      <p className="truncate text-xs text-gray-500 dark:text-slate-400">{habit.description}</p>
                    )}
                  </div>
                </div>

                {/* Estado simple: no hay historial de check-ins expuesto por la API, solo el estado actual */}
                <div className="mt-4 flex items-center gap-2 text-sm">
                  <div className="flex gap-1">
                    {Array.from({ length: 7 }).map((_, i) => (
                      <span
                        key={i}
                        className={`h-3 w-3 rounded-sm ${
                          isComplete && i === 6 ? 'bg-brand-habits' : 'bg-gray-100 dark:bg-slate-700'
                        }`}
                      />
                    ))}
                  </div>
                  <span className="ml-1 text-xs text-gray-400 dark:text-slate-500">últimos días</span>
                </div>

                <CheckInButton goal={habit} onCheckIn={handleCheckIn} />
              </div>
            );
          })}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl bg-white dark:bg-slate-800 p-12 shadow-sm">
          <CheckCircle2 size={48} className="text-gray-300 dark:text-slate-600" />
          <p className="text-sm text-gray-500 dark:text-slate-400">No hay hábitos aún</p>
          <button
            onClick={handleNew}
            className="flex items-center gap-2 rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-charcoal-hover"
          >
            <Plus size={16} />
            Crear hábito
          </button>
        </div>
      )}

      {showForm && (
        <GoalForm
          goal={editingHabit}
          onClose={() => { setShowForm(false); setEditingHabit(null); }}
          onSave={handleSave}
          initialType="binary"
          lockType
          titleNew="Nuevo hábito"
          titleEdit="Editar hábito"
        />
      )}
    </div>
  );
}
