import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import { useNavigate } from 'react-router-dom'
import { renderWithProviders } from '../../../test/test-utils'
import { LocationProbe, toastMessages, resetToasts } from '../../../test/openParam'
import type { Transaction } from '../../../types'

vi.mock('../../../hooks/useFinance', () => ({
  useFinanceSummary: vi.fn(() => ({ data: undefined, isLoading: false })),
  useTransactions: vi.fn(),
  removeTransaction: vi.fn(),
}))
vi.mock('../../../hooks/useRecurring', () => ({ usePendingOccurrences: vi.fn(() => ({ data: [] })) }))
vi.mock('../../../api/endpoints', () => ({ fetchTransactions: vi.fn() }))
vi.mock('../RecurringSection', () => ({ default: () => null }))
vi.mock('../TransactionTable', () => ({ default: () => null }))
vi.mock('../TransactionFilters', () => ({ default: () => null }))
vi.mock('../FinanceCharts', () => ({ default: () => null }))
vi.mock('../InvestmentsSection', () => ({ default: () => <div>InvestmentsSection</div> }))
vi.mock('../TransactionModal', () => ({
  default: ({ transaction }: { transaction: Transaction | null }) => (
    <div role="dialog">Editando {transaction?.product_name ?? 'nuevo'}</div>
  ),
}))

import { useTransactions } from '../../../hooks/useFinance'
import { fetchTransactions } from '../../../api/endpoints'
import FinancePage from '../FinancePage'

const tx = (id: string, name: string) => ({ id, product_name: name }) as Transaction

function mockPage(items: Transaction[] | undefined) {
  vi.mocked(useTransactions).mockReturnValue({
    data: items && { items, total: items.length, page: 1, page_size: 20 },
    isLoading: items === undefined,
  } as never)
}

function SearchJump({ to }: { to: string }) {
  const navigate = useNavigate()
  return <button onClick={() => navigate(to)}>buscar-y-ir</button>
}

function renderAt(url: string) {
  return renderWithProviders(
    <>
      <FinancePage />
      <LocationProbe />
      <SearchJump to="/finances?tab=inversiones&open=i1" />
    </>,
    { router: { initialEntries: [url] } },
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  resetToasts()
})

describe('FinancePage: ?tab= y ?open= desde el buscador', () => {
  it('?tab=inversiones arranca en la pestaña Inversiones', async () => {
    mockPage([])
    renderAt('/finances?tab=inversiones')
    expect(screen.getByText('InvestmentsSection')).toBeInTheDocument()
    expect(screen.queryByText('Nueva transacción')).not.toBeInTheDocument()
  })

  it('con la página ya montada, un cambio de ?tab= en la URL cambia la pestaña', async () => {
    mockPage([])
    renderAt('/finances')
    expect(screen.getByText('Nueva transacción')).toBeInTheDocument()
    fireEvent.click(screen.getByText('buscar-y-ir'))
    expect(await screen.findByText('InvestmentsSection')).toBeInTheDocument()
  })

  it('abre el modal del movimiento que está en la página cargada y limpia la URL', async () => {
    mockPage([tx('t1', 'Café'), tx('t2', 'Nafta')])
    renderAt('/finances?tab=transacciones&open=t2')

    expect(await screen.findByRole('dialog')).toHaveTextContent('Editando Nafta')
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(/^\/finances$/))
    expect(fetchTransactions).not.toHaveBeenCalled()
    expect(toastMessages()).toEqual([])
  })

  it('si el movimiento no está en la página visible lo busca en el historial', async () => {
    mockPage([tx('t1', 'Café')])
    vi.mocked(fetchTransactions).mockResolvedValue({ items: [tx('viejo', 'Alquiler 2024')], total: 1, page: 1, page_size: 200 })
    renderAt('/finances?tab=transacciones&open=viejo')

    expect(await screen.findByRole('dialog')).toHaveTextContent('Editando Alquiler 2024')
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(/^\/finances$/))
  })

  it('espera a que cargue la lista antes de decidir', async () => {
    mockPage(undefined)
    const { rerender } = renderAt('/finances?tab=transacciones&open=t1')
    expect(fetchTransactions).not.toHaveBeenCalled()
    expect(toastMessages()).toEqual([])
    mockPage([tx('t1', 'Café')])
    rerender(<><FinancePage /><LocationProbe /></>)
    expect(await screen.findByRole('dialog')).toHaveTextContent('Editando Café')
  })

  it('si el movimiento no existe avisa y no abre el modal', async () => {
    mockPage([tx('t1', 'Café')])
    vi.mocked(fetchTransactions).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 200 })
    renderAt('/finances?tab=transacciones&open=borrado')

    await waitFor(() => expect(toastMessages()).toEqual(['Ese elemento ya no existe']))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.getByTestId('location')).toHaveTextContent(/^\/finances$/)
  })
})
