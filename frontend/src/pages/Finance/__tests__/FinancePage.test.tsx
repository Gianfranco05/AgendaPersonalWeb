import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'

vi.mock('../../../hooks/useFinance', () => ({
  useFinanceSummary: vi.fn(),
  useTransactions: vi.fn(),
  removeTransaction: vi.fn(),
}))

vi.mock('../TransactionTable', () => ({ default: () => <div>TransactionTable</div> }))
vi.mock('../TransactionFilters', () => ({ default: () => <div>TransactionFilters</div> }))
vi.mock('../FinanceCharts', () => ({ default: () => <div>FinanceCharts</div> }))

import { useFinanceSummary, useTransactions } from '../../../hooks/useFinance'
import FinancePage from '../FinancePage'

beforeEach(() => {
  vi.clearAllMocks()
})

describe('FinancePage', () => {
  it('renders title and new transaction button', () => {
    vi.mocked(useFinanceSummary).mockReturnValue({ data: undefined, isLoading: true, error: undefined, isValidating: false, mutate: vi.fn() })
    vi.mocked(useTransactions).mockReturnValue({ data: undefined, isLoading: true, error: undefined, isValidating: false, mutate: vi.fn() })
    renderWithProviders(<FinancePage />)
    expect(screen.getByText('Finanzas')).toBeInTheDocument()
    expect(screen.getByText('Nueva transacción')).toBeInTheDocument()
  })
})
