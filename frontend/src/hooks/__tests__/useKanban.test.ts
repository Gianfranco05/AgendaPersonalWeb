import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useKanban } from '../useKanban'

const STORAGE_KEY = 'kanban-tasks'
const MOCK_TASKS = [
  { id: 't1', title: 'Configurar entorno de desarrollo', description: 'Instalar dependencias y configurar herramientas', status: 'completed', order: 0 },
  { id: 't2', title: 'Diseñar esquema de base de datos', description: 'Definir tablas, relaciones e índices', status: 'in_progress', order: 0 },
  { id: 't3', title: 'Implementar API de autenticación', description: 'JWT + refresh tokens', status: 'pending', order: 0 },
  { id: 't4', title: 'Escribir tests unitarios', description: 'Cobertura mínima 80%', status: 'pending', order: 1 },
  { id: 't5', title: 'Revisar documentación', description: 'Actualizar README y docs de API', status: 'in_progress', order: 1 },
]

function persistedTasks() {
  return [
    { id: 'p1', title: 'Persisted task', description: 'From storage', status: 'pending', order: 0 },
  ]
}

beforeEach(() => {
  localStorage.clear()
})

describe('useKanban', () => {
  it('loads mock tasks when localStorage is empty', () => {
    const { result } = renderHook(() => useKanban())
    const pending = result.current.columns.find((c) => c.id === 'pending')
    expect(pending?.tasks).toHaveLength(2)
  })

  it('loads persisted tasks from localStorage', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(persistedTasks()))
    const { result } = renderHook(() => useKanban())
    const pending = result.current.columns.find((c) => c.id === 'pending')
    expect(pending?.tasks).toHaveLength(1)
    expect(pending?.tasks[0].title).toBe('Persisted task')
  })

  it('addTask creates a pending task', () => {
    const { result } = renderHook(() => useKanban())
    act(() => {
      result.current.addTask('New task', 'Description')
    })
    const pending = result.current.columns.find((c) => c.id === 'pending')
    expect(pending?.tasks.some((t) => t.title === 'New task')).toBe(true)
  })

  it('moveTask changes task status', () => {
    const { result } = renderHook(() => useKanban())
    act(() => {
      result.current.moveTask('t1', 'pending', 0)
    })
    const pending = result.current.columns.find((c) => c.id === 'pending')
    expect(pending?.tasks.some((t) => t.id === 't1')).toBe(true)
    const completed = result.current.columns.find((c) => c.id === 'completed')
    expect(completed?.tasks.some((t) => t.id === 't1')).toBe(false)
  })

  it('deleteTask removes a task', () => {
    const { result } = renderHook(() => useKanban())
    act(() => {
      result.current.deleteTask('t3')
    })
    const pending = result.current.columns.find((c) => c.id === 'pending')
    expect(pending?.tasks.some((t) => t.id === 't3')).toBe(false)
  })

  it('persists tasks to localStorage after addTask', () => {
    const { result } = renderHook(() => useKanban())
    act(() => {
      result.current.addTask('Persist me', '')
    })
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY)!)
    expect(stored.some((t: { title: string }) => t.title === 'Persist me')).toBe(true)
  })
})
