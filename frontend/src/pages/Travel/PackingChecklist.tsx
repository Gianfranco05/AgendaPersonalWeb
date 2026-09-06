import { useState } from 'react';
import { Trash2 } from 'lucide-react';
import { usePackingItems, addItem, toggleItemPacked, removeItem } from '../../hooks/useTravel';

interface Props {
  tripId: string;
}

export default function PackingChecklist({ tripId }: Props) {
  const { data: items, isLoading } = usePackingItems(tripId);
  const [newItem, setNewItem] = useState('');
  const [adding, setAdding] = useState(false);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!newItem.trim()) return;
    setAdding(true);
    try {
      await addItem(tripId, newItem.trim());
      setNewItem('');
    } finally {
      setAdding(false);
    }
  }

  return (
    <div className="mt-3 rounded-lg bg-gray-50 dark:bg-slate-900/40 p-4">
      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-slate-400">
        Equipaje
      </h4>

      {isLoading ? (
        <p className="text-xs text-gray-500 dark:text-slate-400">Cargando…</p>
      ) : (items ?? []).length === 0 ? (
        <p className="mb-2 text-xs text-gray-500 dark:text-slate-400">Nada en la lista todavía.</p>
      ) : (
        <ul className="mb-3 space-y-1">
          {(items ?? []).map((item) => (
            <li key={item.id} className="flex items-center justify-between gap-2 py-0.5">
              <label className="flex flex-1 cursor-pointer items-center gap-2">
                <input
                  type="checkbox"
                  checked={item.packed}
                  onChange={(e) => toggleItemPacked(tripId, item.id, e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-brand-travel focus:ring-brand-travel"
                />
                <span
                  className={
                    item.packed
                      ? 'text-sm text-gray-400 line-through dark:text-slate-500'
                      : 'text-sm text-gray-700 dark:text-slate-200'
                  }
                >
                  {item.name}
                </span>
              </label>
              <button
                onClick={() => removeItem(tripId, item.id)}
                className="rounded-lg p-1 text-gray-400 dark:text-slate-500 transition-colors hover:bg-rose-50 hover:text-rose-500"
                title="Borrar item"
              >
                <Trash2 size={14} />
              </button>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={handleAdd} className="flex items-center gap-2">
        <input
          value={newItem}
          onChange={(e) => setNewItem(e.target.value)}
          placeholder="Pasaporte, cargador…"
          className="h-9 flex-1 rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 text-sm text-gray-700 dark:text-slate-200 focus:border-brand-travel focus:outline-none focus:ring-1 focus:ring-brand-travel"
        />
        <button
          type="submit"
          disabled={adding || !newItem.trim()}
          className="h-9 rounded-lg bg-brand-travel px-3 text-sm font-medium text-white transition-colors hover:opacity-90 disabled:opacity-50"
        >
          Agregar
        </button>
      </form>
    </div>
  );
}
