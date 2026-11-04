import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'
import { LocationProbe, toastMessages, resetToasts } from '../../../test/openParam'
import type { CalendarEvent } from '../../../types'

vi.mock('../../../hooks/useEvents', () => ({
  useEvents: vi.fn(),
  addEvent: vi.fn(),
  editEvent: vi.fn(),
  removeEvent: vi.fn(),
}))
vi.mock('../../../api/endpoints', () => ({ exportEventsIcs: vi.fn() }))

import { useEvents } from '../../../hooks/useEvents'
import EventsPage from '../EventsPage'

const event = (over: Partial<CalendarEvent>): CalendarEvent => ({
  id: 'e1', title: 'Reunión', start_datetime: '2027-03-15T10:30:00', is_all_day: false, color: '#7C3AED', ...over,
})

function mockEvents(data: CalendarEvent[] | undefined) {
  vi.mocked(useEvents).mockReturnValue({
    data, isLoading: data === undefined, error: undefined, isValidating: false, mutate: vi.fn(),
  } as never)
}

function renderAt(url: string) {
  return renderWithProviders(
    <>
      <EventsPage />
      <LocationProbe />
    </>,
    { router: { initialEntries: [url] } },
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  resetToasts()
})

describe('EventsPage: ?open=<id> desde el buscador', () => {
  it('abre el formulario de edición del evento y limpia la URL', async () => {
    mockEvents([event({ id: 'e1' }), event({ id: 'e2', title: 'Dentista', location: 'Centro' })])
    renderAt('/events?open=e2')

    expect(await screen.findByText('Editar evento')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Dentista')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Centro')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(/^\/events$/))
    expect(toastMessages()).toEqual([])
  })

  it('mueve el calendario al mes del evento (que no es el actual)', async () => {
    mockEvents([event({ id: 'e1', start_datetime: '2027-03-15T10:30:00' })])
    renderAt('/events?open=e1')

    await screen.findByText('Editar evento')
    expect(screen.getByText(/marzo 2027/i)).toBeInTheDocument()
  })

  it('espera a que carguen los eventos antes de decidir', async () => {
    mockEvents(undefined)
    const { rerender } = renderAt('/events?open=e1')
    expect(toastMessages()).toEqual([])
    mockEvents([event({ id: 'e1' })])
    rerender(<><EventsPage /><LocationProbe /></>)
    expect(await screen.findByText('Editar evento')).toBeInTheDocument()
  })

  it('si el id no existe avisa y no abre ningún formulario', async () => {
    mockEvents([event({ id: 'e1' })])
    renderAt('/events?open=borrado')

    await waitFor(() => expect(toastMessages()).toEqual(['Ese elemento ya no existe']))
    expect(screen.queryByText('Editar evento')).not.toBeInTheDocument()
    expect(screen.getByTestId('location')).toHaveTextContent(/^\/events$/)
  })
})
