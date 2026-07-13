import { useState } from 'react';
import { CheckCircle, Loader } from 'lucide-react';
import type { Goal } from '../../types';

interface Props {
  goal: Goal;
  onCheckIn: (goal: Goal) => Promise<void>;
}

export default function CheckInButton({ goal, onCheckIn }: Props) {
  const [loading, setLoading] = useState(false);

  async function handleClick() {
    setLoading(true);
    try {
      await onCheckIn(goal);
    } finally {
      setLoading(false);
    }
  }

  const isComplete = goal.current_value >= goal.target_value;

  if (isComplete && goal.goal_type === 'binary') {
    return (
      <div className="flex items-center justify-center gap-2 rounded-lg bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-600">
        <CheckCircle size={16} />
        Completada
      </div>
    );
  }

  return (
    <button
      onClick={handleClick}
      disabled={loading}
      className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-2 text-sm font-medium text-gray-600 dark:text-slate-300 transition-colors hover:border-brand-indigo hover:text-brand-indigo disabled:opacity-50"
    >
      {loading ? <Loader size={16} className="animate-spin" /> : <CheckCircle size={16} />}
      {loading ? 'Guardando…' : isComplete ? 'Completada' : 'Check-in'}
    </button>
  );
}
