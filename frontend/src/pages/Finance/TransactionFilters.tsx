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
    <div className="flex flex-wrap items-center gap-3 rounded-xl bg-white p-4 shadow-sm">
      <div className="flex items-center gap-2">
        <label className="text-xs font-medium text-gray-500">Desde</label>
        <input
          type="date"
          value={filters.date_from}
          onChange={(e) => update('date_from', e.target.value)}
          className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs focus:border-[#7C3AED] focus:outline-none focus:ring-1 focus:ring-[#7C3AED]"
        />
      </div>

      <div className="flex items-center gap-2">
        <label className="text-xs font-medium text-gray-500">Hasta</label>
        <input
          type="date"
          value={filters.date_to}
          onChange={(e) => update('date_to', e.target.value)}
          className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs focus:border-[#7C3AED] focus:outline-none focus:ring-1 focus:ring-[#7C3AED]"
        />
      </div>

      <div className="flex items-center gap-2">
        <label className="text-xs font-medium text-gray-500">Tipo</label>
        <select
          value={filters.type}
          onChange={(e) => update('type', e.target.value)}
          className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs focus:border-[#7C3AED] focus:outline-none focus:ring-1 focus:ring-[#7C3AED]"
        >
          <option value="">Todos</option>
          <option value="income">Ingresos</option>
          <option value="expense">Egresos</option>
        </select>
      </div>
    </div>
  );
}
