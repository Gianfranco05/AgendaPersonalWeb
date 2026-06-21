import { useEffect, useState } from 'react';
import { Calendar, MapPin } from 'lucide-react';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import { fetchEvents } from '../../api/endpoints';
import type { CalendarEvent } from '../../types';

function isWithinNext7Days(dateStr: string): boolean {
  const now = new Date();
  const date = new Date(dateStr);
  const weekFromNow = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
  return date >= now && date <= weekFromNow;
}

export default function EventsWidget() {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      const data = await fetchEvents();
      if (!cancelled) {
        const upcoming = data
          .filter((e) => isWithinNext7Days(e.start_datetime))
          .sort((a, b) => new Date(a.start_datetime).getTime() - new Date(b.start_datetime).getTime());
        setEvents(upcoming);
        setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return <LoadingSkeleton type="widget" />;
  }

  return (
    <div className="rounded-xl bg-white p-6 shadow-sm">
      <h3 className="mb-4 text-lg font-semibold text-gray-800">Próximos eventos</h3>

      {events.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-6 text-center">
          <Calendar size={28} className="text-gray-300" />
          <p className="text-sm text-gray-400">Sin eventos próximos</p>
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
                  <p className="truncate text-sm font-medium text-gray-700">{ev.title}</p>
                  <p className="text-xs text-gray-400">
                    {day} {!ev.is_all_day && `· ${time}`}
                  </p>
                  {ev.location && (
                    <p className="flex items-center gap-1 text-xs text-gray-400">
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
