import { Pencil, Trash2 } from 'lucide-react';
import type { Book, BookStatus } from '../../types';

interface Props {
  book: Book;
  onEdit: (book: Book) => void;
  onDelete: (book: Book) => void;
}

const STATUS_LABELS: Record<BookStatus, string> = {
  pendiente: 'Pendiente',
  leyendo: 'Leyendo',
  leido: 'Leído',
};

const STATUS_CLASSES: Record<BookStatus, string> = {
  pendiente: 'bg-gray-100 text-gray-500 dark:bg-slate-700 dark:text-slate-400',
  leyendo: 'bg-indigo-100 text-indigo-600 dark:bg-indigo-950 dark:text-indigo-400',
  leido: 'bg-emerald-100 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-400',
};

function stars(rating: number | null): string {
  if (rating === null) return '';
  const full = Math.round(rating);
  return '★'.repeat(full) + '☆'.repeat(5 - full);
}

export default function BookCard({ book, onEdit, onDelete }: Props) {
  return (
    <div className="rounded-xl bg-white dark:bg-slate-800 p-4 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h4 className="truncate font-medium text-gray-800 dark:text-slate-100">{book.title}</h4>
          {book.author && <p className="truncate text-xs text-gray-500 dark:text-slate-400">{book.author}</p>}
        </div>
        <div className="flex shrink-0 gap-1">
          <button
            onClick={() => onEdit(book)}
            className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 transition-colors hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-brand-library"
            title="Editar"
          >
            <Pencil size={13} />
          </button>
          <button
            onClick={() => onDelete(book)}
            className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 transition-colors hover:bg-rose-50 hover:text-rose-500"
            title="Eliminar"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <span className={`rounded-full px-2 py-1 text-[11px] font-medium ${STATUS_CLASSES[book.status]}`}>
          {STATUS_LABELS[book.status]}
        </span>
        {book.rating != null && <span className="text-xs text-amber-500">{stars(book.rating)}</span>}
        {book.pages != null && (
          <span className="text-xs text-gray-500 dark:text-slate-400">{book.pages} pág.</span>
        )}
      </div>
    </div>
  );
}
