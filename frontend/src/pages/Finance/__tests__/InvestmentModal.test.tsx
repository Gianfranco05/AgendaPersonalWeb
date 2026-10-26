import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'
import InvestmentModal from '../InvestmentModal'

vi.mock('../../../hooks/useInvestments', () => ({
  saveInvestment: vi.fn(),
}))
vi.mock('../../../hooks/useMarket', () => ({
  useCryptoAssets: vi.fn(),
}))

import { saveInvestment } from '../../../hooks/useInvestments'
import { useCryptoAssets } from '../../../hooks/useMarket'

const props = { onClose: vi.fn(), onSaved: vi.fn() }

function type(label: string | RegExp, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } })
}

function fillFixedTerm() {
  type('Nombre', 'Plazo fijo Galicia')
  type('Monto invertido', '1.000.000')
  type(/TNA/, '30')
  type(/Fecha de inicio/, '2026-10-01')
  type(/Vencimiento/, '2026-10-31')
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(useCryptoAssets).mockReturnValue({
    data: [
      { ticker: 'BTC', name: 'Bitcoin' },
      { ticker: 'ETH', name: 'Ethereum' },
    ],
    isLoading: false,
    error: undefined,
    isValidating: false,
    mutate: vi.fn(),
  } as never)
})

describe('InvestmentModal', () => {
  it('título según el modo', () => {
    renderWithProviders(<InvestmentModal investment={null} {...props} />)
    expect(screen.getByText('Nueva inversión')).toBeInTheDocument()
  })

  it('previsualiza el interés y el monto al vencimiento de un plazo fijo', () => {
    renderWithProviders(<InvestmentModal investment={null} {...props} />)
    const preview = screen.getByTestId('fixed-term-preview')
    expect(preview).toHaveTextContent('Cargá monto, TNA y fechas')

    fillFixedTerm()

    expect(preview).toHaveTextContent('$ 24.657,53')
    expect(preview).toHaveTextContent('$ 1.024.657,53')
    expect(preview).toHaveTextContent('30 días')
  })

  it('el plazo fijo en dólares previsualiza en dólares', () => {
    renderWithProviders(<InvestmentModal investment={null} {...props} />)
    fillFixedTerm()
    fireEvent.change(screen.getByLabelText('Moneda'), { target: { value: 'USD' } })
    expect(screen.getByTestId('fixed-term-preview')).toHaveTextContent('US$ 24.657,53')
  })

  it('el plazo fijo solo ofrece pesos y dólares', () => {
    renderWithProviders(<InvestmentModal investment={null} {...props} />)
    const currency = screen.getByLabelText('Moneda') as HTMLSelectElement
    expect([...currency.options].map((o) => o.value)).toEqual(['ARS', 'USD'])

    fireEvent.change(screen.getByLabelText('Tipo'), { target: { value: 'crypto' } })
    expect([...currency.options].map((o) => o.value)).toEqual(['ARS', 'USD', 'USDT', 'EUR'])
  })

  it('valida los campos obligatorios del plazo fijo sin llamar a la API', async () => {
    renderWithProviders(<InvestmentModal investment={null} {...props} />)
    fireEvent.click(screen.getByText('Crear'))

    expect(await screen.findByText('El nombre es requerido')).toBeInTheDocument()
    expect(screen.getByText('Ingresá el monto invertido')).toBeInTheDocument()
    expect(screen.getByText('La TNA es requerida')).toBeInTheDocument()
    expect(screen.getByText('El vencimiento es requerido')).toBeInTheDocument()
    expect(saveInvestment).not.toHaveBeenCalled()
  })

  it('rechaza un vencimiento anterior al inicio y montos fuera de rango', async () => {
    renderWithProviders(<InvestmentModal investment={null} {...props} />)
    fillFixedTerm()
    type(/Vencimiento/, '2026-09-01')
    type('Monto invertido', '10000000000')
    fireEvent.click(screen.getByText('Crear'))

    expect(await screen.findByText('El vencimiento no puede ser anterior al inicio')).toBeInTheDocument()
    expect(screen.getByText('Monto fuera de rango')).toBeInTheDocument()
    expect(saveInvestment).not.toHaveBeenCalled()
  })

  it('guarda un plazo fijo: el valor actual va null para que el server lo devengue', async () => {
    vi.mocked(saveInvestment).mockResolvedValue(undefined)
    renderWithProviders(<InvestmentModal investment={null} {...props} />)
    fillFixedTerm()
    fireEvent.click(screen.getByText('Crear'))

    await waitFor(() => expect(saveInvestment).toHaveBeenCalled())
    const [existing, payload] = vi.mocked(saveInvestment).mock.calls[0]
    expect(existing).toBeNull()
    expect(payload).toMatchObject({
      asset_type: 'fixed_term',
      name: 'Plazo fijo Galicia',
      currency: 'ARS',
      invested_amount: 1000000,
      current_value: null,
      interest_rate_tna: 30,
      start_date: '2026-10-01',
      maturity_date: '2026-10-31',
      notify_maturity: true,
    })
    await waitFor(() => expect(props.onSaved).toHaveBeenCalled())
  })

  it('acepta coma decimal y normaliza el ticker', async () => {
    vi.mocked(saveInvestment).mockResolvedValue(undefined)
    renderWithProviders(<InvestmentModal investment={null} {...props} />)
    fireEvent.change(screen.getByLabelText('Tipo'), { target: { value: 'stock' } })
    type('Nombre', 'Apple CEDEAR')
    type(/Ticker/, 'aapl')
    type(/Cantidad/, '0,00012345')
    type('Monto invertido', '1500,50')
    type(/Valor actual/, '1.720,25')
    fireEvent.click(screen.getByText('Crear'))

    await waitFor(() => expect(saveInvestment).toHaveBeenCalled())
    expect(vi.mocked(saveInvestment).mock.calls[0][1]).toMatchObject({
      asset_type: 'stock',
      ticker: 'AAPL',
      quantity: 0.00012345,
      invested_amount: 1500.5,
      current_value: 1720.25,
      interest_rate_tna: null,
      start_date: null,
      maturity_date: null,
    })
  })

  describe('cotización automática de cripto', () => {
    function pickCrypto(ticker: string) {
      fireEvent.change(screen.getByLabelText('Tipo'), { target: { value: 'crypto' } })
      type('Nombre', 'Bitcoin')
      type(/Ticker/, ticker)
    }

    it('el switch solo está disponible para tickers de la lista y sugiere los soportados', () => {
      renderWithProviders(<InvestmentModal investment={null} {...props} />)
      expect(screen.queryByRole('switch')).not.toBeInTheDocument()

      pickCrypto('FOOCOIN')
      const toggle = screen.getByRole('switch', { name: 'Cotización automática' })
      expect(toggle).toBeDisabled()
      expect(screen.getByText(/No tenemos cotización automática para ese ticker/)).toBeInTheDocument()

      type(/Ticker/, 'btc')
      expect(toggle).toBeEnabled()
      const options = [...document.querySelectorAll('#inv-ticker-options option')].map((o) => o.getAttribute('value'))
      expect(options).toEqual(['BTC', 'ETH'])
    })

    it('al activarlo oculta el valor actual y exige la cantidad', async () => {
      renderWithProviders(<InvestmentModal investment={null} {...props} />)
      pickCrypto('BTC')
      type('Monto invertido', '30000')
      expect(screen.getByLabelText(/Valor actual/)).toBeInTheDocument()

      fireEvent.click(screen.getByRole('switch', { name: 'Cotización automática' }))
      expect(screen.queryByLabelText(/Valor actual/)).not.toBeInTheDocument()
      expect(screen.getByLabelText('Cantidad')).toBeInTheDocument()

      fireEvent.click(screen.getByText('Crear'))
      expect(await screen.findByText('La cotización automática necesita la cantidad')).toBeInTheDocument()
      expect(saveInvestment).not.toHaveBeenCalled()
    })

    it('guarda con price_source coingecko y sin valor actual', async () => {
      vi.mocked(saveInvestment).mockResolvedValue(undefined)
      renderWithProviders(<InvestmentModal investment={null} {...props} />)
      pickCrypto('btc')
      type('Monto invertido', '30000')
      type(/Cantidad/, '0,5')
      type(/Valor actual/, '99999')
      fireEvent.click(screen.getByRole('switch', { name: 'Cotización automática' }))
      fireEvent.click(screen.getByText('Crear'))

      await waitFor(() => expect(saveInvestment).toHaveBeenCalled())
      expect(vi.mocked(saveInvestment).mock.calls[0][1]).toMatchObject({
        asset_type: 'crypto',
        ticker: 'BTC',
        quantity: 0.5,
        current_value: null,
        price_source: 'coingecko',
      })
    })

    it('apagado manda price_source manual', async () => {
      vi.mocked(saveInvestment).mockResolvedValue(undefined)
      renderWithProviders(<InvestmentModal investment={null} {...props} />)
      pickCrypto('BTC')
      type('Monto invertido', '30000')
      type(/Valor actual/, '31000')
      fireEvent.click(screen.getByText('Crear'))
      await waitFor(() => expect(saveInvestment).toHaveBeenCalled())
      expect(vi.mocked(saveInvestment).mock.calls[0][1]).toMatchObject({
        current_value: 31000,
        price_source: 'manual',
      })
    })

    it('si cambia el ticker a uno no soportado se apaga solo', async () => {
      renderWithProviders(<InvestmentModal investment={null} {...props} />)
      pickCrypto('BTC')
      const toggle = screen.getByRole('switch', { name: 'Cotización automática' })
      fireEvent.click(toggle)
      expect(toggle).toHaveAttribute('aria-checked', 'true')
      type(/Ticker/, 'FOOCOIN')
      await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', 'false'))
    })
  })

  describe('fecha de compra', () => {
    it('fuera del plazo fijo se llama "Fecha de compra" y explica para qué sirve', () => {
      renderWithProviders(<InvestmentModal investment={null} {...props} />)
      expect(screen.getByLabelText('Fecha de inicio')).toBeInTheDocument()
      fireEvent.change(screen.getByLabelText('Tipo'), { target: { value: 'stock' } })
      expect(screen.getByLabelText(/Fecha de compra/)).toBeInTheDocument()
      expect(screen.getByText(/rendimiento contra la inflación/)).toBeInTheDocument()
      // Una acción no tiene vencimiento.
      expect(screen.queryByLabelText(/Vencimiento/)).not.toBeInTheDocument()
    })

    it('manda la fecha de compra de una acción', async () => {
      vi.mocked(saveInvestment).mockResolvedValue(undefined)
      renderWithProviders(<InvestmentModal investment={null} {...props} />)
      fireEvent.change(screen.getByLabelText('Tipo'), { target: { value: 'stock' } })
      type('Nombre', 'Apple CEDEAR')
      type('Monto invertido', '1000')
      type(/Fecha de compra/, '2026-08-15')
      fireEvent.click(screen.getByText('Crear'))
      await waitFor(() => expect(saveInvestment).toHaveBeenCalled())
      expect(vi.mocked(saveInvestment).mock.calls[0][1]).toMatchObject({
        start_date: '2026-08-15',
        maturity_date: null,
      })
    })
  })

  it('muestra el error del server en español', async () => {
    vi.mocked(saveInvestment).mockRejectedValue({
      response: { data: { detail: 'El plazo fijo necesita la TNA' } },
    })
    renderWithProviders(<InvestmentModal investment={null} {...props} />)
    fillFixedTerm()
    fireEvent.click(screen.getByText('Crear'))

    expect(await screen.findByRole('alert')).toHaveTextContent('El plazo fijo necesita la TNA')
    expect(props.onSaved).not.toHaveBeenCalled()
  })

  it('en edición precarga los campos y guarda con la inversión existente', async () => {
    vi.mocked(saveInvestment).mockResolvedValue(undefined)
    const investment = {
      id: 'i1',
      asset_type: 'stock' as const,
      name: 'Apple CEDEAR',
      ticker: 'AAPL',
      currency: 'ARS' as const,
      quantity: 10,
      invested_amount: 150000.5,
      current_value: 172500,
      interest_rate_tna: null,
      start_date: null,
      maturity_date: null,
      institution: 'Balanz',
      notes: null,
      status: 'active' as const,
      notify_maturity: true,
      value_updated_at: null,
      effective_value: 172500,
      value_source: 'manual' as const,
      gain: 22000,
      gain_pct: 14.66,
      days_to_maturity: null,
      is_matured: false,
      fixed_term: null,
    }
    renderWithProviders(<InvestmentModal investment={investment} {...props} />)

    expect(screen.getByText('Editar inversión')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Apple CEDEAR')).toBeInTheDocument()
    expect(screen.getByDisplayValue('150000,5')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Balanz')).toBeInTheDocument()

    type('Monto invertido', '160000')
    fireEvent.click(screen.getByText('Actualizar'))
    await waitFor(() => expect(saveInvestment).toHaveBeenCalled())
    expect(vi.mocked(saveInvestment).mock.calls[0][0]).toBe(investment)
    expect(vi.mocked(saveInvestment).mock.calls[0][1]).toMatchObject({ invested_amount: 160000 })
  })
})
