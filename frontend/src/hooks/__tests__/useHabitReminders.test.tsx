import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { SWRConfig } from 'swr'
import { type ReactNode } from 'react'
import {
  useHabitReminderSettings,
  useHabitReminderToday,
  saveHabitReminderSettings,
  useSyncReminderOffset,
  HABIT_REMINDER_SETTINGS_KEY,
  HABIT_REMINDER_TODAY_KEY,
} from '../useHabitReminders'
import * as endpoints from '../../api/endpoints'
import type { HabitReminderSettings } from '../../types'

vi.mock('../../api/endpoints', () => ({
  fetchHabitReminderSettings: vi.fn(),
  updateHabitReminderSettings: vi.fn(),
  fetchHabitReminderToday: vi.fn(),
}))

vi.mock('swr', async () => {
  const actual = await vi.importActual('swr')
  return { ...(actual as object), mutate: vi.fn() }
})

import { mutate as globalMutate } from 'swr'

function wrapper({ children }: { children: ReactNode }) {
  return <SWRConfig value={{ provider: () => new Map() }}>{children}</SWRConfig>
}

const localOffset = -new Date().getTimezoneOffset()

function settings(overrides: Partial<HabitReminderSettings> = {}): HabitReminderSettings {
  return {
    enabled: true,
    time: '20:00',
    daily_cap: 3,
    streak_alerts: true,
    timezone_offset_minutes: localOffset,
    has_push_devices: true,
    ...overrides,
  }
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('useHabitReminders', () => {
  it('lee la configuración y la vista del día con claves propias', async () => {
    vi.mocked(endpoints.fetchHabitReminderSettings).mockResolvedValue(settings())
    vi.mocked(endpoints.fetchHabitReminderToday).mockResolvedValue({
      local_date: '2026-11-03',
      enabled: true,
      pending_count: 0,
      slots: [],
    })
    const { result } = renderHook(
      () => ({ settings: useHabitReminderSettings(), today: useHabitReminderToday() }),
      { wrapper },
    )
    await waitFor(() => expect(result.current.settings.data?.time).toBe('20:00'))
    await waitFor(() => expect(result.current.today.data?.local_date).toBe('2026-11-03'))
    expect(HABIT_REMINDER_SETTINGS_KEY).not.toBe(HABIT_REMINDER_TODAY_KEY)
  })

  it('guardar revalida la configuración y la vista del día', async () => {
    vi.mocked(endpoints.updateHabitReminderSettings).mockResolvedValue(settings({ enabled: false }))
    await saveHabitReminderSettings({ enabled: false })
    expect(endpoints.updateHabitReminderSettings).toHaveBeenCalledWith({ enabled: false })
    const keys = vi.mocked(globalMutate).mock.calls.map((c) => c[0])
    expect(keys).toContain(HABIT_REMINDER_SETTINGS_KEY)
    expect(keys).toContain(HABIT_REMINDER_TODAY_KEY)
  })
})

describe('useSyncReminderOffset', () => {
  it('si hay dispositivos y el huso guardado difiere, lo actualiza', async () => {
    vi.mocked(endpoints.updateHabitReminderSettings).mockResolvedValue(settings())
    renderHook(() => useSyncReminderOffset(settings({ timezone_offset_minutes: localOffset + 60 })), { wrapper })
    await waitFor(() => expect(endpoints.updateHabitReminderSettings).toHaveBeenCalledTimes(1))
    expect(endpoints.updateHabitReminderSettings).toHaveBeenCalledWith({
      timezone_offset_minutes: localOffset,
    })
  })

  it('no hace nada si el huso coincide, si no hay dispositivos o si los avisos están apagados', async () => {
    renderHook(() => useSyncReminderOffset(settings()), { wrapper })
    renderHook(() => useSyncReminderOffset(settings({ has_push_devices: false, timezone_offset_minutes: 999 })), { wrapper })
    renderHook(() => useSyncReminderOffset(settings({ enabled: false, timezone_offset_minutes: 999 })), { wrapper })
    renderHook(() => useSyncReminderOffset(undefined), { wrapper })
    await new Promise((r) => setTimeout(r, 20))
    expect(endpoints.updateHabitReminderSettings).not.toHaveBeenCalled()
  })
})
