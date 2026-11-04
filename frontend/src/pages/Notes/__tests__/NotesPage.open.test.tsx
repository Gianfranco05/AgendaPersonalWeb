import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'
import { LocationProbe, toastMessages, resetToasts } from '../../../test/openParam'
import type { Note } from '../../../types'

vi.mock('../../../api/endpoints', () => ({
  fetchNotes: vi.fn(),
  createNote: vi.fn(),
  updateNote: vi.fn(),
  deleteNote: vi.fn(),
  exportNotesJson: vi.fn(),
}))

import { fetchNotes } from '../../../api/endpoints'
import NotesPage from '../NotesPage'

const note = (over: Partial<Note>): Note => ({
  id: 'n1',
  title: 'Primera',
  content: '',
  is_pinned: false,
  is_archived: false,
  color: '#7C3AED',
  tags: [],
  created_at: '2025-06-01T10:00:00',
  updated_at: '2025-06-01T10:00:00',
  ...over,
})

function renderAt(url: string) {
  return renderWithProviders(
    <>
      <NotesPage />
      <LocationProbe />
    </>,
    { router: { initialEntries: [url] } },
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  resetToasts()
})

describe('NotesPage: ?open=<id> desde el buscador', () => {
  it('abre en el editor la nota pedida (no la primera) y limpia la URL', async () => {
    vi.mocked(fetchNotes).mockResolvedValue([
      note({ id: 'n1', title: 'Primera', updated_at: '2025-06-09T10:00:00' }),
      note({ id: 'n2', title: 'Segunda' }),
    ])
    renderAt('/notes?open=n2')

    expect(await screen.findByDisplayValue('Segunda')).toBeInTheDocument()
    expect(screen.queryByDisplayValue('Primera')).not.toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(/^\/notes$/))
    expect(toastMessages()).toEqual([])
  })

  it('si la nota está archivada (la lista normal no la trae) la pide aparte y la abre', async () => {
    vi.mocked(fetchNotes).mockImplementation(async (includeArchived?: boolean) =>
      includeArchived
        ? [note({ id: 'n1' }), note({ id: 'n9', title: 'Vieja archivada', is_archived: true })]
        : [note({ id: 'n1' })],
    )
    renderAt('/notes?open=n9')

    expect(await screen.findByDisplayValue('Vieja archivada')).toBeInTheDocument()
    expect(fetchNotes).toHaveBeenCalledWith(true)
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(/^\/notes$/))
  })

  it('si el id no existe avisa y deja la lista', async () => {
    vi.mocked(fetchNotes).mockResolvedValue([note({ id: 'n1', title: 'Primera' })])
    renderAt('/notes?open=nope')

    await waitFor(() => expect(toastMessages()).toEqual(['Ese elemento ya no existe']))
    expect(screen.getByTestId('location')).toHaveTextContent(/^\/notes$/)
    expect(screen.getByDisplayValue('Primera')).toBeInTheDocument()
  })
})
