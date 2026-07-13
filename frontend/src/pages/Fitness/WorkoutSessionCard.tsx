import { Pencil, Trash2, Clock, Dumbbell } from 'lucide-react';
import type { WorkoutSession } from '../../types';

interface Props {
  session: WorkoutSession;
  onEdit: (session: WorkoutSession) => void;
  onDelete: (id: string) => void;
}

export default function WorkoutSessionCard({ session, onEdit, onDelete }: Props) {
  return (
    <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-semibold text-gray-800 dark:text-slate-100">{session.name}</h3>
          <div className="mt-1 flex items-center gap-3 text-xs text-gray-500 dark:text-slate-400">
            <span>{new Date(session.date).toLocaleDateString('es-AR')}</span>
            {session.duration_minutes != null && (
              <span className="flex items-center gap-1">
                <Clock size={12} />
                {session.duration_minutes} min
              </span>
            )}
          </div>
        </div>
        <div className="flex gap-1">
          <button
            onClick={() => onEdit(session)}
            className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 transition-colors hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-brand-fitness"
            title="Editar"
          >
            <Pencil size={14} />
          </button>
          <button
            onClick={() => onDelete(session.id)}
            className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 transition-colors hover:bg-rose-50 hover:text-rose-500"
            title="Eliminar"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {session.notes && <p className="mt-2 text-xs text-gray-500 dark:text-slate-400">{session.notes}</p>}

      {session.exercises.length > 0 && (
        <div className="mt-4 space-y-1.5 border-t border-gray-100 dark:border-slate-800 pt-3">
          {session.exercises
            .slice()
            .sort((a, b) => a.order - b.order)
            .map((ex, i) => (
              <div key={ex.id ?? i} className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2 text-gray-700 dark:text-slate-200">
                  <Dumbbell size={13} className="text-brand-fitness" />
                  {ex.name}
                </span>
                <span className="text-gray-500 dark:text-slate-400">
                  {ex.sets}×{ex.reps}
                  {ex.weight_kg != null ? ` · ${ex.weight_kg}kg` : ''}
                </span>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
