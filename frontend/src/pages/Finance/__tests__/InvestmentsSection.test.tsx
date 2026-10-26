import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor, within } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'
import type { Investment, MarketFx, NetWorth } from '../../../types'

vi.mock('../../../hooks/useInvestments', () => ({
  useInvestments: vi.fn(),
  useNetWorth: vi.fn(),
  removeInvestment: vi.fn(),
  setInvestmentStatus: vi.fn(),
  saveInvestmentSettings: vi.fn(),
  saveInvestment: vi.fn(),
}))

vi.mock('../../../hooks/useMarket', () => ({
  useMarketFx: vi.fn(),
  useCryptoAssets: vi.fn(),
  useInflation: vi.fn(),
}))

import { useMarketFx, useCryptoAssets } from '../../../hooks/useMarket'
import {
  useInvestments,
  useNetWorth,
  removeInvestment,
  setInvestmentStatus,
  saveInvestmentSettings,
} from '../../../hooks/useInvestments'
import InvestmentsSection from '../InvestmentsSection'

const swr = <T,>(data: T | undefined, extra: object = {}) =>
  ({ data, isLoading: false, error: undefined, isValidating: false, mutate: vi.fn(), ...extra }) as never

function inv(overrides: Partial<Investment>): Investment {
  return {
    id: 'i1',
    asset_type: 'stock',
    name: 'Apple CEDEAR',
    ticker: 'AAPL',
    currency: 'ARS',
    quantity: 10,
    invested_amount: 150000,
    current_value: 172500,
    interest_rate_tna: null,
    start_date: null,
    maturity_date: null,
    institution: 'Balanz',
    notes: null,
    status: 'active',
    notify_maturity: true,
    value_updated_at: null,
    effective_value: 172500,
    value_source: 'manual',
    gain: 22500,
    gain_pct: 15,
    days_to_maturity: null,
    is_matured: false,
    fixed_term: null,
    ...overrides,
  }
}

const fixedTerm = inv({
  id: 'i2',
  asset_type: 'fixed_term',
  name: 'Plazo fijo Galicia',
  ticker: null,
  quantity: null,
  invested_amount: 1000000,
  current_value: null,
  interest_rate_tna: 30,
  start_date: '2026-10-01',
  maturity_date: '2026-10-31',
  effective_value: 1009863.01,
  value_source: 'fixed_term_accrued',
  gain: 9863.01,
  gain_pct: 0.99,
  days_to_maturity: 5,
  fixed_term: {
    term_days: 30,
    interest_total: 24657.53,
    amount_at_maturity: 1024657.53,
    accrued_interest: 9863.01,
    tea_pct: 34.5,
  },
})

const loss = inv({ id: 'i3', name: 'Bono', asset_type: 'bond', ticker: null, gain: -200, gain_pct: -20, effective_value: 800, invested_amount: 1000, quantity: null, institution: null, current_value: 800 })

const netWorth: NetWorth = {
  cash_balance_ars: 100000,
  cash_balance_usd: 68.94,
  investments: {
    by_currency: [{ currency: 'ARS', invested: 1150000, current_value: 1182363.01, gain: 32363.01, count: 2 }],
    by_type: [],
    total_ars: 1182363.01,
    total_usd: 815.1,
    missing_rates: [],
    count_active: 2,
    upcoming_maturities: [],
  },
  net_worth_ars: 1282363.01,
  net_worth_usd: 884.04,
  rates: { usd_ars: 1450.5, eur_ars: null, updated_at: null },
  missing_rates: [],
  include_investments_in_balance: false,
}

const market: MarketFx = {
  usd: [
    { kind: 'oficial', label: 'Oficial', buy: 1500, sell: 1550, provider: 'dolarapi', as_of: new Date().toISOString(), stale: false },
    { kind: 'mep', label: 'MEP', buy: 1557.4, sell: 1563.9, provider: 'dolarapi', as_of: new Date(Date.now() - 12 * 60_000).toISOString(), stale: false },
    { kind: 'blue', label: 'Blue', buy: 1545, sell: 1565, provider: 'dolarapi', as_of: new Date().toISOString(), stale: false },
  ],
  eur: [
    { kind: 'oficial', label: 'Oficial', buy: 1700, sell: 1713.96, provider: 'dolarapi', as_of: new Date().toISOString(), stale: false },
    { kind: 'blue', label: 'Blue', buy: 1662, sell: 1698, provider: 'bluelytics', as_of: new Date().toISOString(), stale: false },
  ],
  last_success_at: new Date().toISOString(),
  degraded: false,
}

const autoRates: NetWorth['rates'] = {
  usd_ars: 1563.9,
  eur_ars: 1713.96,
  updated_at: new Date(Date.now() - 12 * 60_000).toISOString(),
  usd_source: 'mep',
  usd_effective_source: 'mep',
  usd_buy: 1557.4,
  usd_provider: 'dolarapi',
  usd_as_of: new Date(Date.now() - 12 * 60_000).toISOString(),
  usd_stale: false,
  eur_source: 'oficial',
  eur_effective_source: 'oficial',
  eur_provider: 'dolarapi',
  eur_stale: false,
}

const realReturn = {
  nominal_pct: 2.47,
  inflation_pct: 1.9,
  real_pct: 0.56,
  estimated: false,
  estimated_months: [],
  period_start: '2026-09-01',
  period_end: '2026-10-01',
  projected_at_maturity: null,
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(useMarketFx).mockReturnValue(swr(market))
  vi.mocked(useCryptoAssets).mockReturnValue(swr([{ ticker: 'BTC', name: 'Bitcoin' }]))
  vi.mocked(useInvestments).mockReturnValue(swr([inv({}), fixedTerm, loss]))
  vi.mocked(useNetWorth).mockReturnValue(swr(netWorth))
})

describe('InvestmentsSection', () => {
  it('agrupa por tipo con subtotal y muestra ganancia, TNA y chip de vencimiento', () => {
    renderWithProviders(<InvestmentsSection />)

    const groups = screen.getAllByRole('region')
    expect(groups.map((g) => g.getAttribute('aria-label'))).toEqual([
      'Acciones / CEDEARs',
      'Plazo fijo',
      'Bonos',
    ])
    const pf = screen.getByRole('region', { name: 'Plazo fijo' })
    expect(pf).toHaveTextContent('$ 1.009.863,01')
    expect(pf).toHaveTextContent('TNA 30%')
    expect(pf).toHaveTextContent('vence en 5 días')
    expect(pf).toHaveTextContent('Al vencimiento $ 1.024.657,53')
    expect(pf).toHaveTextContent('con interés devengado a hoy')

    const stock = screen.getByRole('region', { name: 'Acciones / CEDEARs' })
    expect(stock).toHaveTextContent('+$ 22.500,00')
    expect(stock).toHaveTextContent('AAPL')
    // Ganancia en verde, pérdida en rojo.
    expect(within(stock).getByText(/\+\$ 22\.500,00/).className).toContain('text-emerald-500')
    const bond = screen.getByRole('region', { name: 'Bonos' })
    expect(within(bond).getByText(/-\$ 200,00/).className).toContain('text-rose-500')
  })

  it('estado vacío', () => {
    vi.mocked(useInvestments).mockReturnValue(swr([]))
    renderWithProviders(<InvestmentsSection />)
    expect(screen.getByText('Todavía no cargaste inversiones')).toBeInTheDocument()
  })

  it('error de carga sin datos previos', () => {
    vi.mocked(useInvestments).mockReturnValue(swr(undefined, { error: new Error('x') }))
    renderWithProviders(<InvestmentsSection />)
    expect(screen.getByRole('alert')).toHaveTextContent('No se pudieron cargar las inversiones')
  })

  it('el filtro Cerradas pide la lista de cerradas', () => {
    renderWithProviders(<InvestmentsSection />)
    fireEvent.click(screen.getByText('Cerradas'))
    expect(useInvestments).toHaveBeenLastCalledWith('closed')
  })

  it('cerrar una inversión', async () => {
    renderWithProviders(<InvestmentsSection />)
    fireEvent.click(screen.getByLabelText('Cerrar Apple CEDEAR'))
    await waitFor(() => expect(setInvestmentStatus).toHaveBeenCalledWith('i1', 'closed'))
  })

  it('reabrir una cerrada', async () => {
    vi.mocked(useInvestments).mockReturnValue(swr([inv({ status: 'closed' })]))
    renderWithProviders(<InvestmentsSection />)
    fireEvent.click(screen.getByLabelText('Reabrir Apple CEDEAR'))
    await waitFor(() => expect(setInvestmentStatus).toHaveBeenCalledWith('i1', 'active'))
  })

  it('borrar pide confirmación', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderWithProviders(<InvestmentsSection />)
    fireEvent.click(screen.getByLabelText('Eliminar Apple CEDEAR'))
    expect(removeInvestment).not.toHaveBeenCalled()

    confirm.mockReturnValue(true)
    fireEvent.click(screen.getByLabelText('Eliminar Apple CEDEAR'))
    await waitFor(() => expect(removeInvestment).toHaveBeenCalledWith('i1'))
    confirm.mockRestore()
  })

  it('si la acción falla muestra el error', async () => {
    vi.mocked(setInvestmentStatus).mockRejectedValue(new Error('x'))
    renderWithProviders(<InvestmentsSection />)
    fireEvent.click(screen.getByLabelText('Cerrar Apple CEDEAR'))
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo completar la acción')
  })

  it('el toggle "Sumar inversiones al balance" guarda la preferencia', async () => {
    renderWithProviders(<InvestmentsSection />)
    const toggle = screen.getByRole('switch', { name: 'Sumar inversiones al balance' })
    expect(toggle).toHaveAttribute('aria-checked', 'false')
    fireEvent.click(toggle)
    await waitFor(() =>
      expect(saveInvestmentSettings).toHaveBeenCalledWith({ include_investments_in_balance: true }),
    )
  })

  it('apagar el toggle manda false', async () => {
    vi.mocked(useNetWorth).mockReturnValue(swr({ ...netWorth, include_investments_in_balance: true }))
    renderWithProviders(<InvestmentsSection />)
    const toggle = screen.getByRole('switch')
    expect(toggle).toHaveAttribute('aria-checked', 'true')
    fireEvent.click(toggle)
    await waitFor(() =>
      expect(saveInvestmentSettings).toHaveBeenCalledWith({ include_investments_in_balance: false }),
    )
  })

  describe('cotización', () => {
    it('muestra el dólar y cuándo se actualizó, y el euro solo si hay activos en EUR', () => {
      const updated = new Date(Date.now() - 3 * 86_400_000).toISOString()
      vi.mocked(useNetWorth).mockReturnValue(
        swr({ ...netWorth, rates: { usd_ars: 1450.5, eur_ars: null, updated_at: updated } }),
      )
      renderWithProviders(<InvestmentsSection />)
      expect(screen.getByText(/Dólar:/)).toHaveTextContent('$ 1.450,50')
      expect(screen.getByText(/Actualizada hace 3 días/)).toBeInTheDocument()
      expect(screen.queryByText(/Euro:/)).not.toBeInTheDocument()
    })

    it('resalta la cotización con más de 7 días', () => {
      const updated = new Date(Date.now() - 10 * 86_400_000).toISOString()
      vi.mocked(useNetWorth).mockReturnValue(
        swr({ ...netWorth, rates: { usd_ars: 1450.5, eur_ars: null, updated_at: updated } }),
      )
      renderWithProviders(<InvestmentsSection />)
      expect(screen.getByText(/conviene actualizarla/)).toBeInTheDocument()
    })

    it('pide la cotización del euro cuando hay activos en EUR', () => {
      vi.mocked(useNetWorth).mockReturnValue(
        swr({
          ...netWorth,
          investments: {
            ...netWorth.investments,
            by_currency: [{ currency: 'EUR', invested: 100, current_value: 100, gain: 0, count: 1 }],
          },
        }),
      )
      renderWithProviders(<InvestmentsSection />)
      expect(screen.getByText(/Euro:/)).toBeInTheDocument()
    })

    it('guarda el dólar con coma decimal y un campo vacío lo borra', async () => {
      renderWithProviders(<InvestmentsSection />)
      fireEvent.click(screen.getByLabelText('Editar cotización'))
      fireEvent.change(screen.getByLabelText(/Dólar/), { target: { value: '1500,75' } })
      fireEvent.click(screen.getByText('Guardar'))
      await waitFor(() =>
        expect(saveInvestmentSettings).toHaveBeenCalledWith({ fx_usd_ars: 1500.75, fx_usd_source: 'manual' }),
      )

      fireEvent.click(screen.getByLabelText('Editar cotización'))
      fireEvent.change(screen.getByLabelText(/Dólar/), { target: { value: '' } })
      fireEvent.click(screen.getByText('Guardar'))
      await waitFor(() =>
        expect(saveInvestmentSettings).toHaveBeenLastCalledWith({ fx_usd_ars: null, fx_usd_source: 'manual' }),
      )
    })

    it('rechaza 0 y negativos sin llamar a la API', async () => {
      renderWithProviders(<InvestmentsSection />)
      for (const bad of ['0', '-5', 'abc']) {
        fireEvent.click(screen.getByLabelText('Editar cotización'))
        fireEvent.change(screen.getByLabelText(/Dólar/), { target: { value: bad } })
        fireEvent.click(screen.getByText('Guardar'))
        expect(await screen.findByRole('alert')).toHaveTextContent('mayor a 0')
        fireEvent.click(screen.getByText('Cancelar'))
      }
      expect(saveInvestmentSettings).not.toHaveBeenCalled()
    })
  })

  describe('cotización automática del dólar', () => {
    beforeEach(() => {
      vi.mocked(useNetWorth).mockReturnValue(swr({ ...netWorth, rates: autoRates }))
    })

    it('ofrece Oficial, MEP, Blue y Manual con la fuente elegida marcada', () => {
      renderWithProviders(<InvestmentsSection />)
      const group = screen.getByRole('radiogroup', { name: 'Fuente del dólar' })
      const options = within(group).getAllByRole('radio')
      expect(options.map((o) => o.textContent)).toEqual(['Oficial', 'MEP', 'Blue', 'Manual'])
      expect(within(group).getByRole('radio', { name: 'MEP' })).toHaveAttribute('aria-checked', 'true')
      expect(within(group).getByRole('radio', { name: 'Blue' })).toHaveAttribute('aria-checked', 'false')
    })

    it('muestra venta y compra de las tres cotizaciones, la fuente y cuándo se actualizó', () => {
      renderWithProviders(<InvestmentsSection />)
      const mep = screen.getByTestId('fx-quote-usd-mep')
      expect(mep).toHaveTextContent('MEP')
      expect(mep).toHaveTextContent('$ 1.563,90')
      expect(mep).toHaveTextContent('compra $ 1.557,40')
      expect(screen.getByTestId('fx-quote-usd-oficial')).toHaveTextContent('$ 1.550,00')
      expect(screen.getByTestId('fx-quote-usd-blue')).toHaveTextContent('$ 1.565,00')
      expect(screen.getByTestId('fx-card')).toHaveTextContent('Dólar MEP $ 1.563,90 · DolarAPI · hace 12 min')
      expect(screen.queryByText('desactualizada')).not.toBeInTheDocument()
    })

    it('cambiar de fuente manda solo la fuente (no toca la cotización manual)', async () => {
      renderWithProviders(<InvestmentsSection />)
      fireEvent.click(screen.getByRole('radio', { name: 'Blue' }))
      await waitFor(() => expect(saveInvestmentSettings).toHaveBeenCalledWith({ fx_usd_source: 'blue' }))
    })

    it('tocar la fuente que ya está elegida no hace nada', () => {
      renderWithProviders(<InvestmentsSection />)
      fireEvent.click(screen.getByRole('radio', { name: 'MEP' }))
      expect(saveInvestmentSettings).not.toHaveBeenCalled()
    })

    it('si falla el cambio de fuente muestra el error', async () => {
      vi.mocked(saveInvestmentSettings).mockRejectedValue(new Error('x'))
      renderWithProviders(<InvestmentsSection />)
      fireEvent.click(screen.getByRole('radio', { name: 'Oficial' }))
      expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo cambiar la cotización')
    })

    it('Manual muestra el campo para cargar el dólar y guarda con fuente manual', async () => {
      vi.mocked(useNetWorth).mockReturnValue(
        swr({
          ...netWorth,
          rates: { ...autoRates, usd_source: 'manual', usd_effective_source: 'manual', usd_ars: 1450.5, usd_provider: null },
        }),
      )
      renderWithProviders(<InvestmentsSection />)
      expect(screen.getByText(/Dólar:/)).toHaveTextContent('$ 1.450,50')
      fireEvent.click(screen.getByLabelText('Editar cotización'))
      fireEvent.change(screen.getByLabelText(/Dólar/), { target: { value: '1480' } })
      fireEvent.click(screen.getByText('Guardar'))
      await waitFor(() =>
        expect(saveInvestmentSettings).toHaveBeenCalledWith({ fx_usd_ars: 1480, fx_usd_source: 'manual' }),
      )
    })

    it('marca la cotización desactualizada', () => {
      vi.mocked(useNetWorth).mockReturnValue(swr({ ...netWorth, rates: { ...autoRates, usd_stale: true } }))
      renderWithProviders(<InvestmentsSection />)
      expect(within(screen.getByTestId('fx-card')).getByText('desactualizada')).toBeInTheDocument()
    })

    it('avisa cuando se usa la cotización manual porque todavía no hay datos', () => {
      vi.mocked(useNetWorth).mockReturnValue(
        swr({
          ...netWorth,
          rates: { ...autoRates, usd_ars: 1400, usd_effective_source: 'manual_fallback', usd_provider: null },
        }),
      )
      vi.mocked(useMarketFx).mockReturnValue(swr({ ...market, usd: [], degraded: true }))
      renderWithProviders(<InvestmentsSection />)
      expect(screen.getByTestId('fx-card')).toHaveTextContent(
        'Usamos tu cotización manual ($ 1.400,00) porque todavía no hay datos del mercado',
      )
    })

    it('avisa que usa la última conocida si el job viene fallando', () => {
      vi.mocked(useMarketFx).mockReturnValue(swr({ ...market, degraded: true }))
      renderWithProviders(<InvestmentsSection />)
      expect(screen.getByText(/usamos la última conocida/)).toBeInTheDocument()
    })

    it('la fila del euro (Oficial / Blue / Manual) aparece solo con activos en EUR', () => {
      renderWithProviders(<InvestmentsSection />)
      expect(screen.queryByRole('radiogroup', { name: 'Fuente del euro' })).not.toBeInTheDocument()

      vi.mocked(useNetWorth).mockReturnValue(
        swr({
          ...netWorth,
          rates: autoRates,
          investments: {
            ...netWorth.investments,
            by_currency: [{ currency: 'EUR', invested: 100, current_value: 100, gain: 0, count: 1 }],
          },
        }),
      )
      renderWithProviders(<InvestmentsSection />)
      const group = screen.getByRole('radiogroup', { name: 'Fuente del euro' })
      expect(within(group).getAllByRole('radio').map((o) => o.textContent)).toEqual(['Oficial', 'Blue', 'Manual'])
      fireEvent.click(within(group).getByRole('radio', { name: 'Blue' }))
      expect(saveInvestmentSettings).toHaveBeenCalledWith({ fx_eur_source: 'blue' })
    })
  })

  describe('rendimiento real y cotización automática', () => {
    it('chip verde "Real +0,56 %" con el detalle nominal / inflación', () => {
      vi.mocked(useInvestments).mockReturnValue(swr([{ ...fixedTerm, real_return: realReturn }]))
      renderWithProviders(<InvestmentsSection />)
      const card = screen.getByTestId('real-return')
      const chip = within(card).getByText('Real +0,56 %')
      expect(chip.className).toContain('emerald')
      expect(chip).toHaveAttribute('title', 'Nominal 2,47 % · Inflación 1,90 % (oct 2026)')
      expect(card).toHaveTextContent('nominal 2,47 % · inflación 1,90 %')
      expect(within(card).queryByText('estimado')).not.toBeInTheDocument()
    })

    it('chip rojo cuando le pierde a la inflación', () => {
      vi.mocked(useInvestments).mockReturnValue(
        swr([{ ...fixedTerm, real_return: { ...realReturn, nominal_pct: 1, inflation_pct: 3, real_pct: -1.94 } }]),
      )
      renderWithProviders(<InvestmentsSection />)
      const chip = screen.getByText('Real -1,94 %')
      expect(chip.className).toContain('rose')
    })

    it('marca "estimado" y proyecta al vencimiento en el plazo fijo', () => {
      vi.mocked(useInvestments).mockReturnValue(
        swr([
          {
            ...fixedTerm,
            real_return: {
              ...realReturn,
              estimated: true,
              estimated_months: ['2026-10'],
              projected_at_maturity: { nominal_pct: 2.47, inflation_pct: 1.95, real_pct: 0.51, estimated: true },
            },
          },
        ]),
      )
      renderWithProviders(<InvestmentsSection />)
      const estimated = screen.getByText('estimado')
      expect(estimated).toHaveAttribute('title', expect.stringContaining('oct 2026'))
      expect(screen.getByTestId('real-return')).toHaveTextContent('Al vencimiento: real ≈ +0,51 %')
    })

    it('explica por qué no hay rendimiento real', () => {
      vi.mocked(useInvestments).mockReturnValue(
        swr([
          inv({ id: 'a', real_return: null, real_return_unavailable_reason: 'no_start_date' }),
          inv({ id: 'b', name: 'Dólar', currency: 'USD', real_return: null, real_return_unavailable_reason: 'currency' }),
        ]),
      )
      renderWithProviders(<InvestmentsSection />)
      const reasons = screen.getAllByTestId('real-return-reason').map((e) => e.textContent)
      expect(reasons).toEqual([
        'Cargá la fecha de compra para ver el rendimiento real',
        'En dólares no se compara con la inflación local',
      ])
    })

    it('resumen: lo que le gana o pierde la cartera en pesos a la inflación', () => {
      vi.mocked(useNetWorth).mockReturnValue(
        swr({
          ...netWorth,
          investments: {
            ...netWorth.investments,
            real_return_ars: {
              nominal_pct: 1.64,
              inflation_pct: 1.9,
              real_pct: 0.56,
              estimated: true,
              included_count: 2,
              excluded_count: 1,
            },
          },
        }),
      )
      renderWithProviders(<InvestmentsSection />)
      const summary = screen.getByTestId('real-return-summary')
      expect(summary).toHaveTextContent('Tus inversiones en pesos le ganan 0,56 % a la inflación (2 activos, estimado)')

      vi.mocked(useNetWorth).mockReturnValue(
        swr({
          ...netWorth,
          investments: {
            ...netWorth.investments,
            real_return_ars: {
              nominal_pct: 1,
              inflation_pct: 3,
              real_pct: -1.94,
              estimated: false,
              included_count: 1,
              excluded_count: 0,
            },
          },
        }),
      )
      renderWithProviders(<InvestmentsSection />)
      expect(screen.getAllByTestId('real-return-summary')[1]).toHaveTextContent(
        'le pierden 1,94 % a la inflación (1 activo)',
      )
    })

    it('sin rendimiento real agregado no hay resumen', () => {
      renderWithProviders(<InvestmentsSection />)
      expect(screen.queryByTestId('real-return-summary')).not.toBeInTheDocument()
    })

    it('cripto automática: antigüedad del precio y atribución a CoinGecko', () => {
      vi.mocked(useInvestments).mockReturnValue(
        swr([
          inv({
            id: 'c1',
            asset_type: 'crypto',
            name: 'Bitcoin',
            ticker: 'BTC',
            currency: 'USD',
            current_value: null,
            price_source: 'coingecko',
            last_price: 79509,
            last_price_at: new Date(Date.now() - 4 * 60_000).toISOString(),
            quote_provider: 'CoinGecko',
            quote_stale: false,
          }),
        ]),
      )
      renderWithProviders(<InvestmentsSection />)
      const quote = screen.getByTestId('auto-quote')
      expect(quote).toHaveTextContent('Cotización automática · hace 4 min')
      const link = within(quote).getByRole('link', { name: 'Datos de CoinGecko' })
      expect(link).toHaveAttribute('href', 'https://www.coingecko.com')
      expect(link).toHaveAttribute('rel', expect.stringContaining('noopener'))
    })

    it('cripto automática desactualizada se resalta; sin precio todavía espera', () => {
      const base = {
        asset_type: 'crypto' as const,
        ticker: 'BTC',
        price_source: 'coingecko' as const,
        quote_provider: 'CoinGecko',
      }
      vi.mocked(useInvestments).mockReturnValue(
        swr([
          inv({ ...base, id: 'c1', name: 'Viejo', last_price_at: new Date(Date.now() - 3 * 3_600_000).toISOString(), quote_stale: true }),
          inv({ ...base, id: 'c2', name: 'Nuevo', last_price_at: null, quote_stale: null }),
        ]),
      )
      renderWithProviders(<InvestmentsSection />)
      const [old, fresh] = screen.getAllByTestId('auto-quote')
      expect(old).toHaveTextContent('hace 3 h (desactualizada)')
      expect(old.querySelector('span')!.className).toContain('amber')
      expect(fresh).toHaveTextContent('Esperando cotización')
      expect(fresh).toHaveTextContent('Datos de CoinGecko')
    })

    it('una inversión manual no muestra datos de CoinGecko', () => {
      renderWithProviders(<InvestmentsSection />)
      expect(screen.queryByText('Datos de CoinGecko')).not.toBeInTheDocument()
    })
  })

  it('"Nueva inversión" abre el formulario', () => {
    renderWithProviders(<InvestmentsSection />)
    fireEvent.click(screen.getByText('Nueva inversión'))
    expect(screen.getByRole('heading', { name: 'Nueva inversión' })).toBeInTheDocument()
  })
})
