import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'
import type { HabitReminderSettings, HabitReminderToday } from '../../../types'

vi.mock('../../../hooks/useHabitReminders', () => ({
  useHabitReminderSettings: vi.fn(),
  useHabitReminderToday: vi.fn(),
  saveHabitReminderSettings: vi.fn(),
  useSyncReminderOffset: vi.fn(),
}))

import {
  useHabitReminderSettings,
  useHabitReminderToday,
  saveHabitReminderSettings,
} from '../../../hooks/useHabitReminders'
import HabitReminderSection from '../HabitReminderSection'

const swr = <T,>(data: T | undefined) =>
  ({ data, isLoading: false, error: undefined, isValidating: false, mutate: vi.fn() }) as never

function settings(overrides: Partial<HabitReminderSettings> = {}): HabitReminderSettings {
  return {
    enabled: true,
    time: '20:00',
    daily_cap: 3,
    streak_alerts: true,
    timezone_offset_minutes: -180,
    has_push_devices: true,
    ...overrides,
  }
}

const today = (overrides: Partial<HabitReminderToday> = {}): HabitReminderToday => ({
  local_date: '2026-11-03',
  enabled: true,
  pending_count: 2,
  slots: [
    {
      time: '20:00',
      status: 'upcoming',
      habits: [
        { id: 'a', title: 'Agua', icon: null, streak: 0 },
        { id: 'b', title: 'Leer', icon: null, streak: 5 },
      ],
    },
  ],
  ...overrides,
})

function setup(s: HabitReminderSettings = settings(), t: HabitReminderToday = today()) {
  vi.mocked(useHabitReminderSettings).mockReturnValue(swr(s))
  vi.mocked(useHabitReminderToday).mockReturnValue(swr(t))
  return renderWithProviders(<HabitReminderSection />)
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(saveHabitReminderSettings).mockResolvedValue(undefined)
})

describe('HabitReminderSection', () => {
  it('muestra los avisos encendidos y apaga con un toque', async () => {
    setup()
    const toggle = screen.getByRole('switch', { name: /avisarme si me falta marcar/i })
    expect(toggle).toHaveAttribute('aria-checked', 'true')
    fireEvent.click(toggle)
    await waitFor(() => expect(saveHabitReminderSettings).toHaveBeenCalledWith({ enabled: false }))
  })

  it('guarda la hora elegida como HH:MM', async () => {
    setup()
    fireEvent.change(screen.getByLabelText(/hora del aviso/i), { target: { value: '21:00' } })
    await waitFor(() => expect(saveHabitReminderSettings).toHaveBeenCalledWith({ time: '21:00' }))
  })

  it('no guarda una hora vacía', () => {
    setup()
    fireEvent.change(screen.getByLabelText(/hora del aviso/i), { target: { value: '' } })
    expect(saveHabitReminderSettings).not.toHaveBeenCalled()
  })

  it('guarda el máximo por día (1 a 5) y el interruptor de rachas', async () => {
    setup()
    const cap = screen.getByLabelText(/máximo de avisos por día/i) as HTMLSelectElement
    expect(Array.from(cap.options).map((o) => o.value)).toEqual(['1', '2', '3', '4', '5'])
    fireEvent.change(cap, { target: { value: '5' } })
    await waitFor(() => expect(saveHabitReminderSettings).toHaveBeenCalledWith({ daily_cap: 5 }))
    fireEvent.click(screen.getByRole('switch', { name: /destacar rachas/i }))
    await waitFor(() => expect(saveHabitReminderSettings).toHaveBeenCalledWith({ streak_alerts: false }))
  })

  it('resume lo que se avisa hoy', () => {
    setup()
    expect(screen.getByText(/Agua, Leer/)).toBeInTheDocument()
    expect(screen.getByText(/a las 20:00/)).toBeInTheDocument()
  })

  it('no promete una franja cuya ventana ya pasó sin avisar', () => {
    const missed = today({
      slots: [{ time: '07:05', status: 'missed', habits: [{ id: 'a', title: 'Agua', icon: null, streak: 0 }] }],
    })
    setup(settings(), missed)
    expect(screen.queryByText(/a las 07:05/)).not.toBeInTheDocument()
  })

  it('una franja ya enviada se dice como enviada y la que viene se promete', () => {
    const mixed = today({
      slots: [
        { time: '20:00', status: 'sent', habits: [{ id: 'a', title: 'Agua', icon: null, streak: 0 }] },
        { time: '22:30', status: 'upcoming', habits: [{ id: 'b', title: 'Leer', icon: null, streak: 0 }] },
      ],
    })
    setup(settings(), mixed)
    expect(screen.getByText('A las 20:00 ya te avisamos: Agua')).toBeInTheDocument()
    expect(screen.getByText('Hoy a las 22:30 te avisamos de: Leer')).toBeInTheDocument()
  })

  it('fusionada, tope alcanzado o sin dispositivos no se prometen; due sí', () => {
    const h = [{ id: 'a', title: 'Agua', icon: null, streak: 0 }]
    setup(
      settings(),
      today({
        slots: [
          { time: '08:00', status: 'merged', habits: h },
          { time: '09:00', status: 'capped', habits: h },
          { time: '10:00', status: 'no_devices', habits: h },
          { time: '11:00', status: 'due', habits: h },
        ],
      }),
    )
    expect(screen.queryByText(/a las 08:00|a las 09:00|a las 10:00/)).not.toBeInTheDocument()
    expect(screen.getByText('Hoy a las 11:00 te avisamos de: Agua')).toBeInTheDocument()
  })

  it('si ya marcó todo lo dice', () => {
    setup(settings(), today({ pending_count: 0, slots: [] }))
    expect(screen.getByText(/ya marcaste todo hoy/i)).toBeInTheDocument()
  })

  it('aclara que los avisos llegan a la app de Android y avisa si no hay dispositivos', () => {
    setup(settings({ has_push_devices: false }))
    expect(screen.getByText(/llegan a la app de Android/i)).toBeInTheDocument()
    expect(screen.getByText(/todavía no tenés ningún celular/i)).toBeInTheDocument()
  })

  it('con dispositivos no muestra la advertencia', () => {
    setup(settings({ has_push_devices: true }))
    expect(screen.queryByText(/todavía no tenés ningún celular/i)).not.toBeInTheDocument()
  })

  it('apagada no ofrece el resumen del día', () => {
    setup(settings({ enabled: false }))
    expect(screen.getByRole('switch', { name: /avisarme si me falta marcar/i })).toHaveAttribute('aria-checked', 'false')
    expect(screen.queryByText(/Agua, Leer/)).not.toBeInTheDocument()
  })
})
