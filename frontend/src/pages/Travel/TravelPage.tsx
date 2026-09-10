import { useState } from 'react';
import { Plane, Plus, Pencil, Trash2, ChevronDown, Luggage } from 'lucide-react';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import ModuleLockedNotice, { isPaymentRequiredError } from '../../components/ModuleLockedNotice';
import { useTrips, useTravelSummary, removeTrip } from '../../hooks/useTravel';
import type { Trip, TripStatus } from '../../types';
import TripForm from './TripForm';
import PackingChecklist from './PackingChecklist';

const STATUS_LABELS: Record<TripStatus, string> = {
  planeado: 'Planeado',
  en_curso: 'En curso',
  completado: 'Completado',
};

const STATUS_CLASSES: Record<TripStatus, string> = {
  planeado: 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-300',
  en_curso: 'bg-sky-100 text-sky-600 dark:bg-sky-950 dark:text-sky-400',
  completado: 'bg-emerald-100 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-400',
};

function formatDate(value: string | null): string | null {
  if (!value) return null;
  const [year, month, day] = value.split('-');
  return `${day}/${month}/${year}`;
}

export default function TravelPage() {
  const { data: trips, isLoading, error: tripsError } = useTrips();
  const { data: summary, error: summaryError } = useTravelSummary();
  const [formOpen, setFormOpen] = useState(false);
  const [editingTrip, setEditingTrip] = useState<Trip | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const error = tripsError ?? summaryError;
  if (isPaymentRequiredError(error)) {
    return <ModuleLockedNotice moduleName="Viajes y Equipaje" />;
  }

  function handleNew() {
    setEditingTrip(null);
    setFormOpen(true);
  }

  function handleEdit(trip: Trip) {
    setEditingTrip(trip);
    setFormOpen(true);
  }

  async function handleDelete(trip: Trip) {
    if (!confirm(`Se borra "${trip.destination}" y su checklist. ¿Seguro?`)) return;
    await removeTrip(trip.id);
    if (expandedId === trip.id) setExpandedId(null);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-2xl font-bold text-gray-800 dark:text-slate-100">
          <Plane className="text-brand-travel" size={24} />
          Viajes y Equipaje
        </h2>
        <button
          onClick={handleNew}
          className="flex items-center gap-2 rounded-lg bg-brand-travel px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90"
        >
          <Plus size={16} />
          Nuevo viaje
        </button>
      </div>

      {isLoading ? (
        <LoadingSkeleton type="page" />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
              <p className="text-sm text-gray-500 dark:text-slate-400">Planeados</p>
              <p className="mt-1 text-2xl font-bold text-gray-800 dark:text-slate-100">
                {summary?.planeados ?? 0}
              </p>
            </div>
            <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
              <p className="text-sm text-gray-500 dark:text-slate-400">Completados</p>
              <p className="mt-1 text-2xl font-bold text-emerald-500">{summary?.completados ?? 0}</p>
            </div>
            <div className="col-span-2 rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm sm:col-span-1">
              <p className="text-sm text-gray-500 dark:text-slate-400">Próximo viaje</p>
              <p className="mt-1 truncate text-sm font-semibold text-gray-800 dark:text-slate-100">
                {summary?.next_trip
                  ? `${summary.next_trip.destination}${
                      formatDate(summary.next_trip.start_date)
                        ? ` · ${formatDate(summary.next_trip.start_date)}`
                        : ''
                    }`
                  : '—'}
              </p>
            </div>
          </div>

          {(trips ?? []).length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-3 rounded-xl bg-white dark:bg-slate-800 p-12 shadow-sm">
              <Luggage size={48} className="text-gray-300 dark:text-slate-600" />
              <p className="text-sm text-gray-500 dark:text-slate-400">Todavía no cargaste ningún viaje</p>
              <button
                onClick={handleNew}
                className="flex items-center gap-2 rounded-lg bg-brand-travel px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90"
              >
                <Plus size={16} />
                Agregar viaje
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {(trips ?? []).map((trip) => {
                const expanded = expandedId === trip.id;
                return (
                  <div key={trip.id} className="rounded-xl bg-white dark:bg-slate-800 p-4 shadow-sm">
                    <div className="flex items-center justify-between gap-3">
                      <button
                        onClick={() => setExpandedId(expanded ? null : trip.id)}
                        className="flex flex-1 items-center gap-2 text-left"
                      >
                        <ChevronDown
                          size={16}
                          className={`shrink-0 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
                        />
                        <div className="min-w-0">
                          <p className="truncate font-medium text-gray-800 dark:text-slate-100">
                            {trip.destination}
                          </p>
                          {formatDate(trip.start_date) ? (
                            <p className="text-xs text-gray-500 dark:text-slate-400">
                              {formatDate(trip.start_date)}
                              {formatDate(trip.end_date) ? ` – ${formatDate(trip.end_date)}` : ''}
                            </p>
                          ) : null}
                        </div>
                      </button>
                      <span
                        className={`shrink-0 rounded-full px-2 py-1 text-[11px] font-medium ${STATUS_CLASSES[trip.status]}`}
                      >
                        {STATUS_LABELS[trip.status]}
                      </span>
                      <div className="flex shrink-0 gap-1">
                        <button
                          onClick={() => handleEdit(trip)}
                          className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 transition-colors hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-brand-travel"
                          title="Editar"
                        >
                          <Pencil size={14} />
                        </button>
                        <button
                          onClick={() => handleDelete(trip)}
                          className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 transition-colors hover:bg-rose-50 hover:text-rose-500"
                          title="Eliminar"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>

                    {expanded ? <PackingChecklist tripId={trip.id} /> : null}
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}

      {formOpen && <TripForm trip={editingTrip} onClose={() => setFormOpen(false)} />}
    </div>
  );
}
