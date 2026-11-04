import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen, fireEvent } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'
import NoteCard from '../NoteCard'

const note = {
  id: 'n1',
  title: 'Mi nota',
  content: 'contenido',
  is_pinned: false,
  is_archived: false,
  color: '#7C3AED',
  tags: [],
  created_at: '2026-10-06T17:00:00',
  updated_at: '2026-10-06T17:00:00',
}

const props = { note, isSelected: false, onSelect: vi.fn(), onPin: vi.fn(), onDelete: vi.fn() }

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('NoteCard', () => {
  it('no anida un button dentro de otro button', () => {
    const { container } = renderWithProviders(<NoteCard {...props} />)
    expect(container.querySelector('button button')).toBeNull()
  })

  it('seleccionar la nota no dispara fijar ni borrar', () => {
    renderWithProviders(<NoteCard {...props} />)
    fireEvent.click(screen.getByText('Mi nota'))
    expect(props.onSelect).toHaveBeenCalledTimes(1)
    expect(props.onPin).not.toHaveBeenCalled()
    expect(props.onDelete).not.toHaveBeenCalled()
  })

  it('pide confirmación antes de borrar', () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderWithProviders(<NoteCard {...props} />)
    fireEvent.click(screen.getByTitle('Eliminar'))
    expect(props.onDelete).not.toHaveBeenCalled()

    confirm.mockReturnValue(true)
    fireEvent.click(screen.getByTitle('Eliminar'))
    expect(props.onDelete).toHaveBeenCalledTimes(1)
    expect(props.onSelect).not.toHaveBeenCalled()
  })
})
