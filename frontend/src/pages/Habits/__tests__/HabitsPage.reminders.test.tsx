import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'
import type { HabitReminderSettings } from '../../../types'

vi.mock('../../../hooks/useHabits', () => ({
  useHabits: vi.fn(() => ({ data: [], isLoading: false, mutate: vi.fn() })),
  addHabit: vi.fn(),
  editHabit: vi.fn(),
}))
vi.mock('../../../hooks/useGoals', () => ({ checkInGoal: vi.fn() }))
vi.mock('../MonthlyHabitGrid', () => ({ default: () => null }))
vi.mock('../../../hooks/useHabitReminders', () => ({
  useHabitReminderSettings: vi.fn(),
  saveHabitReminderSettings: vi.fn(),
  refreshHabitReminderToday: vi.fn(),
  useSyncReminderOffset: vi.fn(),
}))

import { useHabitReminderSettings, saveHabitReminderSettings } from '../../../hooks/useHabitReminders'
import HabitsPage from '../HabitsPage'

const swr = (data: HabitReminderSettings | undefined) =>
  ({ data, isLoading: false, mutate: vi.fn() }) as never

const base: HabitReminderSettings = {
  enabled: true,
  time: '20:00',
  daily_cap: 3,
  streak_alerts: true,
  timezone_offset_minutes: -180,
  has_push_devices: true,
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(saveHabitReminderSettings).mockResolvedValue(undefined)
})

describe('Hábitos: interruptor de avisos de un toque', () => {
  it('con los avisos encendidos, un toque los apaga', async () => {
    vi.mocked(useHabitReminderSettings).mockReturnValue(swr(base))
    renderWithProviders(<HabitsPage />)
    const toggle = screen.getByRole('switch', { name: /avisos de hábitos/i })
    expect(toggle).toHaveAttribute('aria-checked', 'true')
    fireEvent.click(toggle)
    await waitFor(() => expect(saveHabitReminderSettings).toHaveBeenCalledWith({ enabled: false }))
  })

  it('apagados, un toque los vuelve a encender', async () => {
    vi.mocked(useHabitReminderSettings).mockReturnValue(swr({ ...base, enabled: false }))
    renderWithProviders(<HabitsPage />)
    fireEvent.click(screen.getByRole('switch', { name: /avisos de hábitos/i }))
    await waitFor(() => expect(saveHabitReminderSettings).toHaveBeenCalledWith({ enabled: true }))
  })

  it('mientras carga la configuración no muestra el interruptor', () => {
    vi.mocked(useHabitReminderSettings).mockReturnValue(swr(undefined))
    renderWithProviders(<HabitsPage />)
    expect(screen.queryByRole('switch', { name: /avisos de hábitos/i })).not.toBeInTheDocument()
  })
})
