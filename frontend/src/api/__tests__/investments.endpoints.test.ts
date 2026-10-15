import { describe, it, expect, vi, beforeEach } from 'vitest'

const { mockGet, mockPut, mockPost, mockDelete } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPut: vi.fn(),
  mockPost: vi.fn(),
  mockDelete: vi.fn(),
}))

vi.mock('../client', () => ({
  default: { get: mockGet, put: mockPut, post: mockPost, patch: vi.fn(), delete: mockDelete },
}))

import {
  fetchInvestments,
  fetchInvestment,
  fetchInvestmentSummary,
  fetchNetWorth,
  createInvestment,
  updateInvestment,
  deleteInvestment,
  fetchFinanceSummary,
  fetchSettings,
  updateSettings,
} from '../endpoints'
import type { InvestmentInput } from '../../types'

// Minutos al este de UTC, igual que el resto de los resúmenes.
const expectedOffset = -new Date().getTimezoneOffset()

const input: InvestmentInput = {
  asset_type: 'fixed_term',
  name: 'Plazo fijo',
  ticker: null,
  currency: 'ARS',
  quantity: null,
  invested_amount: 1000000,
  current_value: null,
  interest_rate_tna: 30,
  start_date: '2026-10-01',
  maturity_date: '2026-10-31',
  institution: null,
  notes: null,
  notify_maturity: true,
}

const apiInvestment = {
  id: 'i1',
  asset_type: 'fixed_term',
  name: 'Plazo fijo',
  ticker: null,
  currency: 'ARS',
  quantity: '0.00012345',
  invested_amount: '1000000.00',
  current_value: null,
  interest_rate_tna: '30.0000',
  start_date: '2026-10-01',
  maturity_date: '2026-10-31',
  institution: null,
  notes: null,
  status: 'active',
  notify_maturity: true,
  value_updated_at: null,
  effective_value: '1009863.01',
  value_source: 'fixed_term_accrued',
  gain: '9863.01',
  gain_pct: '0.99',
  days_to_maturity: 18,
  is_matured: false,
  fixed_term: {
    term_days: 30,
    interest_total: '24657.53',
    amount_at_maturity: '1024657.53',
    accrued_interest: '9863.01',
    tea_pct: '34.50',
  },
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('inversiones: lecturas', () => {
  it('lista con tz_offset_minutes y status, y pasa los Decimal a number', async () => {
    mockGet.mockResolvedValue({ data: [apiInvestment] })
    const [i] = await fetchInvestments({ status: 'closed' })

    expect(mockGet).toHaveBeenCalledWith('/api/v1/finance/investments', {
      params: { status: 'closed', tz_offset_minutes: expectedOffset },
    })
    expect(i.invested_amount).toBe(1000000)
    expect(i.quantity).toBe(0.00012345)
    expect(i.effective_value).toBe(1009863.01)
    expect(i.gain_pct).toBe(0.99)
    expect(i.current_value).toBeNull()
    expect(i.fixed_term?.amount_at_maturity).toBe(1024657.53)
  })

  it('filtra por tipo', async () => {
    mockGet.mockResolvedValue({ data: [] })
    await fetchInvestments({ status: 'all', asset_type: 'crypto' })
    expect(mockGet).toHaveBeenCalledWith('/api/v1/finance/investments', {
      params: { status: 'all', asset_type: 'crypto', tz_offset_minutes: expectedOffset },
    })
  })

  it('detalle', async () => {
    mockGet.mockResolvedValue({ data: apiInvestment })
    const i = await fetchInvestment('i1')
    expect(mockGet).toHaveBeenCalledWith('/api/v1/finance/investments/i1', {
      params: { tz_offset_minutes: expectedOffset },
    })
    expect(i.effective_value).toBe(1009863.01)
  })

  it('resumen: null sigue siendo null (no 0)', async () => {
    mockGet.mockResolvedValue({
      data: {
        by_currency: [{ currency: 'USD', invested: '1800.00', current_value: '2000.00', gain: '200.00', count: 1 }],
        by_type: [{ asset_type: 'fx', count: 1, value_ars: null }],
        total_ars: null,
        total_usd: '2000.00',
        missing_rates: ['USD'],
        count_active: 1,
        upcoming_maturities: [],
      },
    })
    const s = await fetchInvestmentSummary()
    expect(mockGet).toHaveBeenCalledWith('/api/v1/finance/investments/summary', {
      params: { tz_offset_minutes: expectedOffset },
    })
    expect(s.total_ars).toBeNull()
    expect(s.total_usd).toBe(2000)
    expect(s.by_currency[0].current_value).toBe(2000)
    expect(s.by_type[0].value_ars).toBeNull()
  })

  it('patrimonio: desglose en ARS y USD', async () => {
    mockGet.mockResolvedValue({
      data: {
        cash_balance_ars: '100000.00',
        cash_balance_usd: '68.94',
        investments: {
          by_currency: [],
          by_type: [],
          total_ars: '3401000.00',
          total_usd: '2344.71',
          missing_rates: [],
          count_active: 2,
          upcoming_maturities: [],
        },
        net_worth_ars: '3501000.00',
        net_worth_usd: '2413.65',
        rates: { usd_ars: '1450.5000', eur_ars: null, updated_at: '2026-10-10T12:00:00Z' },
        missing_rates: [],
        include_investments_in_balance: true,
      },
    })
    const n = await fetchNetWorth()
    expect(mockGet).toHaveBeenCalledWith('/api/v1/finance/net-worth', {
      params: { tz_offset_minutes: expectedOffset },
    })
    expect(n.cash_balance_ars).toBe(100000)
    expect(n.cash_balance_usd).toBe(68.94)
    expect(n.investments.total_ars).toBe(3401000)
    expect(n.net_worth_ars).toBe(3501000)
    expect(n.net_worth_usd).toBe(2413.65)
    expect(n.rates.usd_ars).toBe(1450.5)
    expect(n.rates.eur_ars).toBeNull()
  })
})

describe('inversiones: escrituras', () => {
  it('crear manda timezone_offset_minutes', async () => {
    mockPost.mockResolvedValue({ data: apiInvestment })
    await createInvestment(input)
    expect(mockPost).toHaveBeenCalledWith('/api/v1/finance/investments', {
      ...input,
      timezone_offset_minutes: expectedOffset,
    })
  })

  it('editar manda timezone_offset_minutes y conserva los null para borrar campos', async () => {
    mockPut.mockResolvedValue({ data: apiInvestment })
    await updateInvestment('i1', { ...input, current_value: null })
    const [url, body] = mockPut.mock.calls[0]
    expect(url).toBe('/api/v1/finance/investments/i1')
    expect(body).toMatchObject({ current_value: null, timezone_offset_minutes: expectedOffset })
  })

  it('cerrar solo manda el status (y el offset)', async () => {
    mockPut.mockResolvedValue({ data: { ...apiInvestment, status: 'closed' } })
    await updateInvestment('i1', { status: 'closed' })
    expect(mockPut).toHaveBeenCalledWith('/api/v1/finance/investments/i1', {
      status: 'closed',
      timezone_offset_minutes: expectedOffset,
    })
  })

  it('borrar', async () => {
    mockDelete.mockResolvedValue({})
    await deleteInvestment('i1')
    expect(mockDelete).toHaveBeenCalledWith('/api/v1/finance/investments/i1')
  })

  it('un error de la API se propaga (SWR conserva los datos previos)', async () => {
    mockPost.mockRejectedValue(new Error('422'))
    await expect(createInvestment(input)).rejects.toThrow('422')
  })
})

describe('resumen de Finanzas con inversiones', () => {
  it('manda tz_offset_minutes y mapea los campos aditivos', async () => {
    mockGet.mockResolvedValue({
      data: {
        total_income: '1000.00',
        total_expenses: '400.00',
        balance: '600.00',
        investments_value_ars: null,
        net_worth_ars: null,
        investments_missing_rates: ['USD'],
        include_investments_in_balance: true,
      },
    })
    const s = await fetchFinanceSummary()
    expect(mockGet).toHaveBeenCalledWith('/api/v1/finance/summary', {
      params: { tz_offset_minutes: expectedOffset },
    })
    expect(s.balance).toBe(600)
    expect(s.investments_value_ars).toBeNull()
    expect(s.net_worth_ars).toBeNull()
    expect(s.investments_missing_rates).toEqual(['USD'])
    expect(s.include_investments_in_balance).toBe(true)
  })

  it('con un server viejo (sin los campos nuevos) no los inventa', async () => {
    mockGet.mockResolvedValue({
      data: { total_income: '1', total_expenses: '1', balance: '0' },
    })
    const s = await fetchFinanceSummary()
    expect('net_worth_ars' in s).toBe(false)
    expect('include_investments_in_balance' in s).toBe(false)
  })

  it('suma números reales', async () => {
    mockGet.mockResolvedValue({
      data: {
        total_income: '1000.00',
        total_expenses: '400.00',
        balance: '600.00',
        investments_value_ars: '500000.00',
        net_worth_ars: '500600.00',
        investments_missing_rates: [],
        include_investments_in_balance: false,
      },
    })
    const s = await fetchFinanceSummary()
    expect(s.net_worth_ars).toBe(500600)
  })
})

describe('ajustes: cotizaciones', () => {
  it('lee las cotizaciones como number y conserva null', async () => {
    mockGet.mockResolvedValue({
      data: {
        currency: 'ARS',
        theme_color: 'violet',
        date_format: 'DD/MM/YYYY',
        google_calendar_id: 'primary',
        google_connected: false,
        fx_usd_ars: '1450.5000',
        fx_eur_ars: null,
        fx_rates_updated_at: '2026-10-10T12:00:00Z',
        include_investments_in_balance: true,
      },
    })
    const s = await fetchSettings()
    expect(s.fx_usd_ars).toBe(1450.5)
    expect(s.fx_eur_ars).toBeNull()
    expect(s.include_investments_in_balance).toBe(true)
  })

  it('guarda la cotización (null la borra)', async () => {
    mockPut.mockResolvedValue({
      data: { currency: 'ARS', theme_color: 'violet', date_format: 'x', google_calendar_id: 'p', google_connected: false, fx_usd_ars: '1500.0000', fx_eur_ars: null },
    })
    const s = await updateSettings({ fx_usd_ars: 1500, fx_eur_ars: null })
    expect(mockPut).toHaveBeenCalledWith('/api/v1/settings', { fx_usd_ars: 1500, fx_eur_ars: null })
    expect(s.fx_usd_ars).toBe(1500)
  })
})
