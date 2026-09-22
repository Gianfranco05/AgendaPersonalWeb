import { TrendingDown } from 'lucide-react';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import { useFinanceReports } from '../../hooks/useFinance';
import FinanceCharts from './FinanceCharts';

export default function ReportsSection() {
  const { data: reports, isLoading } = useFinanceReports();

  if (isLoading && !reports) {
    return (
      <div className="space-y-6">
        <LoadingSkeleton type="card" />
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <LoadingSkeleton type="card" />
          <LoadingSkeleton type="card" />
        </div>
      </div>
    );
  }

  const byCategory = reports?.by_category ?? [];
  const monthly = reports?.monthly ?? [];
  const isEmpty = byCategory.length === 0 && monthly.every((m) => m.income === 0 && m.expense === 0);

  if (isEmpty) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-xl bg-white dark:bg-slate-800 p-12 shadow-sm">
        <TrendingDown size={48} className="text-gray-300 dark:text-slate-600" />
        <p className="text-sm text-gray-500 dark:text-slate-400">Todavía no hay datos suficientes para generar reportes</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
        <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
          <TrendingDown size={16} className="text-rose-500" />
          Total de gastos históricos
        </div>
        <p className="mt-1 text-2xl font-bold text-rose-500">
          ${(reports?.total_expenses ?? 0).toLocaleString('es-AR')}
        </p>
      </div>

      <FinanceCharts />
    </div>
  );
}
