import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'
import KanbanBoard from '../KanbanBoard'

vi.mock('../../../hooks/useKanban', () => ({
  useKanban: vi.fn(),
}))

import { useKanban } from '../../../hooks/useKanban'

const mockColumns = [
  { id: 'pending', title: 'Pendiente', tasks: [{ id: 't1', title: 'Task 1', description: '', status: 'pending', order: 0 }] },
  { id: 'in_progress', title: 'En Proceso', tasks: [{ id: 't2', title: 'Task 2', description: '', status: 'in_progress', order: 0 }] },
  { id: 'completed', title: 'Completado', tasks: [] },
]

beforeEach(() => {
  vi.clearAllMocks()
})

describe('KanbanBoard', () => {
  it('renders tasks grouped by status', () => {
    vi.mocked(useKanban).mockReturnValue({
      columns: mockColumns,
      addTask: vi.fn(),
      updateTask: vi.fn(),
      deleteTask: vi.fn(),
      moveTask: vi.fn(),
    })

    renderWithProviders(<KanbanBoard />)
    expect(screen.getByText('Tareas')).toBeInTheDocument()
    expect(screen.getByText('Pendiente')).toBeInTheDocument()
    expect(screen.getByText('En Proceso')).toBeInTheDocument()
    expect(screen.getByText('Completado')).toBeInTheDocument()
    expect(screen.getByText('Task 1')).toBeInTheDocument()
    expect(screen.getByText('Task 2')).toBeInTheDocument()
  })
})
