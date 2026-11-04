import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { SWRConfig } from 'swr'
import { type ReactNode } from 'react'
import {
  usePendingOccurrences,
  useRecurring,
  saveRecurring,
  setRecurringPaused,
  removeRecurring,
  confirmPending,
  skipPending,
} from '../useRecurring'
import { renewFixedTerm } from '../useInvestments'
import * as endpoints from '../../api/endpoints'

vi.mock('../../api/endpoints', () => ({
  fetchRecurring: vi.fn(),
  fetchOccurrences: vi.fn(),
  fetchUpcomingRecurring: vi.fn(),
  createRecurring: vi.fn(),
  updateRecurring: vi.fn(),
  deleteRecurring: vi.fn(),
  pauseRecurring: vi.fn(),
  resumeRecurring: vi.fn(),
  confirmOccurrence: vi.fn(),
  skipOccurrence: vi.fn(),
  renewInvestment: vi.fn(),
  fetchRenewals: vi.fn(),
}))

vi.mock('swr', async () => {
  const actual = await vi.importActual('swr')
  return { ...(actual as object), mutate: vi.fn() }
})

import { mutate as globalMutate } from 'swr'

function wrapper({ children }: { children: ReactNode }) {
  return <SWRConfig value={{ provider: () => new Map() }}>{children}</SWRConfig>
}

// Cada llamada a mutate() recibe un filtro de claves: se evalúan todos.
function matchers(): ((key: unknown) => boolean)[] {
  return vi
    .mocked(globalMutate)
    .mock.calls.map((c) => c[0])
    .filter((a): a is (key: unknown) => boolean => typeof a === 'function')
}

const staleBy = (key: unknown) => matchers().some((m) => m(key))

const input = {
  type: 'income' as const,
  name: 'Sueldo',
  description: null,
  notes: null,
  amount: 850000,
  currency: 'ARS',
  category_id: null,
  bank_account_id: null,
  account_type: 'cash',
  payment_method: 'transfer',
  merchant_name: '',
  merchant_category: 'other',
  frequency: 'monthly' as const,
  interval_count: 1,
  weekday: null,
  day_of_month: 5,
  month_of_year: null,
  start_date: '2026-11-01',
  end_date: null,
  requires_confirmation: false,
  notify: true,
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('lecturas', () => {
  it('useRecurring pide la lista con el filtro de estado', async () => {
    vi.mocked(endpoints.fetchRecurring).mockResolvedValue([])
    const { result } = renderHook(() => useRecurring('paused'), { wrapper })
    await waitFor(() => expect(result.current.data).toEqual([]))
    expect(endpoints.fetchRecurring).toHaveBeenCalledWith('paused')
  })

  it('usePendingOccurrences pide solo los pendientes', async () => {
    vi.mocked(endpoints.fetchOccurrences).mockResolvedValue([])
    const { result } = renderHook(() => usePendingOccurrences(), { wrapper })
    await waitFor(() => expect(result.current.data).toEqual([]))
    expect(endpoints.fetchOccurrences).toHaveBeenCalledWith('pending')
  })
})

describe('invalidación de caché', () => {
  it('crear revalida recurrentes, pendientes y próximos, y también transacciones y resumen', async () => {
    await saveRecurring(null, input)
    expect(endpoints.createRecurring).toHaveBeenCalledWith(input)
    expect(staleBy(['finance/recurring', 'all'])).toBe(true)
    expect(staleBy(['finance/recurring/occurrences', 'pending'])).toBe(true)
    expect(staleBy(['finance/recurring/upcoming', 30])).toBe(true)
    expect(staleBy(['finance/transactions', '{}'])).toBe(true)
    expect(staleBy('finance/summary')).toBe(true)
    expect(staleBy(['finance/budgets', 2026, 10])).toBe(true)
    expect(staleBy('finance/reports')).toBe(true)
    // Lo que no corresponde no se toca.
    expect(staleBy('finance/categories')).toBe(false)
    expect(staleBy(['finance/investments', 'active'])).toBe(false)
  })

  it('editar usa update', async () => {
    await saveRecurring({ id: 'r1' } as never, input)
    expect(endpoints.updateRecurring).toHaveBeenCalledWith('r1', input)
  })

  it('pausar revalida solo recurrentes; reanudar también las transacciones', async () => {
    await setRecurringPaused('r1', true)
    expect(endpoints.pauseRecurring).toHaveBeenCalledWith('r1')
    expect(staleBy(['finance/recurring', 'all'])).toBe(true)
    expect(staleBy(['finance/transactions', '{}'])).toBe(false)

    vi.mocked(globalMutate).mockClear()
    await setRecurringPaused('r1', false)
    expect(endpoints.resumeRecurring).toHaveBeenCalledWith('r1')
    expect(staleBy(['finance/transactions', '{}'])).toBe(true)
  })

  it('borrar revalida también las transacciones (quedan desvinculadas)', async () => {
    await removeRecurring('r1')
    expect(endpoints.deleteRecurring).toHaveBeenCalledWith('r1')
    expect(staleBy(['finance/transactions', '{}'])).toBe(true)
  })

  it('confirmar un pendiente revalida pendientes, transacciones, resumen, presupuestos y reportes', async () => {
    await confirmPending('o1', { amount: 31250.5 })
    expect(endpoints.confirmOccurrence).toHaveBeenCalledWith('o1', { amount: 31250.5 })
    expect(staleBy(['finance/recurring/occurrences', 'pending'])).toBe(true)
    expect(staleBy(['finance/transactions', '{}'])).toBe(true)
    expect(staleBy('finance/summary')).toBe(true)
    expect(staleBy(['finance/budgets', 2026, 10])).toBe(true)
    expect(staleBy('finance/reports')).toBe(true)
  })

  it('saltear no toca las transacciones', async () => {
    await skipPending('o1')
    expect(endpoints.skipOccurrence).toHaveBeenCalledWith('o1')
    expect(staleBy(['finance/recurring/occurrences', 'pending'])).toBe(true)
    expect(staleBy(['finance/transactions', '{}'])).toBe(false)
  })

  it('renovar revalida inversiones, patrimonio, historial, resumen y transacciones', async () => {
    vi.mocked(endpoints.renewInvestment).mockResolvedValue({} as never)
    const body = { mode: 'principal_only' as const, interest_rate_tna: 28, term_days: 30 }
    await renewFixedTerm('i1', body)
    expect(endpoints.renewInvestment).toHaveBeenCalledWith('i1', body)
    expect(staleBy(['finance/investments', 'active'])).toBe(true)
    expect(staleBy('finance/net-worth')).toBe(true)
    expect(staleBy('finance/investments/summary')).toBe(true)
    expect(staleBy(['finance/investments/renewals', 'i1'])).toBe(true)
    expect(staleBy(['finance/transactions', '{}'])).toBe(true)
    expect(staleBy('finance/summary')).toBe(true)
  })

  it('si la API falla no revalida', async () => {
    vi.mocked(endpoints.confirmOccurrence).mockRejectedValueOnce(new Error('409'))
    await expect(confirmPending('o1', { amount: 1 })).rejects.toThrow('409')
    expect(globalMutate).not.toHaveBeenCalled()
  })
})
