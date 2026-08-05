import { useState } from 'react';
import { Plus, PiggyBank, Pencil, Trash2 } from 'lucide-react';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import { useSavingsGoals, addSavingsGoal, editSavingsGoal, removeSavingsGoal, depositToSavings } from '../../hooks/useSavings';
import type { Goal } from '../../types';
import GoalForm from '../Goals/GoalForm';

function DepositForm({ goal, onDone }: { goal: Goal; onDone: () => void }) {
  const [amount, setAmount] = useState('');
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const value = Number(amount);
    if (!value) return;
    setSaving(true);
    await depositToSavings(goal.id, value);
    setSaving(false);
    setAmount('');
    onDone();
  }

  return (
    <form onSubmit={handleSubmit} className="mt-3 flex gap-2">
      <input
        type="number"
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
        placeholder="Monto a depositar"
        className="flex-1 rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-2 text-sm focus:border-brand-indigo focus:outline-none focus:ring-1 focus:ring-brand-indigo"
      />
      <button
        type="submit"
        disabled={saving || !amount}
        className="rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-charcoal-hover disabled:opacity-50"
      >
        Depositar
      </button>
    </form>
  );
}

export default function SavingsGoalsSection() {
  const { data: goals, isLoading, mutate } = useSavingsGoals();
  const [showForm, setShowForm] = useState(false);
  const [editingGoal, setEditingGoal] = useState<Goal | null>(null);

  function handleNew() {
    setEditingGoal(null);
    setShowForm(true);
  }

  function handleEdit(goal: Goal) {
    setEditingGoal(goal);
    setShowForm(true);
  }

  async function handleDelete(id: string) {
    await removeSavingsGoal(id);
    await mutate();
  }

  async function handleSave(data: Omit<Goal, 'id'>, id?: string) {
    if (id) {
      await editSavingsGoal(id, data);
    } else {
      await addSavingsGoal(data);
    }
    await mutate();
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-end">
        <button
          onClick={handleNew}
          className="flex items-center gap-2 rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-charcoal-hover"
        >
          <Plus size={16} />
          Nueva meta de ahorro
        </button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <LoadingSkeleton type="card" />
          <LoadingSkeleton type="card" />
        </div>
      ) : !goals || goals.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl bg-white dark:bg-slate-800 p-12 shadow-sm">
          <PiggyBank size={48} className="text-gray-300 dark:text-slate-600" />
          <p className="text-sm text-gray-500 dark:text-slate-400">No hay metas de ahorro aún</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {goals.map((goal) => {
            const pct = goal.target_value > 0 ? Math.min((goal.current_value / goal.target_value) * 100, 100) : 0;
            return (
              <div key={goal.id} className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="font-semibold text-gray-800 dark:text-slate-100">{goal.title}</h4>
                    {goal.description && (
                      <p className="text-xs text-gray-500 dark:text-slate-400">{goal.description}</p>
                    )}
                  </div>
                  <div className="flex gap-1">
                    <button
                      onClick={() => handleEdit(goal)}
                      className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-brand-indigo"
                    >
                      <Pencil size={14} />
                    </button>
                    <button
                      onClick={() => handleDelete(goal.id)}
                      className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 hover:bg-rose-50 hover:text-rose-500"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>

                <div className="mt-3 flex items-center justify-between text-sm">
                  <span className="text-gray-500 dark:text-slate-400">
                    {goal.current_value.toLocaleString('es-AR')} / {goal.target_value.toLocaleString('es-AR')} {goal.unit}
                  </span>
                  <span className="font-medium text-gray-600 dark:text-slate-300">{pct.toFixed(0)}%</span>
                </div>
                <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-slate-700">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{ width: `${pct}%`, backgroundColor: goal.color }}
                  />
                </div>

                <DepositForm goal={goal} onDone={() => mutate()} />
              </div>
            );
          })}
        </div>
      )}

      {showForm && (
        <GoalForm
          goal={editingGoal}
          onClose={() => { setShowForm(false); setEditingGoal(null); }}
          onSave={handleSave}
          initialType="savings"
          lockType
          titleNew="Nueva meta de ahorro"
          titleEdit="Editar meta de ahorro"
        />
      )}
    </div>
  );
}
