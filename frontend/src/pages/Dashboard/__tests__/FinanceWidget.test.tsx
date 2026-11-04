import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'
import FinanceWidget from '../FinanceWidget'

vi.mock('../../../api/endpoints', () => ({
  fetchFinanceSummary: vi.fn(),
  fetchTransactions: vi.fn(),
}))

import { fetchFinanceSummary, fetchTransactions } from '../../../api/endpoints'

const mockSummary = {
  total_income: 1250000,
  total_expenses: 870000,
  balance: 380000,
}

const mockTransactions = {
  items: [
    { id: '1', amount: 50000, type: 'income' as const, product_name: 'Freelance', transaction_date: '2025-06-28', currency: 'ARS', merchant_name: 'Cliente', payment_method: 'Transferencia' },
    { id: '2', amount: 15000, type: 'expense' as const, product_name: 'Supermercado', transaction_date: '2025-06-27', currency: 'ARS', merchant_name: 'Coto', payment_method: 'Tarjeta' },
  ],
  total: 2,
  page: 1,
  page_size: 5,
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('FinanceWidget', () => {
  it('shows loading skeleton while loading', () => {
    vi.mocked(fetchFinanceSummary).mockReturnValue(new Promise(() => {}))
    vi.mocked(fetchTransactions).mockReturnValue(new Promise(() => {}))
    const { container } = renderWithProviders(<FinanceWidget />)
    const skeletons = container.querySelectorAll('.skeleton-shimmer')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('displays summary with formatted values', async () => {
    vi.mocked(fetchFinanceSummary).mockResolvedValue(mockSummary)
    vi.mocked(fetchTransactions).mockResolvedValue(mockTransactions)

    renderWithProviders(<FinanceWidget />)

    await waitFor(() => {
      expect(screen.getByText('Finanzas')).toBeInTheDocument()
    })
    expect(screen.getByText(/Ingresos/)).toBeInTheDocument()
    expect(screen.getByText(/Egresos/)).toBeInTheDocument()
    expect(screen.getByText(/Freelance/)).toBeInTheDocument()
    expect(screen.getByText(/Supermercado/)).toBeInTheDocument()
  })

  describe('Sumar inversiones al balance', () => {
    const withInvestments = {
      ...mockSummary,
      investments_value_ars: 500000,
      net_worth_ars: 880000,
      investments_missing_rates: [],
    }

    it('apagado muestra solo el balance de efectivo, como siempre', async () => {
      vi.mocked(fetchFinanceSummary).mockResolvedValue({ ...withInvestments, include_investments_in_balance: false })
      vi.mocked(fetchTransactions).mockResolvedValue(mockTransactions)
      renderWithProviders(<FinanceWidget />)

      await waitFor(() => expect(screen.getByText('Balance actual')).toBeInTheDocument())
      expect(screen.getByText('+$380.000')).toBeInTheDocument()
      expect(screen.queryByTestId('net-worth-block')).not.toBeInTheDocument()
      expect(screen.queryByText('Balance + inversiones')).not.toBeInTheDocument()
    })

    it('un server sin los campos nuevos se ve igual que apagado', async () => {
      vi.mocked(fetchFinanceSummary).mockResolvedValue(mockSummary)
      vi.mocked(fetchTransactions).mockResolvedValue(mockTransactions)
      renderWithProviders(<FinanceWidget />)
      await waitFor(() => expect(screen.getByText('Balance actual')).toBeInTheDocument())
    })

    it('encendido muestra efectivo + inversiones con tramos diferenciados', async () => {
      vi.mocked(fetchFinanceSummary).mockResolvedValue({ ...withInvestments, include_investments_in_balance: true })
      vi.mocked(fetchTransactions).mockResolvedValue(mockTransactions)
      renderWithProviders(<FinanceWidget />)

      const block = await screen.findByTestId('net-worth-block')
      expect(block).toHaveTextContent('Balance + inversiones')
      expect(block).toHaveTextContent('$ 880.000,00')
      expect(block).toHaveTextContent('Efectivo $ 380.000,00')
      expect(block).toHaveTextContent('Inversiones $ 500.000,00')
      const bar = screen.getByRole('img', { name: 'Efectivo e inversiones' })
      expect(bar.innerHTML).toContain('bg-sky-500')
      expect(screen.queryByText('Balance actual')).not.toBeInTheDocument()
    })

    it('encendido pero sin cotización muestra el efectivo y el aviso', async () => {
      vi.mocked(fetchFinanceSummary).mockResolvedValue({
        ...mockSummary,
        investments_value_ars: null,
        net_worth_ars: null,
        investments_missing_rates: ['USD'],
        include_investments_in_balance: true,
      })
      vi.mocked(fetchTransactions).mockResolvedValue(mockTransactions)
      renderWithProviders(<FinanceWidget />)

      await waitFor(() => expect(screen.getByText('Balance actual')).toBeInTheDocument())
      expect(screen.getByText('+$380.000')).toBeInTheDocument()
      expect(screen.getByRole('status')).toHaveTextContent('Cargá la cotización del dólar')
      expect(screen.queryByTestId('net-worth-block')).not.toBeInTheDocument()
    })
  })
})
