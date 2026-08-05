import { Clock, Loader2, CheckCircle2, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import { useKanban } from '../../hooks/useKanban';

export default function TasksWidget() {
  const { tasks, areas, isLoading } = useKanban();

  if (isLoading) {
    return <LoadingSkeleton type="widget" />;
  }

  const counts = {
    pending: tasks.filter((t) => t.status === 'pending').length,
    in_progress: tasks.filter((t) => t.status === 'in_progress').length,
    completed: tasks.filter((t) => t.status === 'completed').length,
  };

  const items = [
    { label: 'Pendiente', count: counts.pending, icon: Clock, color: 'text-amber-500', bg: 'bg-amber-50 dark:bg-amber-500/10' },
    { label: 'En Proceso', count: counts.in_progress, icon: Loader2, color: 'text-blue-500', bg: 'bg-blue-50 dark:bg-blue-500/10' },
    { label: 'Completado', count: counts.completed, icon: CheckCircle2, color: 'text-emerald-500', bg: 'bg-emerald-50 dark:bg-emerald-500/10' },
  ];

  const byArea = areas.map((area) => ({
    area,
    pending: tasks.filter((t) => t.area === area && t.status !== 'completed').length,
    done: tasks.filter((t) => t.area === area && t.status === 'completed').length,
  }));

  return (
    <div className="card-interactive rounded-xl bg-white dark:bg-slate-800 p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">Tareas</h3>
        <Link
          to="/tasks"
          className="flex items-center gap-1 text-xs font-medium text-brand-indigo hover:underline"
        >
          Ver todas <ArrowRight size={14} />
        </Link>
      </div>

      <div className="space-y-2">
        {items.map(({ label, count, icon: Icon, color, bg }) => (
          <div key={label} className={`flex items-center justify-between rounded-lg ${bg} p-3`}>
            <div className="flex items-center gap-2">
              <Icon size={16} className={color} />
              <span className="text-sm font-medium text-gray-700 dark:text-slate-200">{label}</span>
            </div>
            <span className={`text-lg font-bold ${color}`}>{count}</span>
          </div>
        ))}
      </div>

      {byArea.length > 0 && (
        <div className="mt-4 border-t border-gray-100 dark:border-slate-700 pt-3">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-gray-400 dark:text-slate-500">
                <th className="pb-1 text-left font-medium">Área</th>
                <th className="pb-1 text-right font-medium">Pendientes</th>
                <th className="pb-1 text-right font-medium">Hechas</th>
              </tr>
            </thead>
            <tbody>
              {byArea.map(({ area, pending, done }) => (
                <tr key={area} className="text-gray-600 dark:text-slate-300">
                  <td className="py-0.5">{area}</td>
                  <td className="py-0.5 text-right">{pending}</td>
                  <td className="py-0.5 text-right">{done}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
