import { describe, it, expect, vi, beforeEach } from 'vitest'

const { mockGet, mockPut, mockPost } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPut: vi.fn(),
  mockPost: vi.fn(),
}))

vi.mock('../client', () => ({
  default: { get: mockGet, put: mockPut, post: mockPost, patch: vi.fn(), delete: vi.fn() },
}))

import {
  fetchHabitReminderSettings,
  updateHabitReminderSettings,
  fetchHabitReminderToday,
  createGoal,
  updateGoal,
} from '../endpoints'

// Minutos al este de UTC, igual que el resto de los resúmenes.
const expectedOffset = -new Date().getTimezoneOffset()
const BASE = '/api/v1/habit-reminders'

beforeEach(() => {
  vi.clearAllMocks()
})

describe('avisos de hábitos: configuración y vista del día', () => {
  it('lee la configuración', async () => {
    const settings = {
      enabled: true,
      time: '20:00',
      daily_cap: 3,
      streak_alerts: true,
      timezone_offset_minutes: null,
      has_push_devices: false,
    }
    mockGet.mockResolvedValue({ data: settings })
    expect(await fetchHabitReminderSettings()).toEqual(settings)
    expect(mockGet).toHaveBeenCalledWith(`${BASE}/settings`)
  })

  it('al guardar manda siempre el huso horario de este navegador', async () => {
    mockPut.mockResolvedValue({ data: { enabled: true } })
    await updateHabitReminderSettings({ enabled: true, time: '21:00' })
    expect(mockPut).toHaveBeenCalledWith(`${BASE}/settings`, {
      enabled: true,
      time: '21:00',
      timezone_offset_minutes: expectedOffset,
    })
    await updateHabitReminderSettings({ streak_alerts: false })
    expect(mockPut).toHaveBeenLastCalledWith(`${BASE}/settings`, {
      streak_alerts: false,
      timezone_offset_minutes: expectedOffset,
    })
  })

  it('la vista del día manda tz_offset_minutes', async () => {
    mockGet.mockResolvedValue({
      data: { local_date: '2026-11-03', enabled: true, pending_count: 0, slots: [] },
    })
    const today = await fetchHabitReminderToday()
    expect(mockGet).toHaveBeenCalledWith(`${BASE}/today`, {
      params: { tz_offset_minutes: expectedOffset },
    })
    expect(today.pending_count).toBe(0)
  })
})

describe('metas: campos de aviso por hábito', () => {
  it('crear manda reminder_enabled y reminder_time (null si está vacía)', async () => {
    mockPost.mockResolvedValue({ data: { id: 'g1' } })
    await createGoal({ title: 'Leer', goal_type: 'binary', reminder_enabled: false, reminder_time: '07:30' })
    expect(mockPost.mock.calls[0][1]).toMatchObject({ reminder_enabled: false, reminder_time: '07:30' })
    await createGoal({ title: 'Leer', goal_type: 'binary', reminder_time: '' })
    expect(mockPost.mock.calls[1][1]).toMatchObject({ reminder_enabled: true, reminder_time: null })
  })

  it('editar manda reminder_time null para borrar la hora propia, y lo omite si no viene', async () => {
    mockPut.mockResolvedValue({ data: { id: 'g1' } })
    await updateGoal('g1', { title: 'Leer', reminder_enabled: true, reminder_time: null })
    expect(mockPut.mock.calls[0][1]).toMatchObject({ reminder_enabled: true, reminder_time: null })
    await updateGoal('g1', { title: 'Meta numérica' })
    expect('reminder_time' in mockPut.mock.calls[1][1]).toBe(false)
    expect('reminder_enabled' in mockPut.mock.calls[1][1]).toBe(false)
  })
})

describe('modo mock', () => {
  it('las funciones nuevas responden en memoria sin tocar la red', async () => {
    vi.resetModules()
    vi.stubEnv('VITE_MOCK_ENABLED', 'true')
    const mock = await import('../endpoints')
    const initial = await mock.fetchHabitReminderSettings()
    expect(initial.enabled).toBe(true)
    const saved = await mock.updateHabitReminderSettings({ enabled: false, time: '22:15' })
    expect(saved).toMatchObject({ enabled: false, time: '22:15' })
    expect((await mock.fetchHabitReminderSettings()).time).toBe('22:15')
    const today = await mock.fetchHabitReminderToday()
    expect(today.slots.length).toBeGreaterThan(0)
    expect(today.pending_count).toBe(today.slots.reduce((n, s) => n + s.habits.length, 0))
    vi.unstubAllEnvs()
  })
})
