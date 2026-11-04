import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'

vi.mock('../../../hooks/useFinance', () => ({
  useFinanceSummary: vi.fn(),
  useTransactions: vi.fn(),
  removeTransaction: vi.fn(),
}))

vi.mock('../../../hooks/useRecurring', () => ({
  usePendingOccurrences: vi.fn(() => ({ data: [] })),
}))
vi.mock('../RecurringSection', () => ({ default: () => <div>RecurringSection</div> }))
vi.mock('../TransactionTable', () => ({
  default: ({ onDelete }: { onDelete: (id: string) => void }) => (
    <button onClick={() => onDelete('tx1')}>borrar-tx</button>
  ),
}))
vi.mock('../TransactionFilters', () => ({ default: () => <div>TransactionFilters</div> }))
vi.mock('../FinanceCharts', () => ({ default: () => <div>FinanceCharts</div> }))

import { useFinanceSummary, useTransactions, removeTransaction } from '../../../hooks/useFinance'
import { usePendingOccurrences } from '../../../hooks/useRecurring'
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

  describe('recurrentes', () => {
    const loaded = () => {
      vi.mocked(useFinanceSummary).mockReturnValue({ data: undefined, isLoading: false, error: undefined, isValidating: false, mutate: vi.fn() })
      vi.mocked(useTransactions).mockReturnValue({ data: { items: [], total: 0, page: 1, page_size: 20 }, isLoading: false, error: undefined, isValidating: false, mutate: vi.fn() })
    }

    it('tiene la pestaña Recurrentes', () => {
      loaded()
      renderWithProviders(<FinancePage />)
      fireEvent.click(screen.getByText('Recurrentes'))
      expect(screen.getByText('RecurringSection')).toBeInTheDocument()
    })

    it('sin pendientes no hay banner', () => {
      loaded()
      renderWithProviders(<FinancePage />)
      expect(screen.queryByTestId('pending-banner')).not.toBeInTheDocument()
    })

    it('con pendientes muestra el banner y lleva a Recurrentes', () => {
      loaded()
      vi.mocked(usePendingOccurrences).mockReturnValue({ data: [{ id: 'o1' }, { id: 'o2' }] } as never)
      renderWithProviders(<FinancePage />)
      const banner = screen.getByTestId('pending-banner')
      expect(banner).toHaveTextContent('Tenés 2 movimientos recurrentes para confirmar')
      fireEvent.click(banner)
      expect(screen.getByText('RecurringSection')).toBeInTheDocument()
    })
  })
})
