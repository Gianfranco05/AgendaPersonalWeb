import { useState, useMemo } from 'react';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import { useMetricHabits, useHabitRecordsForGoals, logHabit } from '../../hooks/useHabits';

const DAY_NAMES = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
const MONTH_NAMES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
];

function daysInMonth(year: number, month: number): number {
  return new Date(year, month, 0).getDate();
}

function dateStr(year: number, month: number, day: number): string {
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

export default function MonthlyHabitGrid() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);

  const { data: metrics, isLoading: loadingGoals } = useMetricHabits();
  const goalIds = useMemo(() => (metrics ?? []).map((g) => g.id), [metrics]);
  const { data: recordsByGoal, mutate } = useHabitRecordsForGoals(goalIds, year, month);

  const days = daysInMonth(year, month);

  function valueFor(goalId: string, day: number): number {
    const records = recordsByGoal?.[goalId] ?? [];
    const record = records.find((r) => r.record_date === dateStr(year, month, day));
    return record?.value ?? 0;
  }

  function total(goalId: string): number {
    return (recordsByGoal?.[goalId] ?? []).reduce((sum, r) => sum + r.value, 0);
  }

  function average(goalId: string): number {
    return days > 0 ? total(goalId) / days : 0;
  }

  async function handleCommit(goalId: string, day: number, value: number) {
    await logHabit(goalId, dateStr(year, month, day), value);
    await mutate();
  }

  if (loadingGoals) {
    return <LoadingSkeleton type="card" />;
  }

  if (!metrics || metrics.length === 0) {
    return (
      <div className="rounded-xl bg-white dark:bg-slate-800 p-8 text-center text-sm text-gray-500 dark:text-slate-400">
        No hay hábitos de tipo "Métrica diaria" todavía. Creá uno con "Nuevo hábito" eligiendo el tipo "Métrica diaria" (ej: minutos entrenados, páginas leídas).
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <select
          value={month}
          onChange={(e) => setMonth(Number(e.target.value))}
          className="rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1 text-sm text-gray-700 dark:text-slate-200"
        >
          {MONTH_NAMES.map((name, i) => (
            <option key={name} value={i + 1}>{name}</option>
          ))}
        </select>
        <input
          type="number"
          value={year}
          onChange={(e) => setYear(Number(e.target.value) || now.getFullYear())}
          className="w-20 rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1 text-sm text-gray-700 dark:text-slate-200"
        />
      </div>

      <div className="overflow-x-auto rounded-xl bg-white dark:bg-slate-800 shadow-sm">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 dark:border-slate-700 text-left text-xs text-gray-400 dark:text-slate-500">
              <th className="px-3 py-2 font-medium">Día</th>
              {metrics.map((g) => (
                <th key={g.id} className="px-3 py-2 font-medium">
                  {g.title}{g.unit ? ` (${g.unit})` : ''}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: days }, (_, i) => i + 1).map((day) => {
              const dow = new Date(year, month - 1, day).getDay();
              return (
                <tr key={day} className="border-b border-gray-50 dark:border-slate-800/50">
                  <td className="whitespace-nowrap px-3 py-1 text-xs text-gray-500 dark:text-slate-400">
                    {day} · {DAY_NAMES[dow].slice(0, 3)}
                  </td>
                  {metrics.map((g) => (
                    <td key={g.id} className="px-3 py-1">
                      <input
                        type="number"
                        key={`${g.id}-${day}-${valueFor(g.id, day)}`}
                        defaultValue={valueFor(g.id, day)}
                        onBlur={(e) => handleCommit(g.id, day, Number(e.target.value) || 0)}
                        className="w-16 rounded border border-transparent bg-transparent px-1 py-0.5 text-sm text-gray-700 dark:text-slate-200 hover:border-gray-200 dark:hover:border-slate-600 focus:border-brand-indigo focus:outline-none"
                      />
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-gray-200 dark:border-slate-700 font-semibold text-gray-700 dark:text-slate-200">
              <td className="px-3 py-2 text-xs">TOTAL</td>
              {metrics.map((g) => (
                <td key={g.id} className="px-3 py-2 text-sm">{total(g.id)}</td>
              ))}
            </tr>
            <tr className="text-gray-500 dark:text-slate-400">
              <td className="px-3 py-2 text-xs">PROMEDIO DIARIO</td>
              {metrics.map((g) => (
                <td key={g.id} className="px-3 py-2 text-sm">{average(g.id).toFixed(1)}</td>
              ))}
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}
