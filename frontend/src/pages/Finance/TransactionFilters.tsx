interface Filters {
  date_from: string;
  date_to: string;
  category: string;
  type: string;
}

interface TransactionFiltersProps {
  filters: Filters;
  onChange: (filters: Filters) => void;
}

export default function TransactionFilters({ filters, onChange }: TransactionFiltersProps) {
  function update<K extends keyof Filters>(key: K, value: Filters[K]) {
    onChange({ ...filters, [key]: value });
  }

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl bg-white dark:bg-slate-800 p-4 shadow-sm">
      <div className="flex items-center gap-2">
        <label className="text-xs font-medium text-gray-500 dark:text-slate-400">Desde</label>
        <input
          type="date"
          value={filters.date_from}
          onChange={(e) => update('date_from', e.target.value)}
          className="rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-1.5 text-xs focus:border-brand-indigo focus:outline-none focus:ring-1 focus:ring-brand-indigo"
        />
      </div>

      <div className="flex items-center gap-2">
        <label className="text-xs font-medium text-gray-500 dark:text-slate-400">Hasta</label>
        <input
          type="date"
          value={filters.date_to}
          onChange={(e) => update('date_to', e.target.value)}
          className="rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-1.5 text-xs focus:border-brand-indigo focus:outline-none focus:ring-1 focus:ring-brand-indigo"
        />
      </div>

      <div className="flex items-center gap-2">
        <label className="text-xs font-medium text-gray-500 dark:text-slate-400">Tipo</label>
        <select
          value={filters.type}
          onChange={(e) => update('type', e.target.value)}
          className="rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-1.5 text-xs focus:border-brand-indigo focus:outline-none focus:ring-1 focus:ring-brand-indigo"
        >
          <option value="">Todos</option>
          <option value="income">Ingresos</option>
          <option value="expense">Egresos</option>
        </select>
      </div>
    </div>
  );
}
