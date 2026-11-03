import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'
import { LocationProbe, toastMessages, resetToasts } from '../../../test/openParam'
import type { Goal } from '../../../types'

vi.mock('../../../hooks/useGoals', () => ({
  useGoals: vi.fn(), addGoal: vi.fn(), editGoal: vi.fn(), removeGoal: vi.fn(), checkInGoal: vi.fn(),
}))

import { useGoals } from '../../../hooks/useGoals'
import GoalsPage from '../GoalsPage'

const goal = (over: Partial<Goal>): Goal => ({
  id: 'g1', title: 'Correr 10k', description: null, goal_type: 'progress', target_value: 10, current_value: 2,
  unit: 'km', end_date: null, color: '#7C3AED', icon: 'fa-bullseye', is_completed: false, ...over,
})

function mockGoals(data: Goal[] | undefined) {
  vi.mocked(useGoals).mockReturnValue({ data, isLoading: data === undefined, mutate: vi.fn() } as never)
}

function renderAt(url: string) {
  return renderWithProviders(
    <>
      <GoalsPage />
      <LocationProbe />
    </>,
    { router: { initialEntries: [url] } },
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  resetToasts()
})

describe('GoalsPage: ?open=<id> desde el buscador', () => {
  it('abre el formulario de edición de la meta y limpia la URL', async () => {
    mockGoals([goal({ id: 'g1' }), goal({ id: 'g2', title: 'Ahorrar para viaje', goal_type: 'savings' })])
    renderAt('/goals?open=g2')

    expect(await screen.findByText('Editar meta')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Ahorrar para viaje')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(/^\/goals$/))
    expect(toastMessages()).toEqual([])
  })

  it('espera a que carguen las metas antes de decidir', async () => {
    mockGoals(undefined)
    const { rerender } = renderAt('/goals?open=g1')
    expect(toastMessages()).toEqual([])
    mockGoals([goal({ id: 'g1' })])
    rerender(<><GoalsPage /><LocationProbe /></>)
    expect(await screen.findByText('Editar meta')).toBeInTheDocument()
  })

  it('si el id no existe avisa y no abre el formulario', async () => {
    mockGoals([goal({ id: 'g1' })])
    renderAt('/goals?open=borrada')

    await waitFor(() => expect(toastMessages()).toEqual(['Ese elemento ya no existe']))
    expect(screen.queryByText('Editar meta')).not.toBeInTheDocument()
  })
})
