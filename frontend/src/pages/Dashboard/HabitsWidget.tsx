import { Repeat, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import { useMonthlySummary } from '../../hooks/useHabits';

export default function HabitsWidget() {
  const now = new Date();
  const { data: summary, isLoading } = useMonthlySummary(now.getFullYear(), now.getMonth() + 1);

  if (isLoading) {
    return <LoadingSkeleton type="widget" />;
  }

  return (
    <div className="card-interactive rounded-xl bg-white dark:bg-slate-800 p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">Hábitos del mes</h3>
        <Link
          to="/habits"
          className="flex items-center gap-1 text-xs font-medium text-brand-indigo hover:underline"
        >
          Ver todos <ArrowRight size={14} />
        </Link>
      </div>

      {!summary || summary.length === 0 ? (
        <p className="text-sm text-gray-400 dark:text-slate-500">
          No hay hábitos de tipo "Métrica diaria" todavía.
        </p>
      ) : (
        <ul className="space-y-2">
          {summary.map((item) => (
            <li
              key={item.goal_id}
              className="flex items-center justify-between rounded-lg border border-gray-100 dark:border-slate-800 p-3"
            >
              <div className="flex items-center gap-2">
                <Repeat size={16} className="text-brand-habits" />
                <span className="text-sm font-medium text-gray-700 dark:text-slate-200">{item.title}</span>
              </div>
              <div className="text-right">
                <div className="text-sm font-bold text-gray-800 dark:text-slate-100">
                  {item.total} {item.unit ?? ''}
                </div>
                <div className="text-[11px] text-gray-400 dark:text-slate-500">
                  prom. {item.average.toFixed(1)} / día
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
