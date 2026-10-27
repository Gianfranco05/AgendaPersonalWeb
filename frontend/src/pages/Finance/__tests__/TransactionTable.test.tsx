import { describe, it, expect, vi } from 'vitest'
import { screen, fireEvent } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'
import type { Transaction } from '../../../types'

vi.mock('../../../hooks/useFinance', () => ({
  useCategories: vi.fn(() => ({ data: [] })),
}))

import TransactionTable from '../TransactionTable'

function tx(overrides: Partial<Transaction>): Transaction {
  return {
    id: 't1',
    amount: 850000,
    currency: 'ARS',
    type: 'income',
    transaction_date: '2026-11-05',
    product_name: 'Sueldo',
    merchant_name: '',
    payment_method: 'transfer',
    ...overrides,
  }
}

describe('TransactionTable: movimientos recurrentes', () => {
  it('una transacción manual no lleva badge y ofrece "Hacer recurrente"', () => {
    const onMakeRecurring = vi.fn()
    const manual = tx({ id: 'm1', product_name: 'Café', is_recurring: false, recurrence_id: null })
    renderWithProviders(
      <TransactionTable transactions={[manual]} onEdit={vi.fn()} onDelete={vi.fn()} onMakeRecurring={onMakeRecurring} />,
    )
    expect(screen.queryByText('Recurrente')).not.toBeInTheDocument()
    fireEvent.click(screen.getByLabelText('Hacer recurrente Café'))
    expect(onMakeRecurring).toHaveBeenCalledWith(manual)
  })

  it('una generada por una recurrencia muestra el badge con link y no ofrece "Hacer recurrente"', () => {
    const onViewRecurrence = vi.fn()
    renderWithProviders(
      <TransactionTable
        transactions={[tx({ is_recurring: true, recurrence_id: 'r1' })]}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        onMakeRecurring={vi.fn()}
        onViewRecurrence={onViewRecurrence}
      />,
    )
    fireEvent.click(screen.getByText('Recurrente'))
    expect(onViewRecurrence).toHaveBeenCalledWith('r1')
    expect(screen.queryByLabelText(/Hacer recurrente/)).not.toBeInTheDocument()
  })

  it('si la recurrencia se borró dice "Recurrencia eliminada" (sin link)', () => {
    renderWithProviders(
      <TransactionTable
        transactions={[tx({ is_recurring: true, recurrence_id: null })]}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
      />,
    )
    expect(screen.getByText('Recurrencia eliminada')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Recurrente' })).not.toBeInTheDocument()
  })
})
