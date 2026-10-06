import { describe, it, expect, vi, beforeEach } from 'vitest'

const { mockGet, mockPut, mockPost, mockPatch } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPut: vi.fn(),
  mockPost: vi.fn(),
  mockPatch: vi.fn(),
}))

vi.mock('../client', () => ({
  default: { get: mockGet, put: mockPut, post: mockPost, patch: mockPatch, delete: vi.fn() },
}))

import {
  fetchFinanceSummary,
  fetchTransactions,
  fetchBudgets,
  fetchFinanceReports,
  fetchBankAccounts,
  createNote,
  fetchTags,
  createReminder,
  updateReminder,
} from '../endpoints'

beforeEach(() => {
  vi.clearAllMocks()
})

// La API serializa los Decimal como string: si llegan así a la UI, los montos
// no se formatean ("$50000.00" en vez de "$50.000").
describe('finanzas: Decimal de la API a number', () => {
  it('summary', async () => {
    mockGet.mockResolvedValue({
      data: { total_income: '50000.00', total_expenses: '1600.00', balance: '48400.00' },
    })
    expect(await fetchFinanceSummary()).toEqual({
      total_income: 50000,
      total_expenses: 1600,
      balance: 48400,
    })
  })

  it('transacciones', async () => {
    mockGet.mockResolvedValue({
      data: { items: [{ id: '1', amount: '1500.50' }], total: 1, page: 1, page_size: 20 },
    })
    const res = await fetchTransactions({ page: 1 })
    expect(res.items[0].amount).toBe(1500.5)
  })

  it('presupuestos', async () => {
    mockGet.mockResolvedValue({
      data: [{ id: 'b', amount: '10000.00', spent: '1600.00', remaining: '8400.00', percentage: 16 }],
    })
    const [b] = await fetchBudgets(2026, 10)
    expect([b.amount, b.spent, b.remaining, b.percentage]).toEqual([10000, 1600, 8400, 16])
  })

  it('reportes', async () => {
    mockGet.mockResolvedValue({
      data: {
        by_category: [{ name: 'Comida', color: '#fff', total: '1600.00' }],
        monthly: [{ month: '2026-10-01', income: '50000.00', expense: '1600.00' }],
        total_expenses: '1600.00',
      },
    })
    const r = await fetchFinanceReports()
    expect(r.by_category[0].total).toBe(1600)
    expect(r.monthly[0]).toMatchObject({ income: 50000, expense: 1600 })
    expect(r.total_expenses).toBe(1600)
  })

  it('cuentas', async () => {
    mockGet.mockResolvedValue({ data: [{ id: 'a', balance: '1000.00' }] })
    expect((await fetchBankAccounts())[0].balance).toBe(1000)
  })
})

describe('notas', () => {
  const draft = {
    title: 'n',
    content: 'c',
    color: '#fff',
    is_pinned: true,
    is_archived: false,
    tags: [],
  }

  it('fija la nota con un PUT si el POST ignoró is_pinned', async () => {
    mockPost.mockResolvedValue({ data: { id: 'n1', is_pinned: false } })
    mockPut.mockResolvedValue({ data: { id: 'n1', is_pinned: true } })
    const note = await createNote(draft)
    expect(mockPut).toHaveBeenCalledWith('/api/v1/notes/n1', { is_pinned: true })
    expect(note.is_pinned).toBe(true)
  })

  it('no hace el PUT extra si la API ya la devolvió fijada o no se pidió fijar', async () => {
    mockPost.mockResolvedValue({ data: { id: 'n1', is_pinned: true } })
    await createNote(draft)
    mockPost.mockResolvedValue({ data: { id: 'n2', is_pinned: false } })
    await createNote({ ...draft, is_pinned: false })
    expect(mockPut).not.toHaveBeenCalled()
  })

  it('los tags se piden a /notes/tags', async () => {
    mockGet.mockResolvedValue({ data: [] })
    await fetchTags()
    expect(mockGet).toHaveBeenCalledWith('/api/v1/notes/tags')
  })
})

describe('recordatorios: zona horaria para la push del servidor', () => {
  const expected = -new Date().getTimezoneOffset()

  it('al crear manda timezone_offset_minutes', async () => {
    mockPost.mockResolvedValue({ data: { id: 'r1' } })
    await createReminder({ message: 'm', icon: '🔔', hour: 21, minute: 30, enabled: true })
    expect(mockPost).toHaveBeenCalledWith(
      '/api/v1/reminders',
      expect.objectContaining({ hour: 21, timezone_offset_minutes: expected }),
    )
  })

  it('al cambiar la hora lo actualiza, pero no al prender o apagar', async () => {
    mockPatch.mockResolvedValue({ data: { id: 'r1' } })
    await updateReminder('r1', { hour: 8, minute: 0 })
    expect(mockPatch).toHaveBeenLastCalledWith(
      '/api/v1/reminders/r1',
      expect.objectContaining({ timezone_offset_minutes: expected }),
    )
    await updateReminder('r1', { enabled: false })
    expect(mockPatch).toHaveBeenLastCalledWith('/api/v1/reminders/r1', { enabled: false })
  })
})
