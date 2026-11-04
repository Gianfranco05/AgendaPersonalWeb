import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { SWRConfig } from 'swr'
import { type ReactNode } from 'react'
import { useKanban, addTask, updateTask, deleteTask, moveTask, applyMove, resolveMoveIndex } from '../useKanban'
import * as endpoints from '../../api/endpoints'

vi.mock('../../api/endpoints', () => ({
  fetchTasks: vi.fn(),
  createTask: vi.fn(),
  updateTask: vi.fn(),
  deleteTask: vi.fn(),
  moveTask: vi.fn(),
}))

vi.mock('swr', async () => {
  const actual = await vi.importActual('swr')
  return { ...actual as object, mutate: vi.fn() }
})

import { mutate as globalMutate } from 'swr'

const mockTasks = [
  { id: 't1', title: 'Configurar entorno', description: '', area: 'Trabajo', priority: 'media' as const, due_date: null, status: 'completed' as const, order: 0 },
  { id: 't2', title: 'Diseñar esquema', description: '', area: 'Trabajo', priority: 'alta' as const, due_date: null, status: 'in_progress' as const, order: 0 },
  { id: 't3', title: 'Renovar DNI', description: '', area: 'Otras Tareas', priority: 'media' as const, due_date: null, status: 'pending' as const, order: 0 },
]

function createWrapper(fallback: Record<string, unknown> = {}) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <SWRConfig value={{ provider: () => new Map(), fallback }}>
        {children}
      </SWRConfig>
    )
  }
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('useKanban', () => {
  it('groups tasks by status', async () => {
    vi.mocked(endpoints.fetchTasks).mockResolvedValue(mockTasks)
    const { result } = renderHook(() => useKanban(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.tasks).toHaveLength(3))

    const pending = result.current.columns.find((c) => c.id === 'pending')
    expect(pending?.tasks).toHaveLength(1)
    expect(pending?.tasks[0].title).toBe('Renovar DNI')
  })

  it('exposes the distinct areas', async () => {
    vi.mocked(endpoints.fetchTasks).mockResolvedValue(mockTasks)
    const { result } = renderHook(() => useKanban(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.areas).toEqual(['Otras Tareas', 'Trabajo']))
  })

  it('filters columns by area when provided', async () => {
    vi.mocked(endpoints.fetchTasks).mockResolvedValue(mockTasks)
    const { result } = renderHook(() => useKanban('Trabajo'), { wrapper: createWrapper() })
    await waitFor(() => {
      const total = result.current.columns.reduce((acc, c) => acc + c.tasks.length, 0)
      expect(total).toBe(2)
    })
  })
})

describe('addTask', () => {
  it('creates a task with defaults and invalidates the cache', async () => {
    await addTask({ title: 'Nueva tarea' })
    expect(endpoints.createTask).toHaveBeenCalledWith({
      title: 'Nueva tarea',
      description: '',
      area: 'General',
      priority: 'media',
      due_date: null,
      status: 'pending',
      order: 0,
    })
    expect(globalMutate).toHaveBeenCalled()
  })
})

describe('updateTask', () => {
  it('calls the API and invalidates the cache', async () => {
    await updateTask('t1', { title: 'Editada' })
    expect(endpoints.updateTask).toHaveBeenCalledWith('t1', { title: 'Editada' })
    expect(globalMutate).toHaveBeenCalled()
  })
})

describe('deleteTask', () => {
  it('calls the API and invalidates the cache', async () => {
    await deleteTask('t3')
    expect(endpoints.deleteTask).toHaveBeenCalledWith('t3')
    expect(globalMutate).toHaveBeenCalled()
  })
})

describe('moveTask', () => {
  it('calls the API and invalidates the cache', async () => {
    await moveTask('t1', 'pending', 0)
    expect(endpoints.moveTask).toHaveBeenCalledWith('t1', 'pending', 0)
    expect(globalMutate).toHaveBeenCalled()
  })
})

describe('applyMove / resolveMoveIndex', () => {
  const task = (id: string, area: string, status: 'pending' | 'in_progress' | 'completed', order: number) => ({
    id, title: id, description: '', area, priority: 'media' as const, due_date: null, status, order,
  })
  // Columna 'pending' completa: A(Otra) B(Trab) C(Trab)
  const all = [task('A', 'Otra', 'pending', 0), task('B', 'Trab', 'pending', 1), task('C', 'Trab', 'pending', 2)]

  it('applyMove reindexa la columna destino como el backend', () => {
    const moved = applyMove(all, 'C', 'pending', 0)
    const col = moved.filter((t) => t.status === 'pending').sort((a, b) => a.order - b.order)
    expect(col.map((t) => t.id)).toEqual(['C', 'A', 'B'])
  })

  it('applyMove cambia de columna', () => {
    const moved = applyMove(all, 'B', 'in_progress', 0)
    expect(moved.find((t) => t.id === 'B')).toMatchObject({ status: 'in_progress', order: 0 })
  })

  it('con filtro de área, traduce el índice visible al de la columna completa', () => {
    // Vista filtrada 'Trab': [B, C]. Arrastrar B al final (índice 1) => queda después de C.
    const visible = [all[1], all[2]]
    const idx = resolveMoveIndex(all, visible, 'B', 'pending', 1)
    const moved = applyMove(all, 'B', 'pending', idx)
    const col = moved.filter((t) => t.status === 'pending').sort((a, b) => a.order - b.order)
    expect(col.map((t) => t.id)).toEqual(['A', 'C', 'B'])
  })

  it('soltar en una columna visible vacía va al final de la columna completa', () => {
    const others = [task('X', 'Otra', 'completed', 0), task('Y', 'Otra', 'completed', 1), task('B', 'Trab', 'pending', 0)]
    expect(resolveMoveIndex(others, [], 'B', 'completed', 0)).toBe(2)
  })

  it('moveTask con la lista actual refleja el movimiento antes de la API', async () => {
    await moveTask('B', 'pending', 2, all)
    expect(globalMutate).toHaveBeenNthCalledWith(1, 'kanban/tasks', expect.any(Array), { revalidate: false })
    expect(endpoints.moveTask).toHaveBeenCalledWith('B', 'pending', 2)
  })
})
