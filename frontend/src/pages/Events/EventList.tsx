import { useState } from 'react';
import { Calendar, Trash2, Pencil } from 'lucide-react';
import type { CalendarEvent } from '../../types';

interface Props {
  events: CalendarEvent[];
  onEdit: (event: CalendarEvent) => void;
  onDelete: (id: string) => void;
}

function formatDate(iso: string, allDay: boolean) {
  const d = new Date(iso);
  return d.toLocaleDateString('es-AR', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    // Un evento de todo el día se guarda a las 00:00: mostrar esa hora no dice nada.
    ...(!allDay && { hour: '2-digit', minute: '2-digit' }),
  });
}

export default function EventList({ events, onEdit, onDelete }: Props) {
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const sorted = [...events].sort(
    (a, b) => new Date(a.start_datetime).getTime() - new Date(b.start_datetime).getTime()
  );

  if (sorted.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-xl bg-white dark:bg-slate-800 p-8 shadow-sm">
        <Calendar size={40} className="text-gray-300 dark:text-slate-600" />
        <p className="text-sm text-gray-500 dark:text-slate-400">No hay eventos próximos</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl bg-white dark:bg-slate-800 shadow-sm">
      <div className="border-b border-gray-100 dark:border-slate-800 px-4 py-3">
        <h3 className="text-sm font-semibold text-gray-800 dark:text-slate-100">Próximos eventos</h3>
      </div>
      <div className="divide-y divide-gray-50">
        {sorted.map((ev) => (
          <div key={ev.id} className="flex items-start gap-3 px-4 py-3">
            <span
              className="mt-1 inline-block h-3 w-3 shrink-0 rounded-full"
              style={{ backgroundColor: ev.color }}
            />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-gray-800 dark:text-slate-100">{ev.title}</p>
              <p className="mt-0.5 text-xs text-gray-500 dark:text-slate-400">
                {formatDate(ev.start_datetime, ev.is_all_day)}
                {ev.is_all_day && ' (todo el día)'}
              </p>
              {ev.location && (
                <p className="mt-0.5 text-xs text-gray-400 dark:text-slate-500">{ev.location}</p>
              )}
            </div>
            <div className="flex shrink-0 gap-1">
              <button
                onClick={() => onEdit(ev)}
                className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 transition-colors hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-brand-indigo"
                title="Editar"
              >
                <Pencil size={14} />
              </button>
              {deletingId === ev.id ? (
                <div className="flex gap-1">
                  <button
                    onClick={() => {
                      onDelete(ev.id);
                      setDeletingId(null);
                    }}
                    className="rounded-lg bg-rose-500 px-2 py-1 text-xs font-medium text-white transition-colors hover:bg-rose-600"
                  >
                    Eliminar
                  </button>
                  <button
                    onClick={() => setDeletingId(null)}
                    className="rounded-lg border border-gray-200 dark:border-slate-700 px-2 py-1 text-xs font-medium text-gray-600 dark:text-slate-300 transition-colors hover:bg-gray-50 dark:hover:bg-slate-700/50"
                  >
                    Cancelar
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setDeletingId(ev.id)}
                  className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 transition-colors hover:bg-rose-50 hover:text-rose-500"
                  title="Eliminar"
                >
                  <Trash2 size={14} />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
