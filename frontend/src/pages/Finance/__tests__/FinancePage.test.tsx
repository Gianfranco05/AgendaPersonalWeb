import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'

vi.mock('../../../hooks/useFinance', () => ({
  useFinanceSummary: vi.fn(),
  useTransactions: vi.fn(),
  removeTransaction: vi.fn(),
}))

vi.mock('../TransactionTable', () => ({
  default: ({ onDelete }: { onDelete: (id: string) => void }) => (
    <button onClick={() => onDelete('tx1')}>borrar-tx</button>
  ),
}))
vi.mock('../TransactionFilters', () => ({ default: () => <div>TransactionFilters</div> }))
vi.mock('../FinanceCharts', () => ({ default: () => <div>FinanceCharts</div> }))

import { useFinanceSummary, useTransactions, removeTransaction } from '../../../hooks/useFinance'
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

  it('pide confirmación antes de borrar una transacción', () => {
    vi.mocked(useFinanceSummary).mockReturnValue({ data: undefined, isLoading: false, error: undefined, isValidating: false, mutate: vi.fn() })
    vi.mocked(useTransactions).mockReturnValue({ data: { items: [], total: 0, page: 1, page_size: 20 }, isLoading: false, error: undefined, isValidating: false, mutate: vi.fn() })
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderWithProviders(<FinancePage />)

    fireEvent.click(screen.getByText('borrar-tx'))
    expect(removeTransaction).not.toHaveBeenCalled()

    confirm.mockReturnValue(true)
    fireEvent.click(screen.getByText('borrar-tx'))
    expect(removeTransaction).toHaveBeenCalledWith('tx1', expect.objectContaining({ page: 1 }))
    confirm.mockRestore()
  })

  it('muestra el balance negativo como -$1.000', () => {
    vi.mocked(useFinanceSummary).mockReturnValue({ data: { total_income: 0, total_expenses: 1000, balance: -1000 }, isLoading: false, error: undefined, isValidating: false, mutate: vi.fn() })
    vi.mocked(useTransactions).mockReturnValue({ data: undefined, isLoading: true, error: undefined, isValidating: false, mutate: vi.fn() })
    renderWithProviders(<FinancePage />)
    expect(screen.getByText('-$1.000')).toBeInTheDocument()
  })
})
