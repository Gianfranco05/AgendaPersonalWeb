import { useEffect, useState } from 'react';
import { TrendingUp, TrendingDown, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import { fetchFinanceSummary, fetchTransactions } from '../../api/endpoints';
import type { Transaction } from '../../types';
import type { FinanceSummary } from '../../types';

export default function FinanceWidget() {
  const [summary, setSummary] = useState<FinanceSummary | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      const [summaryData, txData] = await Promise.all([
        fetchFinanceSummary(),
        fetchTransactions({ per_page: 5 }),
      ]);
      if (!cancelled) {
        setSummary(summaryData);
        setTransactions(txData.items.slice(0, 5));
        setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return <LoadingSkeleton type="widget" />;
  }

  if (!summary) {
    return (
      <div className="card-interactive rounded-xl bg-white dark:bg-slate-800 p-6 shadow-sm">
        <p className="text-sm text-gray-400 dark:text-slate-500">No hay datos financieros aún</p>
      </div>
    );
  }

  const balance = summary.balance;
  const isPositive = balance >= 0;

  return (
    <div className="card-interactive rounded-xl bg-white dark:bg-slate-800 p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">Finanzas</h3>
        <Link
          to="/finances"
          className="flex items-center gap-1 text-xs font-medium text-brand-indigo hover:underline"
        >
          Ver todo <ArrowRight size={14} />
        </Link>
      </div>

      {/* Balance */}
      <div className="mb-4">
        <span className="text-xs text-gray-500 dark:text-slate-400">Balance actual</span>
        <p className={`text-2xl font-bold ${isPositive ? 'text-emerald-500' : 'text-rose-500'}`}>
          {isPositive ? '+' : '-'}${Math.abs(balance).toLocaleString('es-AR')}
        </p>
      </div>

      {/* Income / Expense cards */}
      <div className="mb-4 grid grid-cols-2 gap-3">
        <div className="rounded-lg bg-emerald-50 p-3">
          <div className="flex items-center gap-2 text-xs text-emerald-700">
            <TrendingUp size={14} />
            <span>Ingresos</span>
          </div>
          <p className="mt-1 text-lg font-semibold text-emerald-600">
            ${summary.total_income.toLocaleString('es-AR')}
          </p>
        </div>
        <div className="rounded-lg bg-rose-50 p-3">
          <div className="flex items-center gap-2 text-xs text-rose-700">
            <TrendingDown size={14} />
            <span>Egresos</span>
          </div>
          <p className="mt-1 text-lg font-semibold text-rose-600">
            ${(summary.total_expenses ?? 0).toLocaleString('es-AR')}
          </p>
        </div>
      </div>

      {/* Last 5 transactions */}
      <div>
        <h4 className="mb-2 text-xs font-medium text-gray-500 dark:text-slate-400">Últimas transacciones</h4>
        {transactions.length === 0 ? (
          <p className="text-xs text-gray-400 dark:text-slate-500">Sin transacciones</p>
        ) : (
          <ul className="space-y-1.5">
            {transactions.map((tx) => (
              <li
                key={tx.id}
                className="flex items-center justify-between rounded-md bg-gray-50 dark:bg-slate-800/60 px-3 py-1.5 text-xs"
              >
                <div className="flex flex-col">
                  <span className="font-medium text-gray-700 dark:text-slate-200">{tx.product_name}</span>
                  <span className="text-gray-400 dark:text-slate-500">{tx.transaction_date}</span>
                </div>
                <span className={`font-semibold ${tx.type === 'income' ? 'text-emerald-500' : 'text-rose-500'}`}>
                  {tx.type === 'income' ? '+' : '-'}${tx.amount.toLocaleString('es-AR')}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
