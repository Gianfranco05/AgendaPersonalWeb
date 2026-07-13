import { useMemo } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import type { CalendarEvent } from '../../types';

const DAYS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];

function getMonthGrid(year: number, month: number) {
  const firstDay = new Date(year, month, 1);
  const startOffset = (firstDay.getDay() + 6) % 7;
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells: (number | null)[] = [];
  for (let i = 0; i < startOffset; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  return cells;
}

interface Props {
  year: number;
  month: number;
  events: CalendarEvent[];
  onPrevMonth: () => void;
  onNextMonth: () => void;
  onDayClick: (day: number) => void;
}

export default function CalendarGrid({ year, month, events, onPrevMonth, onNextMonth, onDayClick }: Props) {
  const cells = useMemo(() => getMonthGrid(year, month), [year, month]);
  const monthNames = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
  ];

  function eventsForDay(day: number) {
    const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    return events.filter((e) => e.start_datetime.startsWith(dateStr));
  }

  return (
    <div className="rounded-xl bg-white dark:bg-slate-800 p-4 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <button
          onClick={onPrevMonth}
          className="rounded-lg p-1.5 text-gray-500 dark:text-slate-400 transition-colors hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-gray-700 dark:hover:text-slate-100"
          aria-label="Mes anterior"
        >
          <ChevronLeft size={20} />
        </button>
        <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">
          {monthNames[month]} {year}
        </h3>
        <button
          onClick={onNextMonth}
          className="rounded-lg p-1.5 text-gray-500 dark:text-slate-400 transition-colors hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-gray-700 dark:hover:text-slate-100"
          aria-label="Mes siguiente"
        >
          <ChevronRight size={20} />
        </button>
      </div>

      <div className="grid grid-cols-7 gap-px">
        {DAYS.map((d) => (
          <div key={d} className="p-2 text-center text-xs font-medium text-gray-500 dark:text-slate-400">
            {d}
          </div>
        ))}
        {cells.map((day, i) => {
          const dayEvents = day ? eventsForDay(day) : [];
          return (
            <button
              key={i}
              disabled={!day}
              onClick={() => day && onDayClick(day)}
              className={`relative min-h-[60px] rounded-lg p-1.5 text-left text-sm transition-colors ${
                day
                  ? 'cursor-pointer hover:bg-violet-50'
                  : 'cursor-default'
              }`}
            >
              {day && (
                <>
                  <span className="text-xs font-medium text-gray-700 dark:text-slate-200">{day}</span>
                  {dayEvents.length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-0.5">
                      {dayEvents.slice(0, 3).map((ev) => (
                        <span
                          key={ev.id}
                          className="inline-block h-1.5 w-1.5 rounded-full"
                          style={{ backgroundColor: ev.color }}
                        />
                      ))}
                      {dayEvents.length > 3 && (
                        <span className="text-[10px] text-gray-400 dark:text-slate-500">+{dayEvents.length - 3}</span>
                      )}
                    </div>
                  )}
                </>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
