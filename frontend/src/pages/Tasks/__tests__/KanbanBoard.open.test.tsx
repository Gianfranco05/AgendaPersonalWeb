import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import { useNavigate } from 'react-router-dom'
import { renderWithProviders } from '../../../test/test-utils'
import { LocationProbe, toastMessages, resetToasts, stubScrollIntoView } from '../../../test/openParam'
import type { Task, KanbanColumn } from '../../../types'

vi.mock('../../../hooks/useKanban', () => ({ useKanban: vi.fn() }))

import { useKanban } from '../../../hooks/useKanban'
import KanbanBoard from '../KanbanBoard'

const task = (over: Partial<Task>): Task => ({
  id: 't1', title: 'Tarea 1', description: '', area: 'Trabajo', priority: 'media',
  due_date: null, status: 'pending', order: 0, ...over,
})

function mockBoard(tasks: Task[], isLoading = false) {
  const areas = Array.from(new Set(tasks.map((t) => t.area))).sort()
  // Igual que el hook real: el filtro por área recorta las columnas.
  vi.mocked(useKanban).mockImplementation((area?: string) => {
    const shown = area && area !== 'Todas' ? tasks.filter((t) => t.area === area) : tasks
    const columns: KanbanColumn[] = [
      { id: 'pending', title: 'Pendiente', tasks: shown.filter((t) => t.status === 'pending') },
      { id: 'in_progress', title: 'En Proceso', tasks: shown.filter((t) => t.status === 'in_progress') },
      { id: 'completed', title: 'Completado', tasks: shown.filter((t) => t.status === 'completed') },
    ]
    return { tasks, areas, columns, isLoading, addTask: vi.fn(), updateTask: vi.fn(), deleteTask: vi.fn(), moveTask: vi.fn() }
  })
}

function SearchJump({ to }: { to: string }) {
  const navigate = useNavigate()
  return <button onClick={() => navigate(to)}>ir-a-t9</button>
}

function renderAt(url: string) {
  return renderWithProviders(
    <>
      <KanbanBoard />
      <LocationProbe />
    </>,
    { router: { initialEntries: [url] } },
  )
}

let scroll: ReturnType<typeof vi.fn>
beforeEach(() => {
  vi.clearAllMocks()
  resetToasts()
  scroll = stubScrollIntoView()
})

describe('KanbanBoard: ?open=<id> desde el buscador', () => {
  it('lleva a la tarea pedida, la resalta y limpia la URL', async () => {
    mockBoard([task({ id: 't1' }), task({ id: 't2', title: 'Pagar patente', status: 'in_progress' })])
    renderAt('/tasks?open=t2')

    await waitFor(() => expect(scroll).toHaveBeenCalledTimes(1))
    const card = screen.getByText('Pagar patente').closest('#item-t2')
    expect(card).not.toBeNull()
    expect(card).toHaveClass('search-reveal')
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(/^\/tasks$/))
    expect(toastMessages()).toEqual([])
  })

  it('espera a que carguen las tareas antes de decidir que no existe', async () => {
    mockBoard([], true)
    const { rerender } = renderAt('/tasks?open=t2')
    expect(toastMessages()).toEqual([])
    expect(screen.getByTestId('location')).toHaveTextContent('/tasks?open=t2')
    mockBoard([task({ id: 't2', title: 'Recién cargada' })])
    rerender(
      <>
        <KanbanBoard />
        <LocationProbe />
      </>,
    )
    await waitFor(() => expect(scroll).toHaveBeenCalled())
  })

  it('si la tarea existe pero el filtro de área la oculta, muestra todas y la resalta', async () => {
    mockBoard([
      task({ id: 't1', area: 'Trabajo' }),
      task({ id: 't9', title: 'Comprar pan', area: 'Casa' }),
    ])
    renderWithProviders(
      <>
        <KanbanBoard />
        <SearchJump to="/tasks?open=t9" />
      </>,
      { router: { initialEntries: ['/tasks'] } },
    )
    fireEvent.click(screen.getByRole('button', { name: 'Trabajo' }))
    expect(screen.queryByText('Comprar pan')).not.toBeInTheDocument()

    // El buscador navega a /tasks?open=t9 con el tablero ya montado y filtrado.
    fireEvent.click(screen.getByText('ir-a-t9'))

    expect(await screen.findByText('Comprar pan')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText('Comprar pan').closest('#item-t9')).toHaveClass('search-reveal'))
  })

  it('si el id no existe avisa y deja el tablero', async () => {
    mockBoard([task({ id: 't1' })])
    renderAt('/tasks?open=borrada')

    await waitFor(() => expect(toastMessages()).toEqual(['Ese elemento ya no existe']))
    expect(screen.getByTestId('location')).toHaveTextContent(/^\/tasks$/)
    expect(screen.getByText('Tarea 1')).toBeInTheDocument()
    expect(scroll).not.toHaveBeenCalled()
  })
})
