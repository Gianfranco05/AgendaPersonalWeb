import { Pencil, Trash2, CheckCircle } from 'lucide-react';
import type { Goal } from '../../types';

interface Props {
  goal: Goal;
  onEdit: (goal: Goal) => void;
  onDelete: (id: string) => void;
  onCheckIn: (goal: Goal) => void;
}

function ProgressRing({ percentage, color, size = 64 }: { percentage: number; color: string; size?: number }) {
  const strokeWidth = 4;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percentage / 100) * circumference;

  return (
    <svg width={size} height={size} className="shrink-0">
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        className="stroke-gray-200 dark:stroke-slate-700"
        strokeWidth={strokeWidth}
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
        className="transition-all duration-500"
      />
      <text
        x="50%"
        y="50%"
        dominantBaseline="central"
        textAnchor="middle"
        className="text-xs font-bold"
        fill="currentColor"
      >
        {Math.round(percentage)}%
      </text>
    </svg>
  );
}

function daysRemaining(deadline: string | null): { text: string; isOverdue: boolean } {
  if (!deadline) return { text: 'Sin fecha', isOverdue: false };
  const now = new Date();
  const end = new Date(deadline);
  const diff = Math.ceil((end.getTime() - now.getTime()) / 86400000);
  if (diff < 0) return { text: 'Vencida', isOverdue: true };
  if (diff === 0) return { text: 'Hoy', isOverdue: false };
  if (diff === 1) return { text: '1 día', isOverdue: false };
  return { text: `${diff} días`, isOverdue: false };
}

export default function GoalCard({ goal, onEdit, onDelete, onCheckIn }: Props) {
  const percentage = goal.target_value > 0 ? (goal.current_value / goal.target_value) * 100 : 0;
  const cappedPct = Math.min(percentage, 100);
  const deadline = daysRemaining(goal.end_date);

  return (
    <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <ProgressRing percentage={cappedPct} color={goal.color} />
          <div>
            <h3 className="font-semibold text-gray-800 dark:text-slate-100">{goal.title}</h3>
            <p className="mt-0.5 text-xs text-gray-500 dark:text-slate-400">{goal.description}</p>
          </div>
        </div>
        <div className="flex gap-1">
          <button
            onClick={() => onEdit(goal)}
            className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 transition-colors hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-brand-indigo"
            title="Editar"
          >
            <Pencil size={14} />
          </button>
          <button
            onClick={() => onDelete(goal.id)}
            className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 transition-colors hover:bg-rose-50 hover:text-rose-500"
            title="Eliminar"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      <div className="mt-4 space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-500 dark:text-slate-400">
            {goal.current_value} / {goal.target_value} {goal.unit ?? ''}
          </span>
          <span className={`font-medium ${deadline.isOverdue ? 'text-rose-500' : 'text-gray-600 dark:text-slate-300'}`}>
            {deadline.text}
          </span>
        </div>

        <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-slate-700">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${cappedPct}%`, backgroundColor: goal.color }}
          />
        </div>
      </div>

      {goal.goal_type === 'metric' ? (
        <p className="mt-4 text-center text-xs text-gray-400 dark:text-slate-500">
          Se registra desde Hábitos → Registro mensual
        </p>
      ) : goal.goal_type === 'savings' ? (
        <p className="mt-4 text-center text-xs text-gray-400 dark:text-slate-500">
          Se gestiona desde Finanzas → Ahorro
        </p>
      ) : (
        <button
          onClick={() => onCheckIn(goal)}
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-2 text-sm font-medium text-gray-600 dark:text-slate-300 transition-colors hover:border-brand-indigo hover:text-brand-indigo"
        >
          <CheckCircle size={16} />
          Check-in
        </button>
      )}
    </div>
  );
}
