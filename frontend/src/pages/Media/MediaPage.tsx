import { useState } from 'react';
import { Plus, Eye, Clapperboard, CheckCircle2, Film } from 'lucide-react';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import ModuleLockedNotice, { isPaymentRequiredError } from '../../components/ModuleLockedNotice';
import { useMediaItems, useMediaSummary, removeMediaItem } from '../../hooks/useMedia';
import type { MediaItem, MediaStatus } from '../../types';
import MediaForm from './MediaForm';
import MediaCard from './MediaCard';

const FILTERS: { key: MediaStatus | 'all'; label: string }[] = [
  { key: 'all', label: 'Todos' },
  { key: 'pendiente', label: 'Pendientes' },
  { key: 'viendo', label: 'Viendo' },
  { key: 'visto', label: 'Vistos' },
];

export default function MediaPage() {
  const [filter, setFilter] = useState<MediaStatus | 'all'>('all');
  const [modal, setModal] = useState<{ open: boolean; item: MediaItem | null }>({ open: false, item: null });

  const { data: items, isLoading: itemsLoading, error: itemsError } = useMediaItems();
  const { data: summary, isLoading: summaryLoading } = useMediaSummary();

  if (isPaymentRequiredError(itemsError)) {
    return <ModuleLockedNotice moduleName="Películas y Series" />;
  }

  async function handleDelete(item: MediaItem) {
    if (!confirm(`¿Borrar "${item.title}"?`)) return;
    await removeMediaItem(item.id);
  }

  const filtered = (items ?? []).filter((i) => filter === 'all' || i.status === filter);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-800 dark:text-slate-100">Películas y Series</h2>
        <button
          onClick={() => setModal({ open: true, item: null })}
          className="flex items-center gap-2 rounded-lg bg-brand-media px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90"
        >
          <Plus size={16} />
          Nuevo
        </button>
      </div>

      {summaryLoading && !summary ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <LoadingSkeleton type="card" />
          <LoadingSkeleton type="card" />
          <LoadingSkeleton type="card" />
          <LoadingSkeleton type="card" />
        </div>
      ) : summary ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
              <Clapperboard size={16} className="text-gray-400" />
              Pendientes
            </div>
            <p className="mt-1 text-2xl font-bold text-gray-800 dark:text-slate-100">{summary.pendientes}</p>
          </div>
          <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
              <Eye size={16} className="text-brand-media" />
              Viendo
            </div>
            <p className="mt-1 text-2xl font-bold text-brand-media">{summary.viendo}</p>
          </div>
          <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
              <CheckCircle2 size={16} className="text-emerald-500" />
              Vistos
            </div>
            <p className="mt-1 text-2xl font-bold text-emerald-500">{summary.vistos}</p>
          </div>
          <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
              Puntaje prom.
            </div>
            <p className="mt-1 text-2xl font-bold text-amber-500">{summary.average_rating ?? '—'}</p>
          </div>
        </div>
      ) : null}

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
              filter === f.key
                ? 'bg-brand-charcoal text-white'
                : 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-300'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {itemsLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <LoadingSkeleton key={i} type="card" />
          ))}
        </div>
      ) : filtered.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((item) => (
            <MediaCard key={item.id} item={item} onEdit={(i) => setModal({ open: true, item: i })} onDelete={handleDelete} />
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl bg-white dark:bg-slate-800 p-12 shadow-sm">
          <Film size={48} className="text-gray-300 dark:text-slate-600" />
          <p className="text-sm text-gray-500 dark:text-slate-400">
            No hay nada{filter !== 'all' ? ` en "${FILTERS.find((f) => f.key === filter)?.label}"` : ''} todavía
          </p>
          <button
            onClick={() => setModal({ open: true, item: null })}
            className="flex items-center gap-2 rounded-lg bg-brand-media px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90"
          >
            <Plus size={16} />
            Agregar
          </button>
        </div>
      )}

      {modal.open && (
        <MediaForm
          item={modal.item}
          onClose={() => setModal({ open: false, item: null })}
          onSaved={() => setModal({ open: false, item: null })}
        />
      )}
    </div>
  );
}
