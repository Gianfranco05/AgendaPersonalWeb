import { Droppable } from '@hello-pangea/dnd';
import type { KanbanColumn as KanbanColumnType, Task } from '../../types';
import TaskCard from './TaskCard';

interface KanbanColumnProps {
  column: KanbanColumnType;
  onUpdate: (id: string, updates: Partial<Pick<Task, 'title' | 'description'>>) => void;
  onDelete: (id: string) => void;
}

const columnStyles: Record<string, { bg: string; border: string; headerBg: string; text: string }> = {
  pending: {
    bg: 'bg-amber-50/50',
    border: 'border-amber-200',
    headerBg: 'bg-amber-100',
    text: 'text-amber-800',
  },
  in_progress: {
    bg: 'bg-blue-50/50',
    border: 'border-blue-200',
    headerBg: 'bg-blue-100',
    text: 'text-blue-800',
  },
  completed: {
    bg: 'bg-emerald-50/50',
    border: 'border-emerald-200',
    headerBg: 'bg-emerald-100',
    text: 'text-emerald-800',
  },
};

export default function KanbanColumn({ column, onUpdate, onDelete }: KanbanColumnProps) {
  const style = columnStyles[column.id] || columnStyles.pending;

  return (
    <div className={`flex flex-col rounded-xl border ${style.border} ${style.bg}`}>
      {/* Header */}
      <div className={`rounded-t-xl ${style.headerBg} px-4 py-3`}>
        <div className="flex items-center justify-between">
          <h3 className={`text-sm font-semibold ${style.text}`}>{column.title}</h3>
          <span className={`inline-flex h-6 min-w-[24px] items-center justify-center rounded-full bg-white/50 px-2 text-xs font-bold ${style.text}`}>
            {column.tasks.length}
          </span>
        </div>
      </div>

      {/* Droppable area */}
      <Droppable droppableId={column.id}>
        {(provided, snapshot) => (
          <div
            ref={provided.innerRef}
            {...provided.droppableProps}
            className={`flex-1 space-y-2 p-3 transition-colors ${
              snapshot.isDraggingOver ? 'bg-gray-100/50' : ''
            }`}
            style={{ minHeight: '200px' }}
          >
            {column.tasks.map((task, index) => (
              <TaskCard
                key={task.id}
                task={task}
                index={index}
                onUpdate={onUpdate}
                onDelete={onDelete}
              />
            ))}
            {provided.placeholder}

            {column.tasks.length === 0 && (
              <div className="flex h-24 items-center justify-center rounded-lg border-2 border-dashed border-gray-200">
                <span className="text-xs text-gray-400">Sin tareas</span>
              </div>
            )}
          </div>
        )}
      </Droppable>
    </div>
  );
}
