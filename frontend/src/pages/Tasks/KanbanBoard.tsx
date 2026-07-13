import { DragDropContext, type DropResult } from '@hello-pangea/dnd';
import { useKanban } from '../../hooks/useKanban';
import KanbanColumn from './KanbanColumn';
import AddTaskForm from './AddTaskForm';
import type { TaskStatus } from '../../types';

export default function KanbanBoard() {
  const { columns, addTask, updateTask, deleteTask, moveTask } = useKanban();

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
        <AddTaskForm onAdd={addTask} />
      </div>

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
