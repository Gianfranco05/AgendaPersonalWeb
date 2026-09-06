import { useState } from 'react';
import { Trash2, ArrowRight } from 'lucide-react';
import { useProjectTasks, addTask, editTask, removeTask } from '../../hooks/useProjects';
import type { ProjectTask, ProjectTaskStatus } from '../../types';

interface Props {
  projectId: string;
}

const COLUMNS: { key: ProjectTaskStatus; label: string }[] = [
  { key: 'pendiente', label: 'Pendiente' },
  { key: 'en_progreso', label: 'En progreso' },
  { key: 'hecho', label: 'Hecho' },
];

function nextStatus(status: ProjectTaskStatus): ProjectTaskStatus | null {
  const idx = COLUMNS.findIndex((c) => c.key === status);
  return idx < COLUMNS.length - 1 ? COLUMNS[idx + 1].key : null;
}

export default function TaskBoard({ projectId }: Props) {
  const { data: tasks, isLoading } = useProjectTasks(projectId);
  const [newTitle, setNewTitle] = useState('');
  const [adding, setAdding] = useState(false);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!newTitle.trim()) return;
    setAdding(true);
    try {
      await addTask({ project_id: projectId, title: newTitle.trim() });
      setNewTitle('');
    } finally {
      setAdding(false);
    }
  }

  async function handleAdvance(task: ProjectTask) {
    const next = nextStatus(task.status);
    if (!next) return;
    await editTask(task.id, projectId, { status: next });
  }

  async function handleDelete(task: ProjectTask) {
    if (!confirm(`¿Borrar "${task.title}"?`)) return;
    await removeTask(task.id, projectId);
  }

  return (
    <div className="mt-3 rounded-lg bg-gray-50 dark:bg-slate-900/40 p-4">
      <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-slate-400">
        Tareas del proyecto
      </h4>

      {isLoading ? (
        <p className="text-xs text-gray-500 dark:text-slate-400">Cargando…</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {COLUMNS.map((col) => {
            const items = (tasks ?? []).filter((t) => t.status === col.key);
            return (
              <div key={col.key}>
                <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-slate-400">
                  {col.label} ({items.length})
                </p>
                {items.length === 0 ? (
                  <p className="text-xs text-gray-400 dark:text-slate-500">—</p>
                ) : (
                  <ul className="space-y-1.5">
                    {items.map((task) => {
                      const next = nextStatus(task.status);
                      return (
                        <li
                          key={task.id}
                          className="flex items-center justify-between gap-2 rounded-lg bg-white dark:bg-slate-800 px-3 py-2 shadow-sm"
                        >
                          <span className="min-w-0 flex-1 truncate text-sm text-gray-700 dark:text-slate-200">
                            {task.title}
                          </span>
                          <div className="flex shrink-0 items-center gap-1">
                            {next ? (
                              <button
                                onClick={() => handleAdvance(task)}
                                className="rounded-lg p-1 text-brand-projects transition-colors hover:bg-rose-50 dark:hover:bg-rose-950"
                                title={`Mover a "${COLUMNS.find((c) => c.key === next)?.label}"`}
                              >
                                <ArrowRight size={14} />
                              </button>
                            ) : null}
                            <button
                              onClick={() => handleDelete(task)}
                              className="rounded-lg p-1 text-gray-400 dark:text-slate-500 transition-colors hover:bg-rose-50 hover:text-rose-500"
                              title="Borrar tarea"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            );
          })}
        </div>
      )}

      <form onSubmit={handleAdd} className="mt-3 flex items-center gap-2">
        <input
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          placeholder="Nueva tarea…"
          className="h-9 flex-1 rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 text-sm text-gray-700 dark:text-slate-200 focus:border-brand-projects focus:outline-none focus:ring-1 focus:ring-brand-projects"
        />
        <button
          type="submit"
          disabled={adding || !newTitle.trim()}
          className="h-9 rounded-lg bg-brand-projects px-3 text-sm font-medium text-white transition-colors hover:opacity-90 disabled:opacity-50"
        >
          Agregar
        </button>
      </form>
    </div>
  );
}
