import { useState, useEffect } from 'react';
import { Plus, Pencil, Trash2 } from 'lucide-react';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import { useBudgets, saveBudget, removeBudget, useCategories } from '../../hooks/useFinance';
import type { Budget, BudgetProgress } from '../../types';

const MONTH_NAMES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
];

const inputCls =
  'w-full rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-2 text-sm focus:border-brand-indigo focus:outline-none focus:ring-1 focus:ring-brand-indigo';

function BudgetForm({
  budget,
  year,
  month,
  onClose,
}: {
  budget: BudgetProgress | null;
  year: number;
  month: number;
  onClose: () => void;
}) {
  const { data: categories } = useCategories();
  const [categoryId, setCategoryId] = useState(budget?.category_id ?? '');
  const [amount, setAmount] = useState(budget ? String(budget.amount) : '');
  const [alertThreshold, setAlertThreshold] = useState(budget ? String(budget.alert_threshold) : '80');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!categoryId && categories && categories.length > 0) {
      setCategoryId(categories[0].id);
    }
  }, [categories, categoryId]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!categoryId || !amount) return;
    setSaving(true);
    const data: Omit<Budget, 'id'> = {
      category_id: categoryId,
      amount: Number(amount),
      period: 'monthly',
      alert_threshold: Number(alertThreshold) || 80,
    };
    await saveBudget(budget as Budget | null, data, year, month);
    setSaving(false);
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 px-4 py-8 sm:py-12">
      <div className="w-full max-w-md rounded-xl bg-white dark:bg-slate-800 shadow-xl">
        <div className="border-b border-gray-100 dark:border-slate-800 px-6 py-4">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">
            {budget ? 'Editar presupuesto' : 'Nuevo presupuesto'}
          </h3>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4 px-6 py-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Categoría</label>
            <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)} className={inputCls}>
              {(categories ?? []).map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Monto mensual</label>
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className={inputCls}
              placeholder="50000"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">
              Alertar al superar (%)
            </label>
            <input
              type="number"
              value={alertThreshold}
              onChange={(e) => setAlertThreshold(e.target.value)}
              className={inputCls}
              placeholder="80"
            />
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
              disabled={saving || !categoryId || !amount}
              className="rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-charcoal-hover disabled:opacity-50"
            >
              {saving ? 'Guardando…' : budget ? 'Actualizar' : 'Crear'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function BudgetsSection() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<BudgetProgress | null>(null);

  const { data: budgets, isLoading } = useBudgets(year, month);

  function handleNew() {
    setEditing(null);
    setShowForm(true);
  }

  function handleEdit(budget: BudgetProgress) {
    setEditing(budget);
    setShowForm(true);
  }

  async function handleDelete(id: string) {
    if (!window.confirm('¿Eliminar este presupuesto?')) return;
    await removeBudget(id, year, month);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <select
            value={month}
            onChange={(e) => setMonth(Number(e.target.value))}
            className="rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1 text-sm text-gray-700 dark:text-slate-200"
          >
            {MONTH_NAMES.map((name, i) => (
              <option key={name} value={i + 1}>{name}</option>
            ))}
          </select>
          <input
            type="number"
            value={year}
            onChange={(e) => setYear(Number(e.target.value) || now.getFullYear())}
            className="w-20 rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1 text-sm text-gray-700 dark:text-slate-200"
          />
        </div>
        <button
          onClick={handleNew}
          className="flex items-center gap-2 rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-charcoal-hover"
        >
          <Plus size={16} />
          Nuevo presupuesto
        </button>
      </div>

      {isLoading ? (
        <LoadingSkeleton type="card" />
      ) : !budgets || budgets.length === 0 ? (
        <div className="rounded-xl bg-white dark:bg-slate-800 p-8 text-center text-sm text-gray-500 dark:text-slate-400">
          No hay presupuestos para este mes todavía.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {budgets.map((budget) => {
            const capped = Math.min(budget.percentage, 100);
            const overThreshold = budget.percentage >= budget.alert_threshold;
            const barColor = budget.percentage >= 100 ? 'bg-rose-500' : overThreshold ? 'bg-amber-500' : 'bg-emerald-500';
            return (
              <div key={budget.id} className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
                <div className="flex items-center justify-between">
                  <h4 className="font-semibold text-gray-800 dark:text-slate-100">{budget.category_name}</h4>
                  <div className="flex gap-1">
                    <button
                      onClick={() => handleEdit(budget)}
                      className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-brand-indigo"
                    >
                      <Pencil size={14} />
                    </button>
                    <button
                      onClick={() => handleDelete(budget.id)}
                      className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 hover:bg-rose-50 hover:text-rose-500"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
                <div className="mt-3 flex items-center justify-between text-sm">
                  <span className="text-gray-500 dark:text-slate-400">
                    ${budget.spent.toLocaleString('es-AR')} / ${budget.amount.toLocaleString('es-AR')}
                  </span>
                  <span className={overThreshold ? 'font-medium text-rose-500' : 'text-gray-500 dark:text-slate-400'}>
                    {budget.percentage.toFixed(0)}%
                  </span>
                </div>
                <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-slate-700">
                  <div className={`h-full rounded-full ${barColor}`} style={{ width: `${capped}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {showForm && (
        <BudgetForm budget={editing} year={year} month={month} onClose={() => setShowForm(false)} />
      )}
    </div>
  );
}
