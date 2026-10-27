import { useMemo, useState } from 'react';
import { Pencil, Repeat, Trash2 } from 'lucide-react';
import { useCategories } from '../../hooks/useFinance';
import type { Category, Transaction } from '../../types';

interface TransactionTableProps {
  transactions: Transaction[];
  onEdit: (tx: Transaction) => void;
  onDelete: (id: string) => void;
  /** Abre "Nueva recurrente" precargada con esta transacción. */
  onMakeRecurring?: (tx: Transaction) => void;
  /** Muestra los movimientos de la recurrencia que generó la transacción. */
  onViewRecurrence?: (recurrenceId: string) => void;
}

type SortKey = 'transaction_date' | 'product_name' | 'category' | 'amount' | 'type';

export default function TransactionTable({
  transactions,
  onEdit,
  onDelete,
  onMakeRecurring,
  onViewRecurrence,
}: TransactionTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('transaction_date');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const { data: categories } = useCategories();

  // La API devuelve solo category_id: el nombre y el color salen de acá.
  const categoryById = useMemo(() => {
    const map = new Map<string, Category>();
    (categories ?? []).forEach((c) => map.set(c.id, c));
    return map;
  }, [categories]);

  function sortValue(tx: Transaction, key: SortKey): string | number {
    if (key === 'category') {
      return tx.category_id ? categoryById.get(tx.category_id)?.name ?? '' : '';
    }
    return tx[key] ?? '';
  }

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  }

  const sorted = [...transactions].sort((a, b) => {
    const dir = sortDir === 'asc' ? 1 : -1;
    const va = sortValue(a, sortKey);
    const vb = sortValue(b, sortKey);
    if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * dir;
    return String(va).localeCompare(String(vb)) * dir;
  });

  const headers: { key: SortKey; label: string }[] = [
    { key: 'transaction_date', label: 'Fecha' },
    { key: 'product_name', label: 'Descripción' },
    { key: 'category', label: 'Categoría' },
    { key: 'amount', label: 'Monto' },
    { key: 'type', label: 'Tipo' },
  ];

  return (
    <div className="overflow-x-auto rounded-xl bg-white dark:bg-slate-800 shadow-sm">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100 dark:border-slate-800 bg-gray-50 dark:bg-slate-800/60">
            {headers.map(({ key, label }) => (
              <th
                key={key}
                onClick={() => handleSort(key)}
                className="cursor-pointer px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-slate-400 transition-colors hover:text-gray-700 dark:hover:text-slate-100"
              >
                <span className="flex items-center gap-1">
                  {label}
                  {sortKey === key && (
                    <span className="text-brand-indigo">{sortDir === 'asc' ? '↑' : '↓'}</span>
                  )}
                </span>
              </th>
            ))}
            <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-slate-400">
              Acciones
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.length === 0 ? (
            <tr>
              <td colSpan={6} className="px-4 py-12 text-center text-gray-400 dark:text-slate-500">
                No se encontraron transacciones
              </td>
            </tr>
          ) : (
            sorted.map((tx) => {
              const category = tx.category_id ? categoryById.get(tx.category_id) : undefined;
              return (
              <tr
                key={tx.id}
                className="border-b border-gray-50 transition-colors hover:bg-gray-50 dark:hover:bg-slate-700/50"
              >
                <td className="px-4 py-3 text-gray-600 dark:text-slate-300">{tx.transaction_date}</td>
                <td className="max-w-[220px] px-4 py-3 font-medium text-gray-800 dark:text-slate-100">
                  <span className="block truncate">{tx.product_name}</span>
                  {tx.is_recurring &&
                    (tx.recurrence_id ? (
                      <button
                        type="button"
                        onClick={() => onViewRecurrence?.(tx.recurrence_id as string)}
                        title="Ver los movimientos de esta recurrencia"
                        className="mt-0.5 inline-flex items-center gap-1 rounded-full bg-sky-50 dark:bg-sky-500/15 px-2 py-0.5 text-xs font-medium text-sky-700 dark:text-sky-300 hover:underline"
                      >
                        <Repeat size={11} />
                        Recurrente
                      </button>
                    ) : (
                      <span
                        title="Generada por una recurrencia que ya se eliminó"
                        className="mt-0.5 inline-flex items-center gap-1 rounded-full bg-gray-100 dark:bg-slate-700 px-2 py-0.5 text-xs font-medium text-gray-500 dark:text-slate-300"
                      >
                        <Repeat size={11} />
                        Recurrencia eliminada
                      </span>
                    ))}
                </td>
                <td className="px-4 py-3">
                  <span className="inline-flex items-center gap-1.5">
                    {category?.color && (
                      <span
                        className="inline-block h-2 w-2 rounded-full"
                        style={{ backgroundColor: category.color }}
                      />
                    )}
                    <span className="text-gray-600 dark:text-slate-300">{category?.name ?? '-'}</span>
                  </span>
                </td>
                <td className={`px-4 py-3 font-semibold ${tx.type === 'income' ? 'text-emerald-500' : 'text-rose-500'}`}>
                  {tx.type === 'income' ? '+' : '-'}${tx.amount.toLocaleString('es-AR')}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                      tx.type === 'income'
                        ? 'bg-emerald-50 text-emerald-700'
                        : 'bg-rose-50 text-rose-700'
                    }`}
                  >
                    {tx.type === 'income' ? 'Ingreso' : 'Egreso'}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex justify-end gap-1">
                    {onMakeRecurring && !tx.is_recurring && (
                      <button
                        onClick={() => onMakeRecurring(tx)}
                        className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 transition-colors hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-brand-indigo"
                        title="Hacer recurrente"
                        aria-label={`Hacer recurrente ${tx.product_name}`}
                      >
                        <Repeat size={14} />
                      </button>
                    )}
                    <button
                      onClick={() => onEdit(tx)}
                      className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 transition-colors hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-brand-indigo"
                      title="Editar"
                    >
                      <Pencil size={14} />
                    </button>
                    <button
                      onClick={() => onDelete(tx.id)}
                      className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 transition-colors hover:bg-rose-50 hover:text-rose-500"
                      title="Eliminar"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </td>
              </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
