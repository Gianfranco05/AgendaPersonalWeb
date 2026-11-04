import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'
import { toLocalDateString } from '../../../utils/date'
import type { Investment } from '../../../types'

vi.mock('../../../hooks/useFinance', () => ({
  useCategories: vi.fn(() => ({ data: [{ id: 'c1', name: 'Intereses', color: '#000', icon: 'x' }] })),
  useBankAccounts: vi.fn(() => ({ data: [{ id: 'a1', name: 'Galicia' }] })),
}))
vi.mock('../../../hooks/useInvestments', () => ({
  renewFixedTerm: vi.fn(),
}))

import { renewFixedTerm } from '../../../hooks/useInvestments'
import RenewFixedTermModal from '../RenewFixedTermModal'

const today = toLocalDateString()

const matured: Investment = {
  id: 'i1',
  asset_type: 'fixed_term',
  name: 'Plazo fijo Galicia',
  ticker: null,
  currency: 'ARS',
  quantity: null,
  invested_amount: 1000000,
  current_value: null,
  interest_rate_tna: 30,
  start_date: '2026-09-26',
  maturity_date: today,
  institution: 'Galicia',
  notes: null,
  status: 'active',
  notify_maturity: true,
  value_updated_at: null,
  effective_value: 1024657.53,
  value_source: 'fixed_term_accrued',
  gain: 24657.53,
  gain_pct: 2.47,
  days_to_maturity: 0,
  is_matured: false,
  fixed_term: {
    term_days: 30,
    interest_total: 24657.53,
    amount_at_maturity: 1024657.53,
    accrued_interest: 24657.53,
    tea_pct: 34.5,
  },
  can_renew: true,
}

const onClose = vi.fn()
const onDone = vi.fn()

function renderModal() {
  return renderWithProviders(<RenewFixedTermModal investment={matured} onClose={onClose} onDone={onDone} />)
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('RenewFixedTermModal', () => {
  it('precarga el monto cobrado calculado y la TNA anterior', () => {
    renderModal()
    expect(screen.getByLabelText('Monto cobrado al vencer')).toHaveValue('1024657,53')
    expect(screen.getByLabelText('Nueva TNA (%)')).toHaveValue('30')
    expect(screen.getByText(/Calculado: \$ 1\.024\.657,53/)).toBeInTheDocument()
  })

  it('muestra capital, interés y nuevo capital de cada modo', () => {
    renderModal()
    // Capital + interés: el nuevo capital es lo cobrado.
    expect(screen.getByText(/Nuevo capital: \$ 1\.024\.657,53/)).toBeInTheDocument()
    // Solo capital: el interés (24.657,53) se retira.
    const only = screen.getByTestId('renew-principal-only')
    expect(only).toHaveTextContent('Capital $ 1.000.000,00')
    expect(only).toHaveTextContent('interés $ 24.657,53')
    expect(only).toHaveTextContent('nuevo capital $ 1.000.000,00')
  })

  it('la vista previa calcula el interés del nuevo plazo sobre el capital elegido', () => {
    renderModal()
    fireEvent.change(screen.getByLabelText('Nueva TNA (%)'), { target: { value: '28' } })
    const preview = screen.getByTestId('renew-preview')
    // 1.024.657,53 al 28 % por 30 días.
    expect(preview).toHaveTextContent('Nuevo plazo de 30 días')
    expect(preview).toHaveTextContent('Interés $ 23.581,16')
    fireEvent.click(screen.getByLabelText(/Solo el capital/))
    // 1.000.000 al 28 % por 30 días = 23.013,70.
    expect(preview).toHaveTextContent('Interés $ 23.013,70')
    expect(preview).toHaveTextContent('al vencimiento $ 1.023.013,70')
  })

  it('renueva capital + interés con los días del plazo', async () => {
    vi.mocked(renewFixedTerm).mockResolvedValue({} as never)
    renderModal()
    fireEvent.change(screen.getByLabelText('Nueva TNA (%)'), { target: { value: '28,5' } })
    fireEvent.click(screen.getByText('60'))
    fireEvent.click(screen.getByText('Renovar', { selector: 'button[type="submit"]' }))
    await waitFor(() => expect(renewFixedTerm).toHaveBeenCalledTimes(1))
    expect(renewFixedTerm).toHaveBeenCalledWith('i1', {
      mode: 'principal_and_interest',
      interest_rate_tna: 28.5,
      term_days: 60,
      start_date: today,
      amount_collected: 1024657.53,
    })
    await waitFor(() => expect(onDone).toHaveBeenCalled())
  })

  it('solo capital con el interés registrado como ingreso (categoría y cuenta)', async () => {
    vi.mocked(renewFixedTerm).mockResolvedValue({} as never)
    renderModal()
    fireEvent.click(screen.getByLabelText(/Solo el capital/))
    fireEvent.click(screen.getByLabelText(/Registrar el interés como ingreso \(\$ 24\.657,53\)/))
    fireEvent.change(screen.getByLabelText('Categoría'), { target: { value: 'c1' } })
    fireEvent.change(screen.getByLabelText('Cuenta'), { target: { value: 'a1' } })
    fireEvent.click(screen.getByText('Renovar', { selector: 'button[type="submit"]' }))
    await waitFor(() => expect(renewFixedTerm).toHaveBeenCalledTimes(1))
    expect(renewFixedTerm).toHaveBeenCalledWith(
      'i1',
      expect.objectContaining({
        mode: 'principal_only',
        register_interest_income: true,
        income_category_id: 'c1',
        income_bank_account_id: 'a1',
        income_payment_method: 'transfer',
        amount_collected: 1024657.53,
      }),
    )
  })

  it('el checkbox del ingreso arranca apagado', () => {
    renderModal()
    fireEvent.click(screen.getByLabelText(/Solo el capital/))
    expect(screen.getByLabelText(/Registrar el interés como ingreso/)).not.toBeChecked()
  })

  it('una fecha de vencimiento reemplaza a los días', async () => {
    vi.mocked(renewFixedTerm).mockResolvedValue({} as never)
    renderModal()
    const maturity = '2099-01-01'
    fireEvent.change(screen.getByLabelText('Fecha de vencimiento'), { target: { value: maturity } })
    fireEvent.click(screen.getByText('Renovar', { selector: 'button[type="submit"]' }))
    await waitFor(() => expect(renewFixedTerm).toHaveBeenCalledTimes(1))
    const body = vi.mocked(renewFixedTerm).mock.calls[0][1]
    expect(body.maturity_date).toBe(maturity)
    expect(body).not.toHaveProperty('term_days')
  })

  it('valida TNA, plazo y monto antes de mandar', async () => {
    renderModal()
    fireEvent.change(screen.getByLabelText('Nueva TNA (%)'), { target: { value: '0' } })
    fireEvent.change(screen.getByLabelText('Plazo (días)'), { target: { value: '0' } })
    fireEvent.change(screen.getByLabelText('Monto cobrado al vencer'), { target: { value: '' } })
    fireEvent.click(screen.getByText('Renovar', { selector: 'button[type="submit"]' }))
    expect(await screen.findByText(/TNA inválida/)).toBeInTheDocument()
    expect(screen.getByText('Entre 1 y 3650 días')).toBeInTheDocument()
    expect(screen.getByText('Ingresá el monto cobrado')).toBeInTheDocument()
    expect(renewFixedTerm).not.toHaveBeenCalled()
  })

  it('interés negativo en "solo capital" no se manda', async () => {
    renderModal()
    fireEvent.click(screen.getByLabelText(/Solo el capital/))
    fireEvent.change(screen.getByLabelText('Monto cobrado al vencer'), { target: { value: '999999' } })
    expect(screen.getByText(/el interés sería negativo/)).toBeInTheDocument()
    fireEvent.click(screen.getByText('Renovar', { selector: 'button[type="submit"]' }))
    await screen.findByRole('alert')
    expect(renewFixedTerm).not.toHaveBeenCalled()
  })

  it('muestra el error de la API (ya renovado)', async () => {
    vi.mocked(renewFixedTerm).mockRejectedValue({ response: { data: { detail: 'Este plazo fijo ya se renovó' } } })
    renderModal()
    fireEvent.click(screen.getByText('Renovar', { selector: 'button[type="submit"]' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Este plazo fijo ya se renovó')
    expect(onDone).not.toHaveBeenCalled()
  })
})
