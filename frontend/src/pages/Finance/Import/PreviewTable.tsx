import { useMemo, useState } from 'react';
import { useCategories } from '../../../hooks/useFinance';
import { formatCents, toCents } from '../../../utils/financeTransfer';
import type { ImportRowStatus, ParsedImportRow } from '../../../types';

const PAGE_SIZE = 100;
const IMPORTABLE = new Set<ImportRowStatus>(['ok', 'possible_duplicate']);

const STATUS_CHIP: Record<ImportRowStatus, { label: string; cls: string }> = {
  ok: { label: 'OK', cls: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300' },
  error: { label: 'Error', cls: 'bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300' },
  duplicate: { label: 'Ya importado', cls: 'bg-gray-200 text-gray-700 dark:bg-slate-600 dark:text-slate-200' },
  possible_duplicate: { label: 'Posible duplicado', cls: 'bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-200' },
  skipped: { label: 'Omitida', cls: 'bg-gray-100 text-gray-500 dark:bg-slate-700 dark:text-slate-400' },
};

const SOURCE_LABEL = { history: 'según tu historial', rule: 'por palabra clave', none: '' } as const;

interface Props {
  rows: ParsedImportRow[];
  selected: Set<number>;
  categories: Record<number, string>;
  types: Record<number, 'income' | 'expense'>;
  onSelectedChange: (next: Set<number>) => void;
  onCategoryChange: (index: number, categoryId: string) => void;
  onTypeChange: (index: number, type: 'income' | 'expense') => void;
}

export default function PreviewTable({
  rows,
  selected,
  categories,
  types,
  onSelectedChange,
  onCategoryChange,
  onTypeChange,
}: Props) {
  const { data: cats = [] } = useCategories();
  const [filter, setFilter] = useState<'all' | ImportRowStatus>('all');
  const [page, setPage] = useState(0);

  const visible = useMemo(
    () => (filter === 'all' ? rows : rows.filter((r) => r.status === filter)),
    [rows, filter],
  );
  const pages = Math.max(1, Math.ceil(visible.length / PAGE_SIZE));
  const current = Math.min(page, pages - 1);
  const slice = visible.slice(current * PAGE_SIZE, (current + 1) * PAGE_SIZE);
  const importable = visible.filter((r) => IMPORTABLE.has(r.status));
  const allTicked = importable.length > 0 && importable.every((r) => selected.has(r.index));

  function toggle(index: number) {
    const next = new Set(selected);
    if (next.has(index)) next.delete(index);
    else next.add(index);
    onSelectedChange(next);
  }

  function toggleAll() {
    const next = new Set(selected);
    for (const r of importable) {
      if (allTicked) next.delete(r.index);
      else next.add(r.index);
    }
    onSelectedChange(next);
  }

  const statuses = (['all', 'ok', 'possible_duplicate', 'duplicate', 'error', 'skipped'] as const).filter(
    (s) => s === 'all' || rows.some((r) => r.status === s),
  );

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filtrar por estado">
        {statuses.map((s) => (
          <button
            key={s}
            type="button"
            aria-pressed={filter === s}
            onClick={() => {
              setFilter(s);
              setPage(0);
            }}
            className={`rounded-full px-3 py-1 text-xs font-medium ${
              filter === s
                ? 'bg-brand-charcoal text-white'
                : 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-300'
            }`}
          >
            {s === 'all' ? `Todas (${rows.length})` : `${STATUS_CHIP[s].label} (${rows.filter((r) => r.status === s).length})`}
          </button>
        ))}
      </div>

      <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-slate-700">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 dark:bg-slate-900/40 text-left text-xs text-gray-500 dark:text-slate-400">
            <tr>
              <th className="px-3 py-2">
                <input type="checkbox" aria-label="Seleccionar todas" checked={allTicked} onChange={toggleAll} />
              </th>
              <th className="px-3 py-2">Fecha</th>
              <th className="px-3 py-2">Descripción</th>
              <th className="px-3 py-2">Tipo</th>
              <th className="px-3 py-2 text-right">Monto</th>
              <th className="px-3 py-2">Categoría</th>
              <th className="px-3 py-2">Estado</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
            {slice.map((r) => {
              const can = IMPORTABLE.has(r.status);
              const type = types[r.index] ?? r.type;
              const category = r.index in categories ? categories[r.index] : (r.suggested_category_id ?? '');
              const chip = STATUS_CHIP[r.status];
              return (
                <tr key={r.index} data-testid={`row-${r.index}`} className={can ? '' : 'opacity-70'}>
                  <td className="px-3 py-2">
                    <input
                      type="checkbox"
                      aria-label={`Importar fila ${r.source_line}`}
                      disabled={!can}
                      checked={selected.has(r.index)}
                      onChange={() => toggle(r.index)}
                    />
                  </td>
                  <td className="whitespace-nowrap px-3 py-2">{r.date ? r.date.split('-').reverse().join('/') : '—'}</td>
                  <td className="max-w-[16rem] truncate px-3 py-2" title={r.description}>{r.description}</td>
                  <td className="px-3 py-2">
                    {can && type ? (
                      <select
                        aria-label={`Tipo de la fila ${r.source_line}`}
                        className="rounded border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-1 py-0.5 text-xs"
                        value={type}
                        onChange={(e) => onTypeChange(r.index, e.target.value as 'income' | 'expense')}
                      >
                        <option value="income">Ingreso</option>
                        <option value="expense">Egreso</option>
                      </select>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td className={`whitespace-nowrap px-3 py-2 text-right font-medium ${type === 'income' ? 'text-emerald-600' : 'text-rose-600'}`}>
                    {r.amount !== null ? formatCents(toCents(r.amount) * (type === 'expense' ? -1 : 1), r.currency ?? 'ARS') : '—'}
                  </td>
                  <td className="px-3 py-2">
                    {can ? (
                      <div>
                        <select
                          aria-label={`Categoría de la fila ${r.source_line}`}
                          className="max-w-[10rem] rounded border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-1 py-0.5 text-xs"
                          value={category}
                          onChange={(e) => onCategoryChange(r.index, e.target.value)}
                        >
                          <option value="">Sin categoría</option>
                          {cats.map((c) => (
                            <option key={c.id} value={c.id}>{c.name}</option>
                          ))}
                        </select>
                        {!(r.index in categories) && r.suggested_category_id && (
                          <span className="ml-1 text-[10px] text-gray-400">{SOURCE_LABEL[r.suggestion_source]}</span>
                        )}
                      </div>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td className="px-3 py-2">
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${chip.cls}`}
                      title={
                        r.duplicate_of
                          ? `${r.duplicate_of.description} (${r.duplicate_of.date.split('-').reverse().join('/')})`
                          : r.errors.join(' ')
                      }
                    >
                      {chip.label}
                    </span>
                    {r.errors.length > 0 && r.status === 'error' && (
                      <p className="mt-0.5 text-xs text-red-500">{r.errors[0]}</p>
                    )}
                  </td>
                </tr>
              );
            })}
            {slice.length === 0 && (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-center text-gray-400">No hay filas con este estado.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {pages > 1 && (
        <div className="flex items-center justify-between text-sm text-gray-500 dark:text-slate-400">
          <span>Página {current + 1} de {pages}</span>
          <div className="flex gap-2">
            <button type="button" disabled={current === 0} onClick={() => setPage(current - 1)} className="rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-1 disabled:opacity-40">
              Anterior
            </button>
            <button type="button" disabled={current >= pages - 1} onClick={() => setPage(current + 1)} className="rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-1 disabled:opacity-40">
              Siguiente
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
