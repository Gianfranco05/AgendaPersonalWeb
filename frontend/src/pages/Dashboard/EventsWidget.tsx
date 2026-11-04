import { useEffect, useState } from 'react';
import { Calendar, MapPin } from 'lucide-react';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import { fetchEvents } from '../../api/endpoints';
import type { CalendarEvent } from '../../types';

function isWithinNext7Days(ev: CalendarEvent): boolean {
  const now = new Date();
  const date = new Date(ev.start_datetime);
  const weekFromNow = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
  // Un evento de todo el día arranca a las 00:00: el de hoy ya "pasó" para
  // `date >= now` y desaparecía del dashboard justo el día que importa.
  const from = ev.is_all_day ? new Date(now.getFullYear(), now.getMonth(), now.getDate()) : now;
  return date >= from && date <= weekFromNow;
}

export default function EventsWidget() {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const data = await fetchEvents();
        if (cancelled) return;
        const upcoming = data
          .filter(isWithinNext7Days)
          .sort((a, b) => new Date(a.start_datetime).getTime() - new Date(b.start_datetime).getTime());
        setEvents(upcoming);
      } catch {
        // Si falla la carga el widget queda vacío en vez de quedarse cargando para siempre.
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return <LoadingSkeleton type="widget" />;
  }

  return (
    <div className="card-interactive rounded-xl bg-white dark:bg-slate-800 p-6 shadow-sm">
      <h3 className="mb-4 text-lg font-semibold text-gray-800 dark:text-slate-100">Próximos eventos</h3>

      {events.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-6 text-center">
          <Calendar size={28} className="text-gray-300 dark:text-slate-600" />
          <p className="text-sm text-gray-400 dark:text-slate-500">Sin eventos próximos</p>
        </div>
      ) : (
        <ul className="space-y-3">
          {events.map((ev) => {
            const date = new Date(ev.start_datetime);
            const day = date.toLocaleDateString('es-AR', { weekday: 'short', day: 'numeric', month: 'short' });
            const time = ev.is_all_day ? 'Todo el día' : date.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });

            return (
              <li key={ev.id} className="flex gap-3">
                <div
                  className="mt-0.5 h-2 w-2 flex-shrink-0 rounded-full"
                  style={{ backgroundColor: ev.color }}
                />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-gray-700 dark:text-slate-200">{ev.title}</p>
                  <p className="text-xs text-gray-400 dark:text-slate-500">
                    {day} {!ev.is_all_day && `· ${time}`}
                  </p>
                  {ev.location && (
                    <p className="flex items-center gap-1 text-xs text-gray-400 dark:text-slate-500">
                      <MapPin size={10} />
                      {ev.location}
                    </p>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
