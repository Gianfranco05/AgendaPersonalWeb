import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'
import { LocationProbe, toastMessages, resetToasts } from '../../../test/openParam'
import type { Goal } from '../../../types'

vi.mock('../../../hooks/useHabits', () => ({ useHabits: vi.fn(), addHabit: vi.fn(), editHabit: vi.fn() }))
vi.mock('../../../hooks/useGoals', () => ({ checkInGoal: vi.fn() }))
vi.mock('../MonthlyHabitGrid', () => ({ default: () => null }))
vi.mock('../../../hooks/useHabitReminders', () => ({
  useHabitReminderSettings: vi.fn(() => ({ data: undefined })),
  saveHabitReminderSettings: vi.fn(),
  refreshHabitReminderToday: vi.fn(),
  useSyncReminderOffset: vi.fn(),
}))

import { useHabits } from '../../../hooks/useHabits'
import HabitsPage from '../HabitsPage'

const habit = (over: Partial<Goal>): Goal => ({
  id: 'h1', title: 'Leer', description: null, goal_type: 'binary', target_value: 1, current_value: 0,
  unit: null, end_date: null, color: '#7C3AED', icon: 'fa-bullseye', is_completed: false, ...over,
})

function mockHabits(data: Goal[] | undefined) {
  vi.mocked(useHabits).mockReturnValue({ data, isLoading: data === undefined, mutate: vi.fn() } as never)
}

function renderAt(url: string) {
  return renderWithProviders(
    <>
      <HabitsPage />
      <LocationProbe />
    </>,
    { router: { initialEntries: [url] } },
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  resetToasts()
})

describe('HabitsPage: ?open=<id> desde el buscador', () => {
  it('abre el formulario de edición del hábito y limpia la URL', async () => {
    mockHabits([habit({ id: 'h1' }), habit({ id: 'h2', title: 'Meditar' })])
    renderAt('/habits?open=h2')

    expect(await screen.findByText('Editar hábito')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Meditar')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(/^\/habits$/))
    expect(toastMessages()).toEqual([])
  })

  it('una métrica se abre como "Editar métrica"', async () => {
    mockHabits([habit({ id: 'm1', title: 'Pasos', goal_type: 'metric', target_value: 8000, unit: 'pasos' })])
    renderAt('/habits?open=m1')

    expect(await screen.findByText('Editar métrica')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Pasos')).toBeInTheDocument()
  })

  it('si el id no existe avisa y no abre el formulario', async () => {
    mockHabits([habit({ id: 'h1' })])
    renderAt('/habits?open=borrado')

    await waitFor(() => expect(toastMessages()).toEqual(['Ese elemento ya no existe']))
    expect(screen.queryByText('Editar hábito')).not.toBeInTheDocument()
  })
})
