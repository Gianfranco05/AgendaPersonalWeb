import { mutate as globalMutate } from 'swr';
import { useApiSWR } from './useApiSWR';
import {
  fetchTasks,
  createTask,
  updateTask as apiUpdateTask,
  deleteTask as apiDeleteTask,
  moveTask as apiMoveTask,
} from '../api/endpoints';
import type { Task, TaskStatus, KanbanColumn, TaskPriority } from '../types';

const TASKS_KEY = 'kanban/tasks';

export interface NewTaskInput {
  title: string;
  description?: string;
  area?: string;
  priority?: TaskPriority;
  due_date?: string | null;
}

function groupByStatus(tasks: Task[]): KanbanColumn[] {
  return [
    { id: 'pending', title: 'Pendiente', tasks: tasks.filter((t) => t.status === 'pending').sort((a, b) => a.order - b.order) },
    { id: 'in_progress', title: 'En Proceso', tasks: tasks.filter((t) => t.status === 'in_progress').sort((a, b) => a.order - b.order) },
    { id: 'completed', title: 'Completado', tasks: tasks.filter((t) => t.status === 'completed').sort((a, b) => a.order - b.order) },
  ];
}

export async function addTask(data: NewTaskInput) {
  await createTask({
    title: data.title,
    description: data.description ?? '',
    area: data.area || 'General',
    priority: data.priority ?? 'media',
    due_date: data.due_date ?? null,
    status: 'pending',
    order: 0,
  });
  await globalMutate(TASKS_KEY);
}

export async function updateTask(
  id: string,
  updates: Partial<Pick<Task, 'title' | 'description' | 'priority' | 'due_date' | 'area'>>,
) {
  await apiUpdateTask(id, updates);
  await globalMutate(TASKS_KEY);
}

export async function deleteTask(id: string) {
  await apiDeleteTask(id);
  await globalMutate(TASKS_KEY);
}

export async function moveTask(taskId: string, newStatus: TaskStatus, newOrder: number) {
  await apiMoveTask(taskId, newStatus, newOrder);
  await globalMutate(TASKS_KEY);
}

/** area: si se pasa (y no es 'Todas'), filtra las columnas a esa área. */
export function useKanban(area?: string) {
  const { data, isLoading } = useApiSWR(TASKS_KEY, () => fetchTasks());
  const tasks = data ?? [];
  const areas = Array.from(new Set(tasks.map((t) => t.area))).sort();
  const filtered = area && area !== 'Todas' ? tasks.filter((t) => t.area === area) : tasks;

  return {
    tasks,
    areas,
    columns: groupByStatus(filtered),
    isLoading,
    addTask,
    updateTask,
    deleteTask,
    moveTask,
  };
}
