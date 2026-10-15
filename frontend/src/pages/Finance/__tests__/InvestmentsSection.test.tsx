import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor, within } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'
import type { Investment, NetWorth } from '../../../types'

vi.mock('../../../hooks/useInvestments', () => ({
  useInvestments: vi.fn(),
  useNetWorth: vi.fn(),
  removeInvestment: vi.fn(),
  setInvestmentStatus: vi.fn(),
  saveInvestmentSettings: vi.fn(),
  saveInvestment: vi.fn(),
}))

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

beforeEach(() => {
  vi.clearAllMocks()
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
      await waitFor(() => expect(saveInvestmentSettings).toHaveBeenCalledWith({ fx_usd_ars: 1500.75 }))

      fireEvent.click(screen.getByLabelText('Editar cotización'))
      fireEvent.change(screen.getByLabelText(/Dólar/), { target: { value: '' } })
      fireEvent.click(screen.getByText('Guardar'))
      await waitFor(() => expect(saveInvestmentSettings).toHaveBeenLastCalledWith({ fx_usd_ars: null }))
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

  it('"Nueva inversión" abre el formulario', () => {
    renderWithProviders(<InvestmentsSection />)
    fireEvent.click(screen.getByText('Nueva inversión'))
    expect(screen.getByRole('heading', { name: 'Nueva inversión' })).toBeInTheDocument()
  })
})
