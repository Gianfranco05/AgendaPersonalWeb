import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor, within } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'
import type { Occurrence, Recurring, Upcoming } from '../../../types'

vi.mock('../../../hooks/useRecurring', () => ({
  useRecurring: vi.fn(),
  usePendingOccurrences: vi.fn(),
  useUpcomingRecurring: vi.fn(),
  removeRecurring: vi.fn(),
  setRecurringPaused: vi.fn(),
  skipPending: vi.fn(),
  confirmPending: vi.fn(),
  saveRecurring: vi.fn(),
}))
vi.mock('../../../hooks/useFinance', () => ({
  useCategories: vi.fn(() => ({ data: [] })),
  useBankAccounts: vi.fn(() => ({ data: [] })),
}))

import {
  useRecurring,
  usePendingOccurrences,
  useUpcomingRecurring,
  removeRecurring,
  setRecurringPaused,
  skipPending,
} from '../../../hooks/useRecurring'
import RecurringSection from '../RecurringSection'

const swr = <T,>(data: T | undefined, extra: object = {}) =>
  ({ data, isLoading: false, error: undefined, isValidating: false, mutate: vi.fn(), ...extra }) as never

function rec(overrides: Partial<Recurring>): Recurring {
  return {
    id: 'r1',
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
    start_date: '2026-01-01',
    end_date: null,
    anchor_date: '2026-01-05',
    next_occurrence_date: '2026-11-05',
    last_occurrence_date: null,
    status: 'active',
    requires_confirmation: false,
    notify: true,
    timezone_offset_minutes: -180,
    state: 'active',
    rule_label: 'Todos los meses el día 5',
    pending_count: 0,
    last_amount: null,
    ...overrides,
  }
}

const pending: Occurrence = {
  id: 'o1',
  recurrence_id: 'r2',
  occurrence_date: '2026-11-10',
  status: 'pending',
  suggested_amount: 25000,
  transaction_id: null,
  resolved_at: null,
  name: 'Luz',
  type: 'expense',
  currency: 'ARS',
}

const upcoming: Upcoming = {
  days: 30,
  items: [
    { recurrence_id: 'r1', date: '2026-11-05', name: 'Sueldo', type: 'income', amount: 850000, currency: 'ARS', requires_confirmation: false },
    { recurrence_id: 'r3', date: '2026-11-10', name: 'Alquiler', type: 'expense', amount: 300000, currency: 'ARS', requires_confirmation: false },
  ],
  totals: [
    { type: 'income', currency: 'ARS', total: 850000 },
    { type: 'expense', currency: 'ARS', total: 300000 },
  ],
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(useRecurring).mockReturnValue(swr([rec({}), rec({ id: 'r4', name: 'Netflix', status: 'paused', state: 'paused', type: 'expense', amount: 9000, rule_label: 'Todos los meses el día 12' })]))
  vi.mocked(usePendingOccurrences).mockReturnValue(swr([]))
  vi.mocked(useUpcomingRecurring).mockReturnValue(swr(upcoming))
})

describe('RecurringSection', () => {
  it('lista las plantillas con regla, próxima fecha y chip de estado', () => {
    renderWithProviders(<RecurringSection />)
    const items = screen.getAllByTestId('recurring-item')
    expect(items).toHaveLength(2)
    expect(items[0]).toHaveTextContent('Sueldo')
    expect(items[0]).toHaveTextContent('Activa')
    expect(items[0]).toHaveTextContent('Todos los meses el día 5')
    expect(items[0]).toHaveTextContent('Próxima: 5 nov 2026')
    expect(items[0]).toHaveTextContent('+$ 850.000,00')
    expect(items[1]).toHaveTextContent('Pausada')
    expect(items[1]).toHaveTextContent('−$ 9.000,00')
  })

  it('un monto variable se muestra como "Monto variable"', () => {
    vi.mocked(useRecurring).mockReturnValue(swr([rec({ amount: null, requires_confirmation: true, name: 'Gas' })]))
    renderWithProviders(<RecurringSection />)
    expect(screen.getByTestId('recurring-item')).toHaveTextContent('Monto variable')
    expect(screen.getByTestId('recurring-item')).toHaveTextContent('pide confirmación')
  })

  it('estado vacío con ejemplos', () => {
    vi.mocked(useRecurring).mockReturnValue(swr([]))
    renderWithProviders(<RecurringSection />)
    expect(screen.getByTestId('recurring-empty')).toHaveTextContent('sueldo')
    expect(screen.getByTestId('recurring-empty')).toHaveTextContent('Netflix')
  })

  it('resume los próximos 30 días con ingresos y egresos', () => {
    renderWithProviders(<RecurringSection />)
    expect(screen.getByTestId('upcoming-totals')).toHaveTextContent('+$ 850.000,00 / −$ 300.000,00')
  })

  it('muestra los pendientes y permite saltear o abrir la confirmación', async () => {
    vi.mocked(usePendingOccurrences).mockReturnValue(swr([pending]))
    renderWithProviders(<RecurringSection />)
    const card = screen.getByTestId('pending-card')
    expect(card).toHaveTextContent('Para confirmar (1)')
    expect(card).toHaveTextContent('sugerido $ 25.000,00')

    fireEvent.click(within(card).getByText('Saltear'))
    await waitFor(() => expect(skipPending).toHaveBeenCalledWith('o1'))

    fireEvent.click(within(card).getByText('Confirmar'))
    expect(screen.getByRole('dialog', { name: 'Confirmar movimiento' })).toBeInTheDocument()
  })

  it('pausar y reanudar', async () => {
    renderWithProviders(<RecurringSection />)
    fireEvent.click(screen.getByLabelText('Pausar Sueldo'))
    await waitFor(() => expect(setRecurringPaused).toHaveBeenCalledWith('r1', true))
    fireEvent.click(screen.getByLabelText('Reanudar Netflix'))
    await waitFor(() => expect(setRecurringPaused).toHaveBeenCalledWith('r4', false))
  })

  it('borrar avisa que las transacciones registradas se conservan', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderWithProviders(<RecurringSection />)
    fireEvent.click(screen.getByLabelText('Eliminar Sueldo'))
    expect(confirm.mock.calls[0][0]).toContain('Las transacciones ya registradas se conservan')
    expect(removeRecurring).not.toHaveBeenCalled()

    confirm.mockReturnValue(true)
    fireEvent.click(screen.getByLabelText('Eliminar Sueldo'))
    await waitFor(() => expect(removeRecurring).toHaveBeenCalledWith('r1'))
    confirm.mockRestore()
  })

  it('"Ver movimientos" avisa qué recurrencia', () => {
    const onView = vi.fn()
    renderWithProviders(<RecurringSection onViewMovements={onView} />)
    fireEvent.click(screen.getAllByText('Ver movimientos')[0])
    expect(onView).toHaveBeenCalledWith(expect.objectContaining({ id: 'r1' }))
  })

  it('si una acción falla muestra el error de la API', async () => {
    vi.mocked(setRecurringPaused).mockRejectedValue({ response: { data: { detail: 'Recurrencia no encontrada' } } })
    renderWithProviders(<RecurringSection />)
    fireEvent.click(screen.getByLabelText('Pausar Sueldo'))
    expect(await screen.findByRole('alert')).toHaveTextContent('Recurrencia no encontrada')
  })
})
