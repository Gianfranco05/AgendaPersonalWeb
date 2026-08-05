import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { SWRConfig } from 'swr'
import { type ReactNode } from 'react'
import { useKanban, addTask, updateTask, deleteTask, moveTask } from '../useKanban'
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
