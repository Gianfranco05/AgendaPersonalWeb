import { useState, useEffect, useCallback } from 'react';
import type { Task, TaskStatus, KanbanColumn } from '../types';

const STORAGE_KEY = 'kanban-tasks';

const MOCK_TASKS: Task[] = [
  { id: 't1', title: 'Configurar entorno de desarrollo', description: 'Instalar dependencias y configurar herramientas', status: 'completed', order: 0 },
  { id: 't2', title: 'Diseñar esquema de base de datos', description: 'Definir tablas, relaciones e índices', status: 'in_progress', order: 0 },
  { id: 't3', title: 'Implementar API de autenticación', description: 'JWT + refresh tokens', status: 'pending', order: 0 },
  { id: 't4', title: 'Escribir tests unitarios', description: 'Cobertura mínima 80%', status: 'pending', order: 1 },
  { id: 't5', title: 'Revisar documentación', description: 'Actualizar README y docs de API', status: 'in_progress', order: 1 },
];

function loadFromStorage(): Task[] {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored) {
    try {
      return JSON.parse(stored);
    } catch {
      // corrupted data, fall through to mock
    }
  }
  return [...MOCK_TASKS];
}

function saveToStorage(tasks: Task[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));
}

export function useKanban() {
  const [tasks, setTasks] = useState<Task[]>(() => loadFromStorage());

  useEffect(() => {
    saveToStorage(tasks);
  }, [tasks]);

  const columns: KanbanColumn[] = [
    { id: 'pending', title: 'Pendiente', tasks: tasks.filter((t) => t.status === 'pending').sort((a, b) => a.order - b.order) },
    { id: 'in_progress', title: 'En Proceso', tasks: tasks.filter((t) => t.status === 'in_progress').sort((a, b) => a.order - b.order) },
    { id: 'completed', title: 'Completado', tasks: tasks.filter((t) => t.status === 'completed').sort((a, b) => a.order - b.order) },
  ];

  const addTask = useCallback((title: string, description: string) => {
    const pendingTasks = tasks.filter((t) => t.status === 'pending');
    const newTask: Task = {
      id: `task-${Date.now()}`,
      title,
      description,
      status: 'pending',
      order: pendingTasks.length,
    };
    setTasks((prev) => [...prev, newTask]);
  }, [tasks]);

  const updateTask = useCallback((id: string, updates: Partial<Pick<Task, 'title' | 'description'>>) => {
    setTasks((prev) =>
      prev.map((t) => (t.id === id ? { ...t, ...updates } : t))
    );
  }, []);

  const deleteTask = useCallback((id: string) => {
    setTasks((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const moveTask = useCallback((taskId: string, newStatus: TaskStatus, newOrder: number) => {
    setTasks((prev) => {
      const updated = prev.map((t) => {
        if (t.id === taskId) {
          return { ...t, status: newStatus, order: newOrder };
        }
        return t;
      });

      // Reorder tasks in the destination column
      const destTasks = updated
        .filter((t) => t.status === newStatus)
        .sort((a, b) => a.order - b.order);

      const reordered = updated.map((t) => {
        if (t.id === taskId) return t; // already set order
        if (t.status === newStatus) {
          const idx = destTasks.findIndex((dt) => dt.id === t.id);
          if (idx >= newOrder) {
            return { ...t, order: t.order + 1 };
          }
        }
        return t;
      });

      return reordered;
    });
  }, []);

  return {
    columns,
    addTask,
    updateTask,
    deleteTask,
    moveTask,
  };
}
