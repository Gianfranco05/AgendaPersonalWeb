import { useState } from 'react';
import { DragDropContext, type DropResult } from '@hello-pangea/dnd';
import { useKanban } from '../../hooks/useKanban';
import KanbanColumn from './KanbanColumn';
import AddTaskForm from './AddTaskForm';
import type { TaskStatus } from '../../types';

export default function KanbanBoard() {
  const [selectedArea, setSelectedArea] = useState('Todas');
  const { columns, areas, addTask, updateTask, deleteTask, moveTask } = useKanban(selectedArea);

  function handleDragEnd(result: DropResult) {
    const { draggableId, destination, source } = result;

    if (!destination) return;
    if (
      destination.droppableId === source.droppableId &&
      destination.index === source.index
    ) {
      return;
    }

    moveTask(
      draggableId,
      destination.droppableId as TaskStatus,
      destination.index
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-800 dark:text-slate-100">Tareas</h2>
        <AddTaskForm onAdd={addTask} areas={areas} />
      </div>

      {areas.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {['Todas', ...areas].map((area) => (
            <button
              key={area}
              onClick={() => setSelectedArea(area)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                selectedArea === area
                  ? 'bg-brand-charcoal text-white'
                  : 'bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-slate-300 hover:bg-gray-200 dark:hover:bg-slate-700'
              }`}
            >
              {area}
            </button>
          ))}
        </div>
      )}

      <DragDropContext onDragEnd={handleDragEnd}>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {columns.map((column) => (
            <KanbanColumn
              key={column.id}
              column={column}
              onUpdate={updateTask}
              onDelete={deleteTask}
            />
          ))}
        </div>
      </DragDropContext>
    </div>
  );
}
