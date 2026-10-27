import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'
import type { Occurrence } from '../../../types'

vi.mock('../../../hooks/useRecurring', () => ({
  confirmPending: vi.fn(),
  skipPending: vi.fn(),
}))

import { confirmPending, skipPending } from '../../../hooks/useRecurring'
import ConfirmOccurrenceModal from '../ConfirmOccurrenceModal'

const occurrence: Occurrence = {
  id: 'o1',
  recurrence_id: 'r1',
  occurrence_date: '2026-11-05',
  status: 'pending',
  suggested_amount: 25000,
  transaction_id: null,
  resolved_at: null,
  name: 'Luz',
  type: 'expense',
  currency: 'ARS',
}

const onClose = vi.fn()
const onDone = vi.fn()

function renderModal(o: Occurrence = occurrence) {
  return renderWithProviders(<ConfirmOccurrenceModal occurrence={o} onClose={onClose} onDone={onDone} />)
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('ConfirmOccurrenceModal', () => {
  it('precarga el monto sugerido y la fecha de la ocurrencia', () => {
    renderModal()
    expect(screen.getByText('Confirmar Luz')).toBeInTheDocument()
    expect(screen.getByLabelText('Monto')).toHaveValue('25000')
    expect(screen.getByLabelText('Fecha')).toHaveValue('2026-11-05')
    expect(screen.getByText(/sugerido \$ 25\.000,00/)).toBeInTheDocument()
  })

  it('confirma con el monto editado (coma decimal) y la fecha', async () => {
    vi.mocked(confirmPending).mockResolvedValue(undefined)
    renderModal()
    fireEvent.change(screen.getByLabelText('Monto'), { target: { value: '31.250,50' } })
    fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2026-11-04' } })
    fireEvent.click(screen.getByText('Confirmar'))
    await waitFor(() => expect(confirmPending).toHaveBeenCalledTimes(1))
    expect(confirmPending).toHaveBeenCalledWith('o1', { amount: 31250.5, transaction_date: '2026-11-04' })
    await waitFor(() => expect(onDone).toHaveBeenCalled())
  })

  it('sin monto sugerido arranca vacío y exige un monto', async () => {
    renderModal({ ...occurrence, suggested_amount: null })
    expect(screen.getByLabelText('Monto')).toHaveValue('')
    fireEvent.click(screen.getByText('Confirmar'))
    expect(await screen.findByText('Ingresá un monto mayor a 0')).toBeInTheDocument()
    expect(confirmPending).not.toHaveBeenCalled()
  })

  it('saltear no pide monto', async () => {
    vi.mocked(skipPending).mockResolvedValue(undefined)
    renderModal({ ...occurrence, suggested_amount: null })
    fireEvent.click(screen.getByText('Saltear'))
    await waitFor(() => expect(skipPending).toHaveBeenCalledWith('o1'))
    await waitFor(() => expect(onDone).toHaveBeenCalled())
    expect(confirmPending).not.toHaveBeenCalled()
  })

  it('muestra el error de la API (ej. ya resuelto desde otro dispositivo)', async () => {
    vi.mocked(confirmPending).mockRejectedValue({ response: { data: { detail: 'Este movimiento ya se salteó' } } })
    renderModal()
    fireEvent.click(screen.getByText('Confirmar'))
    expect(await screen.findByRole('alert')).toHaveTextContent('Este movimiento ya se salteó')
    expect(onDone).not.toHaveBeenCalled()
  })
})
