import { Search, Plus, X, Download } from 'lucide-react';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import type { Note, Tag } from '../../types';
import NoteCard from './NoteCard';
import TagFilter from './TagFilter';

interface NotesSidebarProps {
  notes: Note[];
  tags: Tag[];
  selectedId: string | null;
  search: string;
  activeTag: string | null;
  loading: boolean;
  exporting: boolean;
  /** En pantallas chicas lista y editor no entran juntos: se muestra uno u otro. */
  hiddenOnMobile?: boolean;
  onSelect: (id: string) => void;
  onSearchChange: (value: string) => void;
  onTagSelect: (tagId: string | null) => void;
  onPin: (id: string) => void;
  onDelete: (id: string) => void;
  onNew: () => void;
  onExport: () => void;
}

export default function NotesSidebar({
  notes,
  tags,
  selectedId,
  search,
  activeTag,
  loading,
  exporting,
  hiddenOnMobile = false,
  onSelect,
  onSearchChange,
  onTagSelect,
  onPin,
  onDelete,
  onNew,
  onExport,
}: NotesSidebarProps) {
  return (
    <div
      className={`${hiddenOnMobile ? 'hidden md:flex' : 'flex'} w-full flex-shrink-0 flex-col md:w-[300px] md:border-r border-gray-100 dark:border-slate-800`}
    >
      {/* Header */}
      <div className="border-b border-gray-100 dark:border-slate-800 p-4">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-800 dark:text-slate-100">Notas</h2>
          <div className="flex items-center gap-1">
            <button
              onClick={onExport}
              disabled={exporting}
              className="rounded-lg p-1.5 text-gray-500 dark:text-slate-400 transition-colors hover:bg-brand-surface-container disabled:opacity-50"
              title="Exportar notas"
            >
              <Download size={16} />
            </button>
            <button
              onClick={onNew}
              className="rounded-lg p-1.5 text-brand-charcoal dark:text-slate-100 transition-colors hover:bg-brand-surface-container"
              title="Nueva nota"
            >
              <Plus size={18} />
            </button>
          </div>
        </div>

        {/* Search */}
        <div className="relative">
          <Search
            size={14}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-slate-500"
          />
          <input
            type="text"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Buscar notas..."
            className="w-full rounded-lg border border-gray-200 dark:border-slate-700 py-2 pl-9 pr-8 text-xs focus:border-brand-indigo focus:outline-none focus:ring-1 focus:ring-brand-indigo"
          />
          {search && (
            <button
              onClick={() => onSearchChange('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-200"
            >
              <X size={14} />
            </button>
          )}
        </div>

        {/* Tag filters */}
        {tags.length > 0 && (
          <div className="mt-2">
            <TagFilter
              tags={tags}
              activeTag={activeTag}
              onSelect={onTagSelect}
            />
          </div>
        )}
      </div>

      {/* Note list */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="space-y-2 p-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <LoadingSkeleton key={i} type="card" />
            ))}
          </div>
        ) : notes.length === 0 ? (
          <div className="flex flex-col items-center gap-2 p-8 text-center">
            <p className="text-sm text-gray-400 dark:text-slate-500">
              {search || activeTag ? 'Sin resultados' : 'No hay notas aún'}
            </p>
            {!search && !activeTag && (
              <button
                onClick={onNew}
                className="text-xs font-medium text-brand-indigo hover:underline"
              >
                Crear la primera nota
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-0.5 p-2">
            {notes.map((note) => (
              <NoteCard
                key={note.id}
                note={note}
                isSelected={note.id === selectedId}
                onSelect={() => onSelect(note.id)}
                onPin={() => onPin(note.id)}
                onDelete={() => onDelete(note.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
