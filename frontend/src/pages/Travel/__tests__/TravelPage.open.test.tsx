import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'
import { LocationProbe, toastMessages, resetToasts, stubScrollIntoView } from '../../../test/openParam'
import type { Trip, PackingItem } from '../../../types'

vi.mock('../../../hooks/useTravel', () => ({
  useTrips: vi.fn(),
  useTravelSummary: vi.fn(() => ({ data: undefined })),
  usePackingItems: vi.fn(),
  removeTrip: vi.fn(),
  addTrip: vi.fn(),
  editTrip: vi.fn(),
  addItem: vi.fn(),
  toggleItemPacked: vi.fn(),
  removeItem: vi.fn(),
}))

import { useTrips, usePackingItems } from '../../../hooks/useTravel'
import TravelPage from '../TravelPage'

const trip = (id: string, destination: string): Trip =>
  ({ id, destination, status: 'planeado', start_date: null, end_date: null, notes: null }) as Trip
const item = (id: string, name: string): PackingItem => ({ id, name, packed: false }) as PackingItem

function mockTrips(trips: Trip[] | undefined, itemsByTrip: Record<string, PackingItem[] | undefined> = {}) {
  vi.mocked(useTrips).mockReturnValue({ data: trips, isLoading: trips === undefined, error: undefined } as never)
  vi.mocked(usePackingItems).mockImplementation(((tripId: string | null) => ({
    data: tripId ? itemsByTrip[tripId] : undefined,
    isLoading: tripId ? itemsByTrip[tripId] === undefined : false,
  })) as never)
}

function renderAt(url: string) {
  return renderWithProviders(
    <>
      <TravelPage />
      <LocationProbe />
    </>,
    { router: { initialEntries: [url] } },
  )
}

let scroll: ReturnType<typeof vi.fn>
beforeEach(() => {
  vi.clearAllMocks()
  resetToasts()
  scroll = stubScrollIntoView()
})

describe('TravelPage: ?open=<id>&entity=... desde el buscador', () => {
  it('entity=trip abre el formulario del viaje y limpia la URL', async () => {
    mockTrips([trip('t1', 'Bariloche'), trip('t2', 'Lisboa')])
    renderAt('/travel?open=t2&entity=trip')

    expect(await screen.findByText('Editar viaje')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Lisboa')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(/^\/travel$/))
    expect(toastMessages()).toEqual([])
  })

  it('entity=packing_item expande el viaje padre y resalta el ítem del equipaje', async () => {
    mockTrips([trip('t1', 'Bariloche'), trip('t2', 'Lisboa')], {
      t2: [item('p1', 'Pasaporte'), item('p2', 'Cargador')],
    })
    renderAt('/travel?open=p2&entity=packing_item&parent=t2')

    await waitFor(() => expect(screen.getByText('Cargador').closest('#item-p2')).toHaveClass('search-reveal'))
    expect(scroll).toHaveBeenCalled()
    expect(screen.queryByText('Editar viaje')).not.toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(/^\/travel$/))
    expect(toastMessages()).toEqual([])
  })

  it('espera a que cargue el equipaje del viaje antes de decidir', async () => {
    mockTrips([trip('t2', 'Lisboa')], { t2: undefined })
    const { rerender } = renderAt('/travel?open=p1&entity=packing_item&parent=t2')
    expect(toastMessages()).toEqual([])
    expect(screen.getByTestId('location')).toHaveTextContent('open=p1')
    mockTrips([trip('t2', 'Lisboa')], { t2: [item('p1', 'Pasaporte')] })
    rerender(<><TravelPage /><LocationProbe /></>)
    await waitFor(() => expect(screen.getByText('Pasaporte').closest('#item-p1')).toHaveClass('search-reveal'))
  })

  it('si el ítem ya no está en el equipaje avisa', async () => {
    mockTrips([trip('t2', 'Lisboa')], { t2: [item('p1', 'Pasaporte')] })
    renderAt('/travel?open=borrado&entity=packing_item&parent=t2')

    await waitFor(() => expect(toastMessages()).toEqual(['Ese elemento ya no existe']))
    expect(scroll).not.toHaveBeenCalled()
  })

  it('si el viaje padre no existe avisa', async () => {
    mockTrips([trip('t1', 'Bariloche')])
    renderAt('/travel?open=p1&entity=packing_item&parent=fantasma')
    await waitFor(() => expect(toastMessages()).toEqual(['Ese elemento ya no existe']))
  })
})
