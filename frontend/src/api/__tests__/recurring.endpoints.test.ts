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
  fetchRecurring,
  fetchRecurringOne,
  createRecurring,
  updateRecurring,
  deleteRecurring,
  pauseRecurring,
  resumeRecurring,
  previewRecurring,
  fetchUpcomingRecurring,
  fetchOccurrences,
  confirmOccurrence,
  skipOccurrence,
  renewInvestment,
  fetchRenewals,
  fetchTransactions,
} from '../endpoints'
import type { RecurringInput } from '../../types'

// Minutos al este de UTC, igual que el resto de los resúmenes.
const expectedOffset = -new Date().getTimezoneOffset()
const BASE = '/api/v1/finance/recurring'

const input: RecurringInput = {
  type: 'income',
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
  frequency: 'monthly',
  interval_count: 1,
  weekday: null,
  day_of_month: 5,
  month_of_year: null,
  start_date: '2026-11-01',
  end_date: null,
  requires_confirmation: false,
  notify: true,
}

const apiRecurring = {
  id: 'r1',
  ...input,
  amount: '850000.00',
  anchor_date: '2026-11-05',
  next_occurrence_date: '2026-11-05',
  last_occurrence_date: null,
  status: 'active',
  state: 'active',
  rule_label: 'Todos los meses el día 5',
  pending_count: 1,
  last_amount: '840000.00',
  timezone_offset_minutes: -180,
}

const apiOccurrence = {
  id: 'o1',
  recurrence_id: 'r1',
  occurrence_date: '2026-11-05',
  status: 'pending',
  suggested_amount: '25000.00',
  transaction_id: null,
  resolved_at: null,
  name: 'Luz',
  type: 'expense',
  currency: 'ARS',
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('recurrentes: lecturas', () => {
  it('lista con status y tz_offset_minutes, y pasa los Decimal a number', async () => {
    mockGet.mockResolvedValue({ data: [apiRecurring] })
    const [r] = await fetchRecurring('active')
    expect(mockGet).toHaveBeenCalledWith(BASE, {
      params: { status: 'active', tz_offset_minutes: expectedOffset },
    })
    expect(r.amount).toBe(850000)
    expect(r.last_amount).toBe(840000)
    expect(r.rule_label).toBe('Todos los meses el día 5')
  })

  it('monto variable: amount null sigue siendo null (no 0)', async () => {
    mockGet.mockResolvedValue({ data: [{ ...apiRecurring, amount: null, last_amount: null }] })
    const [r] = await fetchRecurring()
    expect(r.amount).toBeNull()
    expect(r.last_amount).toBeNull()
    expect(mockGet).toHaveBeenCalledWith(BASE, {
      params: { status: 'all', tz_offset_minutes: expectedOffset },
    })
  })

  it('detalle con ocurrencias recientes', async () => {
    mockGet.mockResolvedValue({
      data: { ...apiRecurring, recent_occurrences: [apiOccurrence], next_dates: ['2026-12-05'] },
    })
    const d = await fetchRecurringOne('r1')
    expect(mockGet).toHaveBeenCalledWith(`${BASE}/r1`, { params: { tz_offset_minutes: expectedOffset } })
    expect(d.recent_occurrences[0].suggested_amount).toBe(25000)
    expect(d.next_dates).toEqual(['2026-12-05'])
  })

  it('próximos movimientos: días y offset, totales como number', async () => {
    mockGet.mockResolvedValue({
      data: {
        days: 30,
        items: [
          { recurrence_id: 'r1', date: '2026-11-05', name: 'Sueldo', type: 'income', amount: '850000.00', currency: 'ARS', requires_confirmation: false },
          { recurrence_id: 'r2', date: '2026-11-10', name: 'Luz', type: 'expense', amount: null, currency: 'ARS', requires_confirmation: true },
        ],
        totals: [{ type: 'income', currency: 'ARS', total: '850000.00' }],
      },
    })
    const u = await fetchUpcomingRecurring()
    expect(mockGet).toHaveBeenCalledWith(`${BASE}/upcoming`, {
      params: { days: 30, tz_offset_minutes: expectedOffset },
    })
    expect(u.items[0].amount).toBe(850000)
    expect(u.items[1].amount).toBeNull()
    expect(u.totals[0].total).toBe(850000)
  })

  it('pendientes', async () => {
    mockGet.mockResolvedValue({ data: [apiOccurrence] })
    const [o] = await fetchOccurrences()
    expect(mockGet).toHaveBeenCalledWith(`${BASE}/occurrences`, { params: { status: 'pending' } })
    expect(o.suggested_amount).toBe(25000)
  })

  it('transacciones: filtro recurrence_id', async () => {
    mockGet.mockResolvedValue({ data: { items: [], total: 0, page: 1, page_size: 20 } })
    await fetchTransactions({ page: 1, per_page: 20, recurrence_id: 'r1' })
    expect(mockGet).toHaveBeenCalledWith('/api/v1/finance/transactions', {
      params: { skip: 0, limit: 20, recurrence_id: 'r1' },
    })
    await fetchTransactions({ page: 1, per_page: 20 })
    expect(mockGet.mock.calls[1][1].params).not.toHaveProperty('recurrence_id')
  })
})

describe('recurrentes: escrituras', () => {
  it('crear manda timezone_offset_minutes', async () => {
    mockPost.mockResolvedValue({ data: apiRecurring })
    await createRecurring({ ...input, generate_past: true })
    expect(mockPost).toHaveBeenCalledWith(BASE, {
      ...input,
      generate_past: true,
      timezone_offset_minutes: expectedOffset,
    })
  })

  it('editar manda timezone_offset_minutes y conserva los null', async () => {
    mockPut.mockResolvedValue({ data: apiRecurring })
    await updateRecurring('r1', { end_date: null, amount: 900000 })
    expect(mockPut).toHaveBeenCalledWith(`${BASE}/r1`, {
      end_date: null,
      amount: 900000,
      timezone_offset_minutes: expectedOffset,
    })
  })

  it('pausar y reanudar mandan el offset', async () => {
    mockPost.mockResolvedValue({ data: apiRecurring })
    await pauseRecurring('r1')
    await resumeRecurring('r1')
    expect(mockPost).toHaveBeenNthCalledWith(1, `${BASE}/r1/pause`, { timezone_offset_minutes: expectedOffset })
    expect(mockPost).toHaveBeenNthCalledWith(2, `${BASE}/r1/resume`, { timezone_offset_minutes: expectedOffset })
  })

  it('borrar', async () => {
    mockDelete.mockResolvedValue({})
    await deleteRecurring('r1')
    expect(mockDelete).toHaveBeenCalledWith(`${BASE}/r1`)
  })

  it('vista previa: POST con tz_offset_minutes', async () => {
    mockPost.mockResolvedValue({ data: { anchor_date: '2027-01-31', dates: ['2027-01-31', '2027-02-28'] } })
    const res = await previewRecurring({
      frequency: 'monthly',
      interval_count: 1,
      weekday: null,
      day_of_month: 31,
      month_of_year: null,
      start_date: '2027-01-31',
      end_date: null,
    })
    expect(mockPost).toHaveBeenCalledWith(`${BASE}/preview`, {
      frequency: 'monthly',
      interval_count: 1,
      weekday: null,
      day_of_month: 31,
      month_of_year: null,
      start_date: '2027-01-31',
      end_date: null,
      generate_past: false,
      tz_offset_minutes: expectedOffset,
    })
    expect(res.dates).toEqual(['2027-01-31', '2027-02-28'])
  })

  it('confirmar y saltear mandan el offset', async () => {
    mockPost.mockResolvedValue({ data: { ...apiOccurrence, status: 'confirmed' } })
    const o = await confirmOccurrence('o1', { amount: 31250.5, transaction_date: '2026-11-05' })
    expect(mockPost).toHaveBeenCalledWith(`${BASE}/occurrences/o1/confirm`, {
      amount: 31250.5,
      transaction_date: '2026-11-05',
      timezone_offset_minutes: expectedOffset,
    })
    expect(o.status).toBe('confirmed')
    await skipOccurrence('o1')
    expect(mockPost).toHaveBeenLastCalledWith(`${BASE}/occurrences/o1/skip`, {
      timezone_offset_minutes: expectedOffset,
    })
  })
})

describe('renovación de plazo fijo', () => {
  const apiInvestment = {
    id: 'i1',
    asset_type: 'fixed_term',
    name: 'PF',
    ticker: null,
    currency: 'ARS',
    quantity: null,
    invested_amount: '1024657.53',
    current_value: null,
    interest_rate_tna: '28.0000',
    start_date: '2026-10-26',
    maturity_date: '2026-11-25',
    institution: null,
    notes: null,
    status: 'active',
    notify_maturity: true,
    value_updated_at: null,
    effective_value: '1024657.53',
    value_source: 'invested',
    gain: '0.00',
    gain_pct: '0.00',
    days_to_maturity: 30,
    is_matured: false,
    fixed_term: null,
    renewed_from_id: 'i0',
    renewed_to_id: null,
    can_renew: false,
  }

  it('renovar manda el offset y convierte ambos plazos fijos', async () => {
    mockPost.mockResolvedValue({
      data: {
        closed: { ...apiInvestment, id: 'i0', status: 'closed', current_value: '1024657.53', renewed_to_id: 'i1' },
        renewed: apiInvestment,
        interest_transaction_id: null,
      },
    })
    const res = await renewInvestment('i0', {
      mode: 'principal_and_interest',
      interest_rate_tna: 28,
      term_days: 30,
    })
    expect(mockPost).toHaveBeenCalledWith('/api/v1/finance/investments/i0/renew', {
      mode: 'principal_and_interest',
      interest_rate_tna: 28,
      term_days: 30,
      timezone_offset_minutes: expectedOffset,
    })
    expect(res.closed.current_value).toBe(1024657.53)
    expect(res.renewed.invested_amount).toBe(1024657.53)
    expect(res.renewed.renewed_from_id).toBe('i0')
  })

  it('historial de renovaciones: Decimal a number', async () => {
    mockGet.mockResolvedValue({
      data: {
        items: [
          {
            id: 'i0', name: 'PF', status: 'closed', start_date: '2026-09-26', maturity_date: '2026-10-26',
            term_days: 30, invested_amount: '1000000.00', interest_rate_tna: '30.0000',
            amount_at_maturity: '1024657.53', interest: '24657.53', renewed_from_id: null,
          },
        ],
        accumulated_interest: '24657.53',
        currency: 'ARS',
      },
    })
    const chain = await fetchRenewals('i0')
    expect(mockGet).toHaveBeenCalledWith('/api/v1/finance/investments/i0/renewals')
    expect(chain.accumulated_interest).toBe(24657.53)
    expect(chain.items[0].interest).toBe(24657.53)
    expect(chain.items[0].invested_amount).toBe(1000000)
  })
})
