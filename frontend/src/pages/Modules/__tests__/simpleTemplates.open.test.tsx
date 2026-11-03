import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import type { ReactElement } from 'react'
import { renderWithProviders } from '../../../test/test-utils'
import { LocationProbe, toastMessages, resetToasts } from '../../../test/openParam'
import type { Book, MediaItem, WorkOpportunity } from '../../../types'

vi.mock('../../../hooks/useLibrary', () => ({
  useBooks: vi.fn(), useLibrarySummary: vi.fn(() => ({ data: undefined, isLoading: false })), removeBook: vi.fn(), saveBook: vi.fn(),
}))
vi.mock('../../../hooks/useMedia', () => ({
  useMediaItems: vi.fn(), useMediaSummary: vi.fn(() => ({ data: undefined, isLoading: false })), removeMediaItem: vi.fn(), saveMediaItem: vi.fn(),
}))
vi.mock('../../../hooks/useWork', () => ({
  useOpportunities: vi.fn(), useWorkSummary: vi.fn(() => ({ data: undefined, isLoading: false })), removeOpportunity: vi.fn(), saveOpportunity: vi.fn(),
}))

import { useBooks } from '../../../hooks/useLibrary'
import { useMediaItems } from '../../../hooks/useMedia'
import { useOpportunities } from '../../../hooks/useWork'
import LibraryPage from '../../Library/LibraryPage'
import MediaPage from '../../Media/MediaPage'
import WorkPage from '../../Work/WorkPage'

const swr = (data: unknown) => ({ data, isLoading: data === undefined, error: undefined }) as never

const book = (id: string, title: string): Book => ({
  id, title, author: null, status: 'pendiente', rating: null, pages: null, notes: null, started_date: null, finished_date: null,
})
const media = (id: string, title: string): MediaItem => ({
  id, title, media_type: 'pelicula', status: 'pendiente', rating: null, year: null, notes: null,
})
const opp = (id: string, company: string): WorkOpportunity => ({
  id, company, role: 'Dev', status: 'aplicado', salary: null, applied_date: null, notes: null,
})

function renderAt(page: ReactElement, url: string) {
  return renderWithProviders(
    <>
      {page}
      <LocationProbe />
    </>,
    { router: { initialEntries: [url] } },
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  resetToasts()
})

describe('Biblioteca: ?open=<id>&entity=book', () => {
  it('abre el formulario del libro y limpia la URL', async () => {
    vi.mocked(useBooks).mockReturnValue(swr([book('b1', 'Dune'), book('b2', 'Rayuela')]))
    renderAt(<LibraryPage />, '/library?open=b2&entity=book')

    expect(await screen.findByText('Editar libro')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Rayuela')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(/^\/library$/))
  })

  it('si el libro ya no existe avisa', async () => {
    vi.mocked(useBooks).mockReturnValue(swr([book('b1', 'Dune')]))
    renderAt(<LibraryPage />, '/library?open=zzz&entity=book')
    await waitFor(() => expect(toastMessages()).toEqual(['Ese elemento ya no existe']))
    expect(screen.queryByText('Editar libro')).not.toBeInTheDocument()
  })
})

describe('Películas y Series: ?open=<id>&entity=media_item', () => {
  it('abre el formulario del título y limpia la URL', async () => {
    vi.mocked(useMediaItems).mockReturnValue(swr([media('m1', 'Dark'), media('m2', 'Alien')]))
    renderAt(<MediaPage />, '/media?open=m2&entity=media_item')

    expect(await screen.findByText('Editar')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Alien')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(/^\/media$/))
  })

  it('si el título ya no existe avisa', async () => {
    vi.mocked(useMediaItems).mockReturnValue(swr([media('m1', 'Dark')]))
    renderAt(<MediaPage />, '/media?open=zzz&entity=media_item')
    await waitFor(() => expect(toastMessages()).toEqual(['Ese elemento ya no existe']))
  })
})

describe('Trabajo: ?open=<id>&entity=opportunity', () => {
  it('abre el formulario de la oportunidad y limpia la URL', async () => {
    vi.mocked(useOpportunities).mockReturnValue(swr([opp('o1', 'Acme'), opp('o2', 'Globex')]))
    renderAt(<WorkPage />, '/work?open=o2&entity=opportunity')

    expect(await screen.findByText('Editar oportunidad')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Globex')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(/^\/work$/))
  })

  it('espera a que carguen antes de decidir', async () => {
    vi.mocked(useOpportunities).mockReturnValue(swr(undefined))
    const { rerender } = renderAt(<WorkPage />, '/work?open=o1&entity=opportunity')
    expect(toastMessages()).toEqual([])
    vi.mocked(useOpportunities).mockReturnValue(swr([opp('o1', 'Acme')]))
    rerender(<><WorkPage /><LocationProbe /></>)
    expect(await screen.findByText('Editar oportunidad')).toBeInTheDocument()
  })
})
