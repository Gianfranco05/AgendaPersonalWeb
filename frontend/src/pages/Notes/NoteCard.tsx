import { Pin, Trash2 } from 'lucide-react';
import type { Note } from '../../types';
import { parseServerTimestamp } from '../../utils/date';

interface NoteCardProps {
  note: Note;
  isSelected: boolean;
  onSelect: () => void;
  onPin: () => void;
  onDelete: () => void;
}

export default function NoteCard({ note, isSelected, onSelect, onPin, onDelete }: NoteCardProps) {
  const preview = note.content
    .replace(/[#*`>\[\]()]/g, '')
    .replace(/\n/g, ' ')
    .substring(0, 100);

  return (
    <button
      onClick={onSelect}
      className={`group relative w-full rounded-lg p-3 text-left transition-colors ${
        isSelected
          ? 'bg-brand-surface-container ring-1 ring-brand-indigo/30'
          : 'hover:bg-gray-50 dark:hover:bg-slate-700/50'
      }`}
      style={{
        borderLeft: `3px solid ${note.is_pinned ? '#6366f1' : note.color}`,
      }}
    >
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            {note.is_pinned && <Pin size={12} className="flex-shrink-0 text-brand-indigo" />}
            <span className={`truncate text-sm ${note.is_pinned ? 'font-semibold' : 'font-medium'} text-gray-700 dark:text-slate-200`}>
              {note.title || 'Sin título'}
            </span>
          </div>
          {preview && (
            <p className="mt-0.5 text-xs leading-snug text-gray-400 dark:text-slate-500 line-clamp-2">
              {preview}
            </p>
          )}
          <div className="mt-1.5 flex items-center gap-2">
            <span className="text-xs text-gray-400 dark:text-slate-500">
              {parseServerTimestamp(note.updated_at).toLocaleDateString('es-AR')}
            </span>
            {note.tags.length > 0 && (
              <div className="flex gap-1">
                {note.tags.slice(0, 2).map((tag) => (
                  <span
                    key={tag.id}
                    className="rounded-full px-1.5 py-0.5 text-xs font-medium"
                    style={{
                      backgroundColor: `${tag.color}20`,
                      color: tag.color,
                    }}
                  >
                    {tag.name}
                  </span>
                ))}
                {note.tags.length > 2 && (
                  <span className="text-xs text-gray-400 dark:text-slate-500">+{note.tags.length - 2}</span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Actions (show on hover) */}
      <div className="absolute right-2 top-2 flex gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
        <button
          onClick={(e) => { e.stopPropagation(); onPin(); }}
          className="rounded p-1 text-gray-400 dark:text-slate-500 hover:bg-gray-200 dark:hover:bg-slate-600 hover:text-brand-indigo"
          title={note.is_pinned ? 'Desfijar' : 'Fijar'}
        >
          <Pin size={12} />
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onDelete(); }}
          className="rounded p-1 text-gray-400 dark:text-slate-500 hover:bg-rose-100 hover:text-rose-500"
          title="Eliminar"
        >
          <Trash2 size={12} />
        </button>
      </div>
    </button>
  );
}
