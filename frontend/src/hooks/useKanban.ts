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

const byOrder = (a: Task, b: Task) => a.order - b.order;

/**
 * Aplica un movimiento igual que el backend (inserta en la columna destino y
 * reindexa esa columna), para mostrarlo al instante mientras viaja el request.
 */
export function applyMove(tasks: Task[], taskId: string, newStatus: TaskStatus, newOrder: number): Task[] {
  const moving = tasks.find((t) => t.id === taskId);
  if (!moving) return tasks;
  const column = tasks.filter((t) => t.status === newStatus && t.id !== taskId).sort(byOrder);
  column.splice(Math.max(0, Math.min(newOrder, column.length)), 0, { ...moving, status: newStatus });
  const reindexed = new Map(column.map((t, i) => [t.id, { ...t, order: i }]));
  return tasks.map((t) => reindexed.get(t.id) ?? t);
}

/**
 * El tablero filtrado por área solo muestra una parte de la columna, pero la API
 * inserta en la columna completa (todas las áreas): el índice de la columna
 * visible hay que traducirlo a la posición real o la tarea cae en otro lado.
 */
export function resolveMoveIndex(
  tasks: Task[],
  visible: Task[],
  taskId: string,
  newStatus: TaskStatus,
  visibleIndex: number,
): number {
  const full = tasks.filter((t) => t.status === newStatus && t.id !== taskId).sort(byOrder);
  const shown = visible.filter((t) => t.id !== taskId);
  const anchor = shown[visibleIndex];
  if (anchor) return full.findIndex((t) => t.id === anchor.id);
  const last = shown[shown.length - 1];
  return last ? full.findIndex((t) => t.id === last.id) + 1 : full.length;
}

/** `current`: lista actual de tareas; si se pasa, el movimiento se refleja antes de que responda la API. */
export async function moveTask(
  taskId: string,
  newStatus: TaskStatus,
  newOrder: number,
  current?: Task[],
) {
  // Sin esto, @hello-pangea/dnd suelta la tarjeta en su lugar y recién la
  // mueve cuando vuelve el request: se veía el salto hacia atrás.
  if (current) {
    await globalMutate(TASKS_KEY, applyMove(current, taskId, newStatus, newOrder), { revalidate: false });
  }
  try {
    await apiMoveTask(taskId, newStatus, newOrder);
  } finally {
    // También si falla: revalida y deshace el movimiento optimista.
    await globalMutate(TASKS_KEY);
  }
}

/** area: si se pasa (y no es 'Todas'), filtra las columnas a esa área. */
export function useKanban(area?: string) {
  const { data, isLoading } = useApiSWR(TASKS_KEY, () => fetchTasks());
  const tasks = data ?? [];
  const areas = Array.from(new Set(tasks.map((t) => t.area))).sort();
  const filtered = area && area !== 'Todas' ? tasks.filter((t) => t.area === area) : tasks;
  const columns = groupByStatus(filtered);

  // `visibleIndex` es el índice dentro de la columna que se ve en pantalla.
  const moveVisibleTask = (taskId: string, newStatus: TaskStatus, visibleIndex: number) => {
    const visible = columns.find((c) => c.id === newStatus)?.tasks ?? [];
    return moveTask(taskId, newStatus, resolveMoveIndex(tasks, visible, taskId, newStatus, visibleIndex), tasks);
  };

  return {
    tasks,
    areas,
    columns,
    isLoading,
    addTask,
    updateTask,
    deleteTask,
    moveTask: moveVisibleTask,
  };
}
