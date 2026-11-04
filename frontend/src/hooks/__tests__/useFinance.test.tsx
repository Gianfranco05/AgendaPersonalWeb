import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { SWRConfig } from 'swr'
import { type ReactNode } from 'react'
import { useFinanceSummary, useTransactions, saveTransaction, removeTransaction } from '../useFinance'
import * as endpoints from '../../api/endpoints'

vi.mock('../../api/endpoints', () => ({
  fetchFinanceSummary: vi.fn(),
  fetchTransactions: vi.fn(),
  fetchCategories: vi.fn(),
  createTransaction: vi.fn(),
  updateTransaction: vi.fn(),
  deleteTransaction: vi.fn(),
}))

vi.mock('swr', async () => {
  const actual = await vi.importActual('swr')
  return { ...actual as object, mutate: vi.fn() }
})

import { mutate as globalMutate } from 'swr'

const mockSummary = {
  total_income: 1250000,
  total_expense: 870000,
  balance: 380000,
  currency: 'ARS',
}

const mockTxResponse = {
  items: [
    { id: '1', amount: 100, type: 'expense' as const, product_name: 'Test', transaction_date: '2025-06-01', currency: 'ARS', merchant_name: 'Store', payment_method: 'Cash' },
  ],
  total: 1,
  page: 1,
  page_size: 20,
}

function createWrapper(fallback: Record<string, unknown> = {}) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <SWRConfig value={{ provider: () => new Map(), fallback }}>
        {children}
      </SWRConfig>
    )
  }
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('useFinanceSummary', () => {
  it('returns cached summary data via SWR fallback', async () => {
    const { result } = renderHook(
      () => useFinanceSummary(),
      { wrapper: createWrapper({ 'finance/summary': mockSummary }) },
    )
    await waitFor(() => expect(result.current.data).toEqual(mockSummary))
  })
})

describe('useTransactions', () => {
  it('fetches transactions via API endpoint', async () => {
    vi.mocked(endpoints.fetchTransactions).mockResolvedValue(mockTxResponse)
    const { result } = renderHook(
      () => useTransactions({ page: 1, per_page: 20 }),
      { wrapper: createWrapper() },
    )
    await waitFor(() => expect(result.current.data).toEqual(mockTxResponse))
    expect(endpoints.fetchTransactions).toHaveBeenCalledWith({ page: 1, per_page: 20 })
  })
})

describe('saveTransaction', () => {
  it('calls createTransaction for new records and invalidates', async () => {
    const data = { amount: 100, type: 'expense' as const, product_name: 'Test', transaction_date: '2025-06-01', currency: 'ARS' as const, merchant_name: '', payment_method: 'cash', category_id: '' }
    await saveTransaction(null, data, { page: 1, per_page: 20 })
    expect(endpoints.createTransaction).toHaveBeenCalledWith(data)
    expect(globalMutate).toHaveBeenCalled()
  })

  it('calls updateTransaction for existing records and invalidates', async () => {
    const existing = { id: '1', amount: 50, type: 'income' as const, product_name: 'Old', transaction_date: '2025-05-01', currency: 'ARS' as const, merchant_name: '', payment_method: 'cash', category_id: '' }
    const updates = { amount: 200, type: 'income' as const, product_name: 'Updated', transaction_date: '2025-06-01', currency: 'ARS' as const, merchant_name: '', payment_method: 'transfer', category_id: '' }
    await saveTransaction(existing, updates, { page: 1, per_page: 20 })
    expect(endpoints.updateTransaction).toHaveBeenCalledWith('1', updates)
    expect(globalMutate).toHaveBeenCalled()
  })
})

describe('removeTransaction', () => {
  it('calls deleteTransaction and invalidates caches', async () => {
    await removeTransaction('1', { page: 1, per_page: 20 })
    expect(endpoints.deleteTransaction).toHaveBeenCalledWith('1')
    expect(globalMutate).toHaveBeenCalled()
  })
})
