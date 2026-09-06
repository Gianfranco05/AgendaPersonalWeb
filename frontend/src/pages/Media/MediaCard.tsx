import { Pencil, Trash2, Film, Tv } from 'lucide-react';
import type { MediaItem, MediaStatus } from '../../types';

interface Props {
  item: MediaItem;
  onEdit: (item: MediaItem) => void;
  onDelete: (item: MediaItem) => void;
}

const STATUS_LABELS: Record<MediaStatus, string> = {
  pendiente: 'Pendiente',
  viendo: 'Viendo',
  visto: 'Visto',
};

const STATUS_CLASSES: Record<MediaStatus, string> = {
  pendiente: 'bg-gray-100 text-gray-500 dark:bg-slate-700 dark:text-slate-400',
  viendo: 'bg-indigo-100 text-indigo-600 dark:bg-indigo-950 dark:text-indigo-400',
  visto: 'bg-emerald-100 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-400',
};

function stars(rating: number | null): string {
  if (rating === null) return '';
  const full = Math.round(rating);
  return '★'.repeat(full) + '☆'.repeat(5 - full);
}

export default function MediaCard({ item, onEdit, onDelete }: Props) {
  const Icon = item.media_type === 'serie' ? Tv : Film;
  return (
    <div className="rounded-xl bg-white dark:bg-slate-800 p-4 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <Icon size={16} className="shrink-0 text-brand-media" />
          <h4 className="truncate font-medium text-gray-800 dark:text-slate-100">
            {item.title}
            {item.year ? ` (${item.year})` : ''}
          </h4>
        </div>
        <div className="flex shrink-0 gap-1">
          <button
            onClick={() => onEdit(item)}
            className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 transition-colors hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-brand-media"
            title="Editar"
          >
            <Pencil size={13} />
          </button>
          <button
            onClick={() => onDelete(item)}
            className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 transition-colors hover:bg-rose-50 hover:text-rose-500"
            title="Eliminar"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <span className={`rounded-full px-2 py-1 text-[11px] font-medium ${STATUS_CLASSES[item.status]}`}>
          {STATUS_LABELS[item.status]}
        </span>
        {item.rating != null && <span className="text-xs text-amber-500">{stars(item.rating)}</span>}
      </div>
    </div>
  );
}
