import { useState, useRef, useEffect } from 'react';
import { Draggable } from '@hello-pangea/dnd';
import { Pencil, Trash2, Check, X } from 'lucide-react';
import type { Task } from '../../types';

interface TaskCardProps {
  task: Task;
  index: number;
  onUpdate: (id: string, updates: Partial<Pick<Task, 'title' | 'description'>>) => void;
  onDelete: (id: string) => void;
}

export default function TaskCard({ task, index, onUpdate, onDelete }: TaskCardProps) {
  const [editingTitle, setEditingTitle] = useState(false);
  const [editingDesc, setEditingDesc] = useState(false);
  const [titleDraft, setTitleDraft] = useState(task.title);
  const [descDraft, setDescDraft] = useState(task.description);
  const titleRef = useRef<HTMLInputElement>(null);
  const descRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (editingTitle) titleRef.current?.focus();
  }, [editingTitle]);

  useEffect(() => {
    if (editingDesc) descRef.current?.focus();
  }, [editingDesc]);

  function handleDelete() {
    if (window.confirm('¿Eliminar esta tarea?')) {
      onDelete(task.id);
    }
  }

  function saveTitle() {
    if (titleDraft.trim()) {
      onUpdate(task.id, { title: titleDraft.trim() });
    } else {
      setTitleDraft(task.title);
    }
    setEditingTitle(false);
  }

  function saveDesc() {
    onUpdate(task.id, { description: descDraft });
    setEditingDesc(false);
  }

  return (
    <Draggable draggableId={task.id} index={index}>
      {(provided, snapshot) => (
        <div
          ref={provided.innerRef}
          {...provided.draggableProps}
          {...provided.dragHandleProps}
          className={`group rounded-lg border border-gray-200 bg-white p-3 shadow-sm transition-shadow ${
            snapshot.isDragging ? 'shadow-lg ring-1 ring-[#7C3AED]/30' : 'hover:shadow-md'
          }`}
        >
          {/* Title */}
          <div className="flex items-start gap-2">
            {editingTitle ? (
              <div className="flex flex-1 items-center gap-1">
                <input
                  ref={titleRef}
                  value={titleDraft}
                  onChange={(e) => setTitleDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') saveTitle();
                    if (e.key === 'Escape') {
                      setTitleDraft(task.title);
                      setEditingTitle(false);
                    }
                  }}
                  className="flex-1 rounded border border-[#7C3AED] px-2 py-0.5 text-sm outline-none"
                />
                <button onClick={saveTitle} className="rounded p-0.5 text-emerald-500 hover:bg-emerald-50">
                  <Check size={14} />
                </button>
                <button onClick={() => { setTitleDraft(task.title); setEditingTitle(false); }} className="rounded p-0.5 text-gray-400 hover:bg-gray-100">
                  <X size={14} />
                </button>
              </div>
            ) : (
              <span
                onClick={() => { setTitleDraft(task.title); setEditingTitle(true); }}
                className="flex-1 cursor-text text-sm font-medium text-gray-700"
              >
                {task.title}
              </span>
            )}

            <div className="flex gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
              {!editingTitle && (
                <button
                  onClick={() => { setTitleDraft(task.title); setEditingTitle(true); }}
                  className="rounded p-0.5 text-gray-400 hover:bg-gray-100 hover:text-[#7C3AED]"
                  title="Editar título"
                >
                  <Pencil size={12} />
                </button>
              )}
              <button
                onClick={handleDelete}
                className="rounded p-0.5 text-gray-400 hover:bg-rose-50 hover:text-rose-500"
                title="Eliminar"
              >
                <Trash2 size={12} />
              </button>
            </div>
          </div>

          {/* Description */}
          {editingDesc ? (
            <div className="mt-2">
              <textarea
                ref={descRef}
                value={descDraft}
                onChange={(e) => setDescDraft(e.target.value)}
                className="w-full resize-none rounded border border-[#7C3AED] px-2 py-1 text-xs outline-none"
                rows={3}
              />
              <div className="mt-1 flex justify-end gap-1">
                <button onClick={saveDesc} className="rounded px-2 py-0.5 text-xs font-medium text-emerald-600 hover:bg-emerald-50">
                  Guardar
                </button>
                <button onClick={() => { setDescDraft(task.description); setEditingDesc(false); }} className="rounded px-2 py-0.5 text-xs text-gray-500 hover:bg-gray-100">
                  Cancelar
                </button>
              </div>
            </div>
          ) : task.description ? (
            <p
              onClick={() => { setDescDraft(task.description); setEditingDesc(true); }}
              className="mt-1.5 cursor-text text-xs leading-relaxed text-gray-500"
            >
              {task.description}
            </p>
          ) : (
            <button
              onClick={() => { setDescDraft(''); setEditingDesc(true); }}
              className="mt-1.5 text-xs text-gray-400 hover:text-[#7C3AED]"
            >
              + Agregar descripción
            </button>
          )}
        </div>
      )}
    </Draggable>
  );
}
