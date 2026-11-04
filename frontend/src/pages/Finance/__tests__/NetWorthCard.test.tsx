import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'
import NetWorthCard from '../NetWorthCard'
import type { NetWorth } from '../../../types'

const full: NetWorth = {
  cash_balance_ars: 100000,
  cash_balance_usd: 68.94,
  investments: {
    by_currency: [
      { currency: 'ARS', invested: 400000, current_value: 500000, gain: 100000, count: 1 },
      { currency: 'USD', invested: 1800, current_value: 2000, gain: 200, count: 1 },
    ],
    by_type: [],
    total_ars: 3401000,
    total_usd: 2344.71,
    missing_rates: [],
    count_active: 2,
    upcoming_maturities: [],
  },
  net_worth_ars: 3501000,
  net_worth_usd: 2413.65,
  rates: { usd_ars: 1450.5, eur_ars: null, updated_at: null },
  missing_rates: [],
  include_investments_in_balance: false,
}

describe('NetWorthCard', () => {
  it('muestra disponible, inversiones y total, cada uno en ARS y en USD', () => {
    renderWithProviders(<NetWorthCard data={full} />)
    const card = screen.getByTestId('net-worth-card')

    expect(card).toHaveTextContent('Patrimonio')
    expect(card).toHaveTextContent('$ 3.501.000,00')
    expect(card).toHaveTextContent('≈ US$ 2.413,65')
    // Tabla: Disponible / Inversiones / Total
    const rows = card.querySelectorAll('tbody tr')
    expect(rows).toHaveLength(3)
    expect(rows[0]).toHaveTextContent('Disponible$ 100.000,00US$ 68,94')
    expect(rows[1]).toHaveTextContent('Inversiones$ 3.401.000,00US$ 2.344,71')
    expect(rows[2]).toHaveTextContent('Total$ 3.501.000,00US$ 2.413,65')
    // Subtotales por moneda
    expect(card).toHaveTextContent('$ 500.000,00')
    expect(card).toHaveTextContent('US$ 2.000,00')
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('con el toggle encendido el titular es "Balance + inversiones" y hay dos tramos con leyenda', () => {
    renderWithProviders(<NetWorthCard data={{ ...full, include_investments_in_balance: true }} />)
    const card = screen.getByTestId('net-worth-card')
    expect(card).toHaveTextContent('Balance + inversiones')
    expect(screen.getByRole('img', { name: 'Efectivo e inversiones' })).toBeInTheDocument()
    expect(card).toHaveTextContent('Efectivo')
    expect(card).toHaveTextContent('Inversiones')
    // El tramo de inversiones no es el verde de ingresos ni el rojo de egresos.
    const bar = screen.getByRole('img', { name: 'Efectivo e inversiones' })
    expect(bar.innerHTML).toContain('bg-sky-500')
    expect(bar.innerHTML).not.toContain('rose')
  })

  it('sin cotización muestra el efectivo, "—" y el aviso', () => {
    const data: NetWorth = {
      ...full,
      cash_balance_usd: null,
      investments: { ...full.investments, total_ars: null, total_usd: 2000, missing_rates: ['USD'] },
      net_worth_ars: null,
      net_worth_usd: null,
      rates: { usd_ars: null, eur_ars: null, updated_at: null },
      missing_rates: ['USD'],
    }
    renderWithProviders(<NetWorthCard data={data} />)
    const card = screen.getByTestId('net-worth-card')

    expect(card).toHaveTextContent('Disponible')
    expect(card).toHaveTextContent('$ 100.000,00')
    expect(screen.getByRole('status')).toHaveTextContent('Cargá la cotización del dólar para ver el total')
    // Los subtotales por moneda siguen visibles.
    expect(card).toHaveTextContent('US$ 2.000,00')
    expect(card.querySelectorAll('tbody td')[7]).toHaveTextContent('—')
    expect(screen.queryByRole('img', { name: 'Efectivo e inversiones' })).not.toBeInTheDocument()
  })

  it('con el dólar cargado pero sin euro pide la cotización del euro', () => {
    const data: NetWorth = {
      ...full,
      investments: { ...full.investments, total_ars: null, total_usd: null, missing_rates: ['EUR'] },
      net_worth_ars: null,
      net_worth_usd: null,
      missing_rates: ['EUR'],
    }
    renderWithProviders(<NetWorthCard data={data} />)
    expect(screen.getByRole('status')).toHaveTextContent('del euro')
  })

  it('solo falta el dólar para los montos en USD: el total en pesos se ve', () => {
    const data: NetWorth = {
      ...full,
      cash_balance_usd: null,
      investments: { ...full.investments, total_usd: null, missing_rates: ['USD'] },
      net_worth_usd: null,
      missing_rates: ['USD'],
    }
    renderWithProviders(<NetWorthCard data={data} />)
    expect(screen.getByTestId('net-worth-card')).toHaveTextContent('$ 3.501.000,00')
    expect(screen.getByRole('status')).toHaveTextContent('montos en USD')
  })

  it('indica qué dólar se usa, de dónde viene y cuándo se actualizó', () => {
    const data: NetWorth = {
      ...full,
      rates: {
        usd_ars: 1563.9,
        eur_ars: null,
        updated_at: new Date(Date.now() - 12 * 60_000).toISOString(),
        usd_source: 'mep',
        usd_effective_source: 'mep',
        usd_provider: 'dolarapi',
        usd_as_of: new Date(Date.now() - 12 * 60_000).toISOString(),
        usd_stale: false,
      },
    }
    renderWithProviders(<NetWorthCard data={data} />)
    expect(screen.getByTestId('fx-used')).toHaveTextContent('Dólar MEP $ 1.563,90 · DolarAPI · hace 12 min')
    expect(screen.queryByText('desactualizada')).not.toBeInTheDocument()
  })

  it('marca desactualizada la cotización vieja y nombra la manual', () => {
    const stale: NetWorth = {
      ...full,
      rates: { ...full.rates, usd_source: 'blue', usd_effective_source: 'blue', usd_provider: 'bluelytics', usd_stale: true },
    }
    const { unmount } = renderWithProviders(<NetWorthCard data={stale} />)
    expect(screen.getByTestId('fx-used')).toHaveTextContent('Dólar Blue $ 1.450,50 · Bluelytics')
    expect(screen.getByText('desactualizada')).toBeInTheDocument()
    unmount()

    const manual: NetWorth = {
      ...full,
      rates: { ...full.rates, usd_source: 'manual', usd_effective_source: 'manual' },
    }
    renderWithProviders(<NetWorthCard data={manual} />)
    expect(screen.getByTestId('fx-used')).toHaveTextContent('Dólar manual $ 1.450,50')
  })

  it('sin información de fuente (server viejo) no muestra el pie', () => {
    renderWithProviders(<NetWorthCard data={full} />)
    expect(screen.queryByTestId('fx-used')).not.toBeInTheDocument()
  })
})
