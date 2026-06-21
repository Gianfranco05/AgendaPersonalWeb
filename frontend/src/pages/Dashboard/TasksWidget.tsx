import { useEffect, useState } from 'react';
import { Clock, Loader2, CheckCircle2, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';

interface TaskCounts {
  pending: number;
  in_progress: number;
  completed: number;
}

function loadTaskCounts(): TaskCounts {
  const stored = localStorage.getItem('kanban-tasks');
  if (!stored) return { pending: 0, in_progress: 0, completed: 0 };
  try {
    const tasks = JSON.parse(stored);
    return {
      pending: tasks.filter((t: { status: string }) => t.status === 'pending').length,
      in_progress: tasks.filter((t: { status: string }) => t.status === 'in_progress').length,
      completed: tasks.filter((t: { status: string }) => t.status === 'completed').length,
    };
  } catch {
    return { pending: 0, in_progress: 0, completed: 0 };
  }
}

export default function TasksWidget() {
  const [counts, setCounts] = useState<TaskCounts>({ pending: 0, in_progress: 0, completed: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setCounts(loadTaskCounts());
    setLoading(false);

    const handleStorage = () => {
      setCounts(loadTaskCounts());
    };
    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, []);

  if (loading) {
    return <LoadingSkeleton type="widget" />;
  }

  const items = [
    { label: 'Pendiente', count: counts.pending, icon: Clock, color: 'text-amber-500', bg: 'bg-amber-50' },
    { label: 'En Proceso', count: counts.in_progress, icon: Loader2, color: 'text-blue-500', bg: 'bg-blue-50' },
    { label: 'Completado', count: counts.completed, icon: CheckCircle2, color: 'text-emerald-500', bg: 'bg-emerald-50' },
  ];

  return (
    <div className="rounded-xl bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-800">Tareas</h3>
        <Link
          to="/tasks"
          className="flex items-center gap-1 text-xs font-medium text-[#7C3AED] hover:underline"
        >
          Ver todas <ArrowRight size={14} />
        </Link>
      </div>

      <div className="space-y-2">
        {items.map(({ label, count, icon: Icon, color, bg }) => (
          <div key={label} className={`flex items-center justify-between rounded-lg ${bg} p-3`}>
            <div className="flex items-center gap-2">
              <Icon size={16} className={color} />
              <span className="text-sm font-medium text-gray-700">{label}</span>
            </div>
            <span className={`text-lg font-bold ${color}`}>{count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
