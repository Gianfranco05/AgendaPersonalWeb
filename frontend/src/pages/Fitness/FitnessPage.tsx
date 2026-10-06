import { useState } from 'react';
import { Plus, CalendarCheck, Dumbbell, CalendarClock } from 'lucide-react';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import { useFitnessSummary, useWorkoutSessions, removeWorkoutSession } from '../../hooks/useFitness';
import type { WorkoutSession } from '../../types';
import WorkoutSessionCard from './WorkoutSessionCard';
import WorkoutSessionForm from './WorkoutSessionForm';
import { parseDateOnly } from '../../utils/date';

export default function FitnessPage() {
  const [showForm, setShowForm] = useState(false);
  const [editingSession, setEditingSession] = useState<WorkoutSession | null>(null);

  const { data: summary, isLoading: summaryLoading } = useFitnessSummary();
  const { data: sessions, isLoading: sessionsLoading } = useWorkoutSessions();

  function handleNew() {
    setEditingSession(null);
    setShowForm(true);
  }

  function handleEdit(session: WorkoutSession) {
    setEditingSession(session);
    setShowForm(true);
  }

  async function handleDelete(id: string) {
    if (!window.confirm('¿Eliminar esta sesión?')) return;
    await removeWorkoutSession(id);
  }

  function handleSaved() {
    setShowForm(false);
    setEditingSession(null);
  }

  const sortedSessions = (sessions ?? []).slice().sort((a, b) => (a.date < b.date ? 1 : -1));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-800 dark:text-slate-100">Gimnasio y Fitness</h2>
        <button
          onClick={handleNew}
          className="flex items-center gap-2 rounded-lg bg-brand-fitness px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90"
        >
          <Plus size={16} />
          Nueva sesión
        </button>
      </div>

      {summaryLoading && !summary ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <LoadingSkeleton type="card" />
          <LoadingSkeleton type="card" />
          <LoadingSkeleton type="card" />
        </div>
      ) : summary ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
              <CalendarCheck size={16} className="text-brand-fitness" />
              Sesiones este mes
            </div>
            <p className="mt-1 text-2xl font-bold text-brand-fitness">{summary.sessions_this_month}</p>
          </div>
          <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
              <Dumbbell size={16} className="text-brand-fitness" />
              Ejercicios totales
            </div>
            <p className="mt-1 text-2xl font-bold text-brand-fitness">{summary.total_exercises}</p>
          </div>
          <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
              <CalendarClock size={16} className="text-brand-fitness" />
              Última sesión
            </div>
            <p className="mt-1 text-2xl font-bold text-brand-fitness">
              {summary.last_session_date
                ? parseDateOnly(summary.last_session_date).toLocaleDateString('es-AR')
                : 'Sin datos'}
            </p>
          </div>
        </div>
      ) : null}

      {sessionsLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <LoadingSkeleton key={i} type="card" />
          ))}
        </div>
      ) : sortedSessions.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {sortedSessions.map((session) => (
            <WorkoutSessionCard
              key={session.id}
              session={session}
              onEdit={handleEdit}
              onDelete={handleDelete}
            />
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl bg-white dark:bg-slate-800 p-12 shadow-sm">
          <Dumbbell size={48} className="text-gray-300 dark:text-slate-600" />
          <p className="text-sm text-gray-500 dark:text-slate-400">No hay sesiones registradas aún</p>
          <button
            onClick={handleNew}
            className="flex items-center gap-2 rounded-lg bg-brand-fitness px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90"
          >
            <Plus size={16} />
            Crear sesión
          </button>
        </div>
      )}

      {showForm && (
        <WorkoutSessionForm
          session={editingSession}
          onClose={() => { setShowForm(false); setEditingSession(null); }}
          onSaved={handleSaved}
        />
      )}
    </div>
  );
}
