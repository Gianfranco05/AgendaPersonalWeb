import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'
import { LocationProbe, toastMessages, resetToasts } from '../../../test/openParam'
import type { Investment } from '../../../types'

vi.mock('../../../hooks/useInvestments', () => ({
  useInvestments: vi.fn(),
  useNetWorth: vi.fn(() => ({ data: undefined })),
  removeInvestment: vi.fn(),
  setInvestmentStatus: vi.fn(),
  saveInvestmentSettings: vi.fn(),
  useRenewals: vi.fn(() => ({ data: undefined, isLoading: false })),
}))
vi.mock('../../../hooks/useMarket', () => ({ useMarketFx: vi.fn(() => ({ data: undefined })) }))
vi.mock('../NetWorthCard', () => ({ default: () => null }))
vi.mock('../FxRatesEditor', () => ({ default: () => null }))
vi.mock('../RenewFixedTermModal', () => ({ default: () => null }))
vi.mock('../InvestmentModal', () => ({
  default: ({ investment }: { investment: Investment | null }) => (
    <div role="dialog">Editando {investment?.name ?? 'nueva'}</div>
  ),
}))

import { useInvestments } from '../../../hooks/useInvestments'
import InvestmentsSection from '../InvestmentsSection'

const inv = (id: string, name: string, status: 'active' | 'closed' = 'active'): Investment => ({
  id,
  asset_type: 'stock',
  name,
  ticker: null,
  currency: 'ARS',
  quantity: null,
  invested_amount: 100,
  current_value: 100,
  interest_rate_tna: null,
  start_date: null,
  maturity_date: null,
  institution: null,
  notes: null,
  status,
  notify_maturity: false,
  value_updated_at: null,
  effective_value: 100,
  value_source: 'manual',
  gain: 0,
  gain_pct: 0,
  days_to_maturity: null,
  is_matured: false,
  fixed_term: null,
})

function mockLists(lists: { active: Investment[] | undefined; closed: Investment[] | undefined }) {
  vi.mocked(useInvestments).mockImplementation(((status: 'active' | 'closed' = 'active') => ({
    data: lists[status], isLoading: lists[status] === undefined, error: undefined,
  })) as never)
}

function renderAt(url: string) {
  return renderWithProviders(
    <>
      <InvestmentsSection />
      <LocationProbe />
    </>,
    { router: { initialEntries: [url] } },
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  resetToasts()
})

describe('InvestmentsSection: ?open=<id> desde el buscador', () => {
  it('abre el modal de la inversión activa y limpia open/tab de la URL', async () => {
    mockLists({ active: [inv('i1', 'Apple'), inv('i2', 'Bono AL30')], closed: [] })
    renderAt('/finances?tab=inversiones&open=i2')

    expect(await screen.findByRole('dialog')).toHaveTextContent('Editando Bono AL30')
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(/^\/finances$/))
    expect(toastMessages()).toEqual([])
  })

  it('si está cerrada cambia al filtro de cerradas y la abre', async () => {
    mockLists({ active: [inv('i1', 'Apple')], closed: [inv('i9', 'Plazo fijo viejo', 'closed')] })
    renderAt('/finances?tab=inversiones&open=i9')

    expect(await screen.findByRole('dialog')).toHaveTextContent('Editando Plazo fijo viejo')
    expect(screen.getByText('Cerradas').className).toContain('bg-brand-charcoal')
  })

  it('espera a que cargue la lista antes de decidir', async () => {
    mockLists({ active: undefined, closed: undefined })
    const { rerender } = renderAt('/finances?tab=inversiones&open=i1')
    expect(toastMessages()).toEqual([])
    mockLists({ active: [inv('i1', 'Apple')], closed: [] })
    rerender(<><InvestmentsSection /><LocationProbe /></>)
    expect(await screen.findByRole('dialog')).toHaveTextContent('Editando Apple')
  })

  it('si no está ni entre las activas ni entre las cerradas avisa', async () => {
    mockLists({ active: [inv('i1', 'Apple')], closed: [inv('i9', 'Otra', 'closed')] })
    renderAt('/finances?tab=inversiones&open=borrada')

    await waitFor(() => expect(toastMessages()).toEqual(['Ese elemento ya no existe']))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.getByTestId('location')).toHaveTextContent(/^\/finances$/)
  })
})
