import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'
import TransactionModal from '../TransactionModal'

vi.mock('../../../hooks/useFinance', () => ({
  useCategories: vi.fn(() => ({ data: [] })),
  saveTransaction: vi.fn(),
}))

const defaultProps = {
  txParams: { page: 1, per_page: 20 } as const,
  onClose: vi.fn(),
  onSaved: vi.fn(),
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('TransactionModal', () => {
  it('shows "Nueva transacción" title in create mode', () => {
    renderWithProviders(<TransactionModal transaction={null} {...defaultProps} />)
    expect(screen.getByText('Nueva transacción')).toBeInTheDocument()
  })

  it('pre-fills form fields in edit mode', () => {
    const transaction = {
      id: '1',
      amount: 25000,
      type: 'expense' as const,
      currency: 'ARS' as const,
      transaction_date: '2025-06-15',
      product_name: 'Test transaction',
      merchant_name: 'Store',
      category_id: 'c1',
      payment_method: 'credit_card',
    }
    renderWithProviders(<TransactionModal transaction={transaction} {...defaultProps} />)
    expect(screen.getByText('Editar transacción')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Test transaction')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Store')).toBeInTheDocument()
    expect(screen.getByDisplayValue('25000')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Tarjeta de crédito')).toBeInTheDocument()
  })

  it('maps a legacy Spanish payment label to the API enum value', () => {
    // Transacciones editadas desde la web antes del fix quedaron con "Tarjeta".
    const transaction = {
      id: '2',
      amount: 100,
      type: 'expense' as const,
      currency: 'ARS' as const,
      transaction_date: '2025-06-15',
      product_name: 'Legacy',
      merchant_name: '',
      payment_method: 'Tarjeta',
    }
    renderWithProviders(<TransactionModal transaction={transaction} {...defaultProps} />)
    expect(screen.getByDisplayValue('Tarjeta de crédito')).toBeInTheDocument()
  })

  it('calls onClose when cancel is clicked', () => {
    const onClose = vi.fn()
    renderWithProviders(<TransactionModal transaction={null} {...defaultProps} onClose={onClose} />)
    fireEvent.click(screen.getByText('Cancelar'))
    expect(onClose).toHaveBeenCalledOnce()
  })
})
