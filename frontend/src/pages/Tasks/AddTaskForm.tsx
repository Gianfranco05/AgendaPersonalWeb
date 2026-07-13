import { useState } from 'react';
import { Plus, X } from 'lucide-react';

interface AddTaskFormProps {
  onAdd: (title: string, description: string) => void;
}

export default function AddTaskForm({ onAdd }: AddTaskFormProps) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');

  function handleSubmit() {
    if (!title.trim()) return;
    onAdd(title.trim(), description.trim());
    setTitle('');
    setDescription('');
    setOpen(false);
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-charcoal-hover"
      >
        <Plus size={16} />
        Nueva tarea
      </button>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 px-4 py-8 sm:py-12">
      <div className="w-full max-w-md rounded-xl bg-white dark:bg-slate-800 shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-100 dark:border-slate-800 px-6 py-4">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">Nueva tarea</h3>
          <button onClick={() => setOpen(false)} className="rounded-lg p-1 text-gray-400 dark:text-slate-500 hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-gray-600 dark:hover:text-slate-200">
            <X size={20} />
          </button>
        </div>

        <div className="space-y-4 px-6 py-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Título</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleSubmit(); }}
              autoFocus
              className="w-full rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-2 text-sm focus:border-brand-indigo focus:outline-none focus:ring-1 focus:ring-brand-indigo"
              placeholder="¿Qué hay que hacer?"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Descripción (opcional)</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full resize-none rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-2 text-sm focus:border-brand-indigo focus:outline-none focus:ring-1 focus:ring-brand-indigo"
              placeholder="Detalles de la tarea..."
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button
              onClick={() => setOpen(false)}
              className="rounded-lg border border-gray-200 dark:border-slate-700 px-4 py-2 text-sm font-medium text-gray-600 dark:text-slate-300 transition-colors hover:bg-gray-50 dark:hover:bg-slate-700/50"
            >
              Cancelar
            </button>
            <button
              onClick={handleSubmit}
              disabled={!title.trim()}
              className="rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-charcoal-hover disabled:opacity-50"
            >
              Crear tarea
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
