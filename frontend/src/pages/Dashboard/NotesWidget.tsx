import { useEffect, useState } from 'react';
import { Pin, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import { fetchNotes } from '../../api/endpoints';
import type { Note } from '../../types';

export default function NotesWidget() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      const data = await fetchNotes();
      if (!cancelled) {
        const sorted = [...data]
          .sort((a, b) => {
            if (a.is_pinned !== b.is_pinned) return a.is_pinned ? -1 : 1;
            return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
          })
          .slice(0, 5);
        setNotes(sorted);
        setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return <LoadingSkeleton type="widget" />;
  }

  return (
    <div className="card-interactive rounded-xl bg-white dark:bg-slate-800 p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">Notas recientes</h3>
        <Link
          to="/notes"
          className="flex items-center gap-1 text-xs font-medium text-brand-indigo hover:underline"
        >
          Ver todas <ArrowRight size={14} />
        </Link>
      </div>

      {notes.length === 0 ? (
        <p className="text-sm text-gray-400 dark:text-slate-500">No hay notas aún</p>
      ) : (
        <ul className="space-y-2">
          {notes.map((note) => (
            <li
              key={note.id}
              className="flex items-center gap-3 rounded-lg border border-gray-100 dark:border-slate-800 p-3 transition-colors hover:bg-gray-50 dark:hover:bg-slate-700/50"
            >
              <div
                className="h-3 w-3 flex-shrink-0 rounded-full"
                style={{ backgroundColor: note.color }}
              />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  {note.is_pinned && <Pin size={12} className="text-brand-indigo" />}
                  <span className="truncate text-sm font-medium text-gray-700 dark:text-slate-200">
                    {note.title || 'Sin título'}
                  </span>
                </div>
                <p className="truncate text-xs text-gray-400 dark:text-slate-500">
                  {note.content.replace(/[#*`]/g, '').substring(0, 100)}
                </p>
              </div>
              <span className="flex-shrink-0 text-xs text-gray-400 dark:text-slate-500">
                {new Date(note.updated_at).toLocaleDateString('es-AR')}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
