import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'
import { toLocalDateString } from '../../../utils/date'
import type { Recurring } from '../../../types'

vi.mock('../../../hooks/useFinance', () => ({
  useCategories: vi.fn(() => ({ data: [{ id: 'c1', name: 'Servicios', color: '#000', icon: 'x' }] })),
  useBankAccounts: vi.fn(() => ({ data: [{ id: 'a1', name: 'Galicia' }] })),
}))
vi.mock('../../../hooks/useRecurring', () => ({
  saveRecurring: vi.fn(),
}))
vi.mock('../../../api/endpoints', () => ({
  previewRecurring: vi.fn(),
}))

import { saveRecurring } from '../../../hooks/useRecurring'
import { previewRecurring } from '../../../api/endpoints'
import RecurringModal from '../RecurringModal'

const onClose = vi.fn()
const onSaved = vi.fn()

function renderModal(props: Partial<React.ComponentProps<typeof RecurringModal>> = {}) {
  return renderWithProviders(<RecurringModal recurring={null} onClose={onClose} onSaved={onSaved} {...props} />)
}

const existing: Recurring = {
  id: 'r1',
  type: 'expense',
  name: 'Alquiler',
  description: null,
  notes: null,
  amount: 300000,
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
  day_of_month: 10,
  month_of_year: null,
  start_date: '2026-01-01',
  end_date: null,
  anchor_date: '2026-01-10',
  next_occurrence_date: '2026-11-10',
  last_occurrence_date: null,
  status: 'active',
  requires_confirmation: false,
  notify: true,
  timezone_offset_minutes: -180,
  state: 'active',
  rule_label: 'Todos los meses el día 10',
  pending_count: 0,
  last_amount: 300000,
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(previewRecurring).mockResolvedValue({ anchor_date: '2026-11-05', dates: ['2026-11-05', '2026-12-05'] })
})

describe('RecurringModal', () => {
  it('muestra el título de alta y los campos de una regla mensual', () => {
    renderModal()
    expect(screen.getByText('Nuevo movimiento recurrente')).toBeInTheDocument()
    expect(screen.getByLabelText('Día del mes')).toBeInTheDocument()
    expect(screen.queryByLabelText('Día de la semana')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Mes')).not.toBeInTheDocument()
  })

  it('cambia los campos según la frecuencia', () => {
    renderModal()
    fireEvent.change(screen.getByLabelText('Frecuencia'), { target: { value: 'weekly' } })
    expect(screen.getByLabelText('Día de la semana')).toBeInTheDocument()
    expect(screen.queryByLabelText('Día del mes')).not.toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Frecuencia'), { target: { value: 'yearly' } })
    expect(screen.getByLabelText('Día del mes')).toBeInTheDocument()
    expect(screen.getByLabelText('Mes')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Frecuencia'), { target: { value: 'daily' } })
    expect(screen.queryByLabelText('Día del mes')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Día de la semana')).not.toBeInTheDocument()
  })

  it('el día 31 muestra la ayuda del último día del mes; el 5 no', () => {
    renderModal()
    expect(screen.queryByTestId('short-month-help')).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Día del mes'), { target: { value: '31' } })
    expect(screen.getByTestId('short-month-help')).toHaveTextContent('último día del mes')
    fireEvent.change(screen.getByLabelText('Día del mes'), { target: { value: '5' } })
    expect(screen.queryByTestId('short-month-help')).not.toBeInTheDocument()
  })

  it('valida nombre y monto antes de guardar', async () => {
    renderModal()
    fireEvent.click(screen.getByText('Crear'))
    expect(await screen.findByText('El nombre es requerido')).toBeInTheDocument()
    expect(screen.getByText(/Ingresá el monto o activá/)).toBeInTheDocument()
    expect(saveRecurring).not.toHaveBeenCalled()
  })

  it('rechaza un monto en cero y un día que no existe en el mes anual', async () => {
    renderModal()
    fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: 'Seguro' } })
    fireEvent.change(screen.getByLabelText('Monto'), { target: { value: '0' } })
    fireEvent.change(screen.getByLabelText('Frecuencia'), { target: { value: 'yearly' } })
    fireEvent.change(screen.getByLabelText('Día del mes'), { target: { value: '31' } })
    fireEvent.change(screen.getByLabelText('Mes'), { target: { value: '4' } })
    fireEvent.click(screen.getByText('Crear'))
    expect(await screen.findByText('El monto debe ser mayor a 0')).toBeInTheDocument()
    expect(screen.getByText('Ese día no existe en el mes elegido')).toBeInTheDocument()
    expect(saveRecurring).not.toHaveBeenCalled()
  })

  it('guarda con coma decimal y manda solo los campos de la regla mensual', async () => {
    vi.mocked(saveRecurring).mockResolvedValue(undefined)
    renderModal()
    fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: '  Sueldo ' } })
    fireEvent.change(screen.getByLabelText('Monto'), { target: { value: '850.000,50' } })
    fireEvent.change(screen.getByLabelText('Día del mes'), { target: { value: '5' } })
    fireEvent.change(screen.getByLabelText('Desde'), { target: { value: toLocalDateString() } })
    fireEvent.click(screen.getByText('Crear'))

    await waitFor(() => expect(saveRecurring).toHaveBeenCalledTimes(1))
    const [existingArg, payload] = vi.mocked(saveRecurring).mock.calls[0]
    expect(existingArg).toBeNull()
    expect(payload).toMatchObject({
      name: 'Sueldo',
      amount: 850000.5,
      frequency: 'monthly',
      interval_count: 1,
      day_of_month: 5,
      weekday: null,
      month_of_year: null,
      requires_confirmation: false,
      notify: true,
      category_id: null,
      bank_account_id: null,
    })
    expect(payload).not.toHaveProperty('generate_past')
    await waitFor(() => expect(onSaved).toHaveBeenCalled())
  })

  it('con "confirmar el monto" el monto es opcional y se manda null', async () => {
    vi.mocked(saveRecurring).mockResolvedValue(undefined)
    renderModal()
    fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: 'Luz' } })
    fireEvent.click(screen.getByLabelText(/Confirmar el monto antes de registrar/))
    fireEvent.click(screen.getByText('Crear'))
    await waitFor(() => expect(saveRecurring).toHaveBeenCalledTimes(1))
    expect(vi.mocked(saveRecurring).mock.calls[0][1]).toMatchObject({ amount: null, requires_confirmation: true })
  })

  it('"Registrar también los anteriores" solo aparece con inicio pasado y manda generate_past', async () => {
    vi.mocked(saveRecurring).mockResolvedValue(undefined)
    renderModal()
    expect(screen.queryByLabelText(/Registrar también los anteriores/)).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Desde'), { target: { value: '2020-01-01' } })
    fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: 'Netflix' } })
    fireEvent.change(screen.getByLabelText('Monto'), { target: { value: '9000' } })
    fireEvent.click(screen.getByLabelText(/Registrar también los anteriores/))
    fireEvent.click(screen.getByText('Crear'))
    await waitFor(() => expect(saveRecurring).toHaveBeenCalledTimes(1))
    expect(vi.mocked(saveRecurring).mock.calls[0][1]).toMatchObject({ generate_past: true })
  })

  it('pide la vista previa con debounce y muestra las próximas fechas', async () => {
    renderModal()
    fireEvent.change(screen.getByLabelText('Día del mes'), { target: { value: '5' } })
    // Antes del debounce no hay llamada.
    expect(previewRecurring).not.toHaveBeenCalled()
    await waitFor(() => expect(previewRecurring).toHaveBeenCalled(), { timeout: 2000 })
    const arg = vi.mocked(previewRecurring).mock.calls.at(-1)![0]
    expect(arg).toMatchObject({ frequency: 'monthly', day_of_month: 5, interval_count: 1 })
    const preview = await screen.findByText(/5 nov 2026 · 5 dic 2026/)
    expect(preview).toBeInTheDocument()
  })

  it('si la vista previa falla no bloquea el formulario', async () => {
    vi.mocked(previewRecurring).mockRejectedValue(new Error('offline'))
    renderModal()
    expect(await screen.findByText('No se pudo calcular ahora.', undefined, { timeout: 2000 })).toBeInTheDocument()
    expect(screen.getByText('Crear')).toBeEnabled()
  })

  it('en edición precarga los datos y actualiza', async () => {
    vi.mocked(saveRecurring).mockResolvedValue(undefined)
    renderModal({ recurring: existing })
    expect(screen.getByText('Editar recurrente')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Alquiler')).toBeInTheDocument()
    expect(screen.getByDisplayValue('300000')).toBeInTheDocument()
    expect(screen.getByDisplayValue('10')).toBeInTheDocument()
    // No se ofrece registrar anteriores al editar.
    expect(screen.queryByLabelText(/Registrar también los anteriores/)).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Monto'), { target: { value: '320000' } })
    fireEvent.click(screen.getByText('Actualizar'))
    await waitFor(() => expect(saveRecurring).toHaveBeenCalledTimes(1))
    expect(vi.mocked(saveRecurring).mock.calls[0][0]).toBe(existing)
    expect(vi.mocked(saveRecurring).mock.calls[0][1]).toMatchObject({ amount: 320000, day_of_month: 10 })
  })

  it('muestra el error de la API si guardar falla', async () => {
    vi.mocked(saveRecurring).mockRejectedValue({ response: { data: { detail: 'Categoría no encontrada' } } })
    renderModal()
    fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: 'Sueldo' } })
    fireEvent.change(screen.getByLabelText('Monto'), { target: { value: '100' } })
    fireEvent.click(screen.getByText('Crear'))
    expect(await screen.findByRole('alert')).toHaveTextContent('Categoría no encontrada')
    expect(onSaved).not.toHaveBeenCalled()
  })

  it('precarga desde una transacción ("Hacer recurrente")', () => {
    renderModal({
      prefill: { type: 'expense', name: 'Netflix', amount: 9000.5, start_date: '2026-10-12', payment_method: 'credit_card' },
    })
    expect(screen.getByDisplayValue('Netflix')).toBeInTheDocument()
    expect(screen.getByDisplayValue('9000,5')).toBeInTheDocument()
    expect(screen.getByDisplayValue('12')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Tarjeta de crédito')).toBeInTheDocument()
  })

  it('cancelar cierra', () => {
    renderModal()
    fireEvent.click(screen.getByText('Cancelar'))
    expect(onClose).toHaveBeenCalledOnce()
  })
})
