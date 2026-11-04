import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Search, X } from 'lucide-react';
import { useSearch } from '../../hooks/useSearch';
import { isSearchable } from '../../utils/search';
import type { SearchGroup, SearchItem, SearchType } from '../../types';
import SearchResultItem, { SEARCH_ICONS } from './SearchResultItem';

interface Props {
  open: boolean;
  onClose: () => void;
}

type Entry =
  | { kind: 'item'; item: SearchItem }
  | { kind: 'more'; group: SearchGroup };

const FOCUSABLE = 'button:not([disabled]), input:not([disabled]), [href], [tabindex]:not([tabindex="-1"])';

function errorMessage(error: unknown): string {
  const status = (error as { response?: { status?: number } } | undefined)?.response?.status;
  if (status === 429) return 'Estás buscando muy rápido, esperá un momento';
  return 'No pudimos buscar. Probá de nuevo.';
}

export default function SearchPalette({ open, onClose }: Props) {
  const navigate = useNavigate();
  const uid = useId();
  const listId = `${uid}-list`;
  const optionId = (i: number) => `${uid}-opt-${i}`;
  const [query, setQuery] = useState('');
  const [expanded, setExpanded] = useState<SearchType | null>(null);
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);

  const { data, error, isLoading, enabled } = useSearch(
    query,
    expanded ? { types: [expanded], limit: 20 } : {},
  );

  // Foco al abrir y, al cerrar, de vuelta al elemento que lo tenía.
  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    inputRef.current?.focus();
    return () => {
      setQuery('');
      setExpanded(null);
      setActive(0);
      previous?.focus?.();
    };
  }, [open]);

  const entries = useMemo<Entry[]>(() => {
    const out: Entry[] = [];
    for (const group of data?.groups ?? []) {
      for (const item of group.items) out.push({ kind: 'item', item });
      if (group.has_more && !expanded) out.push({ kind: 'more', group });
    }
    return out;
  }, [data, expanded]);

  useEffect(() => setActive(0), [data, expanded]);

  useEffect(() => {
    document.getElementById(optionId(active))?.scrollIntoView?.({ block: 'nearest' });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  if (!open) return null;

  function select(entry: Entry) {
    if (entry.kind === 'more') {
      setExpanded(entry.group.type);
      return;
    }
    navigate(entry.item.path);
    onClose();
  }

  function onKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    } else if (e.key === 'ArrowDown' && entries.length > 0) {
      e.preventDefault();
      setActive((i) => (i + 1) % entries.length);
    } else if (e.key === 'ArrowUp' && entries.length > 0) {
      e.preventDefault();
      setActive((i) => (i - 1 + entries.length) % entries.length);
    } else if (e.key === 'Enter' && entries[active]) {
      e.preventDefault();
      select(entries[active]);
    } else if (e.key === 'Tab') {
      const nodes = dialogRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE);
      if (!nodes || nodes.length === 0) return;
      const first = nodes[0];
      const last = nodes[nodes.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  }

  const searchable = isSearchable(query);
  const hasResults = entries.length > 0;
  let flatIndex = 0;
  let status: string | null = null;
  if (!searchable) status = 'Escribí al menos 2 letras';
  else if (error) status = errorMessage(error);
  else if (enabled && data && !hasResults) status = `No encontramos nada para «${data.query}»`;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-start justify-center bg-black/50 p-4 pt-[10vh]"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="Buscar"
        onKeyDown={onKeyDown}
        className="flex max-h-[75vh] w-full max-w-xl flex-col overflow-hidden rounded-xl bg-white shadow-2xl dark:bg-slate-800"
      >
        <div className="flex items-center gap-2 border-b border-gray-200 px-4 dark:border-slate-700">
          <Search size={18} className="shrink-0 text-gray-400" aria-hidden="true" />
          <input
            ref={inputRef}
            type="text"
            role="combobox"
            aria-expanded={hasResults}
            aria-controls={listId}
            aria-activedescendant={hasResults ? optionId(active) : undefined}
            aria-autocomplete="list"
            aria-label="Buscar en todo"
            autoComplete="off"
            maxLength={120}
            placeholder="Buscar notas, tareas, movimientos…"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setExpanded(null);
            }}
            className="h-12 flex-1 bg-transparent text-sm text-gray-900 outline-none placeholder:text-gray-400 dark:text-slate-100"
          />
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-700"
            aria-label="Cerrar búsqueda"
          >
            <X size={16} />
          </button>
        </div>

        <div className="overflow-y-auto p-2">
          {expanded && (
            <button
              type="button"
              onClick={() => setExpanded(null)}
              className="mb-1 flex items-center gap-1 px-3 py-1 text-xs font-medium text-brand-indigo hover:underline"
            >
              <ArrowLeft size={12} aria-hidden="true" /> Todos los resultados
            </button>
          )}
          {status && (
            <p className="px-3 py-6 text-center text-sm text-gray-500 dark:text-slate-400" role="status">
              {status}
            </p>
          )}
          {searchable && isLoading && !hasResults && !error && (
            <p className="px-3 py-6 text-center text-sm text-gray-500 dark:text-slate-400" role="status">
              Buscando…
            </p>
          )}
          <div
            id={listId}
            role="listbox"
            aria-label="Resultados"
            className={searchable && hasResults ? '' : 'hidden'}
          >
            {data?.groups.map((group) => {
              const Icon = SEARCH_ICONS[group.type];
              return (
                <div key={group.type} role="presentation">
                  <div
                    role="presentation"
                    className="flex items-center gap-1.5 px-3 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-slate-400"
                  >
                    <Icon size={12} aria-hidden="true" />
                    {group.label}
                  </div>
                  {group.items.map((item) => {
                    const i = flatIndex++;
                    return (
                      <SearchResultItem
                        key={`${item.entity}-${item.id}`}
                        item={item}
                        id={optionId(i)}
                        active={i === active}
                        onHover={() => setActive(i)}
                        onSelect={() => select({ kind: 'item', item })}
                      />
                    );
                  })}
                  {group.has_more && !expanded && (() => {
                    const i = flatIndex++;
                    return (
                      <div
                        id={optionId(i)}
                        role="option"
                        aria-selected={i === active}
                        aria-label={`Ver más en ${group.label}`}
                        onMouseMove={() => setActive(i)}
                        onClick={() => select({ kind: 'more', group })}
                        className={`cursor-pointer rounded-lg px-3 py-1.5 text-xs font-medium text-brand-indigo ${
                          i === active ? 'bg-brand-indigo/10' : ''
                        }`}
                      >
                        Ver más en {group.label}
                      </div>
                    );
                  })()}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
