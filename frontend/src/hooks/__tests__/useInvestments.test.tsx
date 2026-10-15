import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { SWRConfig } from 'swr'
import { type ReactNode } from 'react'
import {
  useInvestments,
  useNetWorth,
  saveInvestment,
  setInvestmentStatus,
  removeInvestment,
  saveInvestmentSettings,
} from '../useInvestments'
import * as endpoints from '../../api/endpoints'

vi.mock('../../api/endpoints', () => ({
  fetchInvestments: vi.fn(),
  fetchInvestmentSummary: vi.fn(),
  fetchNetWorth: vi.fn(),
  createInvestment: vi.fn(),
  updateInvestment: vi.fn(),
  deleteInvestment: vi.fn(),
  updateSettings: vi.fn(),
}))

vi.mock('swr', async () => {
  const actual = await vi.importActual('swr')
  return { ...(actual as object), mutate: vi.fn() }
})

import { mutate as globalMutate } from 'swr'

function wrapper({ children }: { children: ReactNode }) {
  return <SWRConfig value={{ provider: () => new Map() }}>{children}</SWRConfig>
}

// Las claves que el hook invalida: se evalúa el filtro que le pasa a mutate().
function invalidatedKeys(): (key: unknown) => boolean {
  const filter = vi.mocked(globalMutate).mock.calls.map((c) => c[0]).find((a) => typeof a === 'function')
  return filter as (key: unknown) => boolean
}

const input = {
  asset_type: 'stock' as const,
  name: 'Apple',
  ticker: 'AAPL',
  currency: 'ARS' as const,
  quantity: 10,
  invested_amount: 150000,
  current_value: null,
  interest_rate_tna: null,
  start_date: null,
  maturity_date: null,
  institution: null,
  notes: null,
  notify_maturity: true,
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('lecturas', () => {
  it('useInvestments pide la lista con el filtro de estado', async () => {
    vi.mocked(endpoints.fetchInvestments).mockResolvedValue([])
    const { result } = renderHook(() => useInvestments('closed'), { wrapper })
    await waitFor(() => expect(result.current.data).toEqual([]))
    expect(endpoints.fetchInvestments).toHaveBeenCalledWith({ status: 'closed' })
  })

  it('useNetWorth expone el error sin tirar los datos', async () => {
    vi.mocked(endpoints.fetchNetWorth).mockRejectedValue(new Error('boom'))
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const { result } = renderHook(() => useNetWorth(), { wrapper })
    await waitFor(() => expect(result.current.error).toBeDefined(), { timeout: 5000 })
    expect(result.current.data).toBeUndefined()
    spy.mockRestore()
  })
})

describe('invalidación de caché', () => {
  it('crear revalida lista, resumen, patrimonio y finance/summary', async () => {
    await saveInvestment(null, input)
    expect(endpoints.createInvestment).toHaveBeenCalledWith(input)

    const matches = invalidatedKeys()
    expect(matches(['finance/investments', 'active'])).toBe(true)
    expect(matches(['finance/investments', 'closed'])).toBe(true)
    expect(matches('finance/investments/summary')).toBe(true)
    expect(matches('finance/net-worth')).toBe(true)
    expect(matches('finance/summary')).toBe(true)
    // Lo que no corresponde no se toca.
    expect(matches('finance/accounts')).toBe(false)
    expect(matches('settings')).toBe(false)
    expect(matches(['finance/transactions', '{}'])).toBe(false)
  })

  it('editar usa update y también revalida', async () => {
    await saveInvestment({ id: 'i1' } as never, input)
    expect(endpoints.updateInvestment).toHaveBeenCalledWith('i1', input)
    expect(invalidatedKeys()).toBeTypeOf('function')
  })

  it('cerrar, reabrir y borrar revalidan', async () => {
    await setInvestmentStatus('i1', 'closed')
    expect(endpoints.updateInvestment).toHaveBeenCalledWith('i1', { status: 'closed' })
    await removeInvestment('i1')
    expect(endpoints.deleteInvestment).toHaveBeenCalledWith('i1')
    expect(vi.mocked(globalMutate)).toHaveBeenCalledTimes(2)
  })

  it('cambiar la cotización revalida además settings', async () => {
    await saveInvestmentSettings({ fx_usd_ars: 1450.5 })
    expect(endpoints.updateSettings).toHaveBeenCalledWith({ fx_usd_ars: 1450.5 })
    expect(globalMutate).toHaveBeenCalledWith('settings')
    expect(invalidatedKeys()('finance/net-worth')).toBe(true)
  })

  it('si la API falla no revalida (queda el dato anterior)', async () => {
    vi.mocked(endpoints.createInvestment).mockRejectedValueOnce(new Error('422'))
    await expect(saveInvestment(null, input)).rejects.toThrow('422')
    expect(globalMutate).not.toHaveBeenCalled()
  })
})
