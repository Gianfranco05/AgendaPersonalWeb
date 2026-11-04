import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen, fireEvent, act } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'
import NoteEditor from '../NoteEditor'

const baseNote = {
  id: 'n1',
  title: 'Test Note',
  content: '# Hello',
  is_pinned: false,
  is_archived: false,
  color: '#7C3AED',
  tags: [],
  created_at: '2025-06-01T10:00:00',
  updated_at: '2025-06-01T10:00:00',
}

const defaultProps = {
  onSave: vi.fn(),
  onDelete: vi.fn(),
  onColorChange: vi.fn(),
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('NoteEditor', () => {
  it('pre-fills title and shows editor', () => {
    renderWithProviders(<NoteEditor note={baseNote} {...defaultProps} />)
    expect(screen.getByDisplayValue('Test Note')).toBeInTheDocument()
  })

  describe('autosave', () => {
    beforeEach(() => {
      vi.useFakeTimers()
    })
    afterEach(() => {
      vi.useRealTimers()
    })

    it('no guarda si no se editó nada', () => {
      renderWithProviders(<NoteEditor note={baseNote} {...defaultProps} />)
      act(() => {
        vi.advanceTimersByTime(10_000)
      })
      expect(defaultProps.onSave).not.toHaveBeenCalled()
    })

    it('guarda una sola vez tras editar, aunque el padre reemplace la nota', () => {
      const { rerender } = renderWithProviders(<NoteEditor note={baseNote} {...defaultProps} />)
      fireEvent.change(screen.getByDisplayValue('Test Note'), { target: { value: 'Editada' } })
      act(() => {
        vi.advanceTimersByTime(1000)
      })
      expect(defaultProps.onSave).toHaveBeenCalledTimes(1)
      expect(defaultProps.onSave).toHaveBeenCalledWith(expect.objectContaining({ title: 'Editada' }))

      // El padre reemplaza la nota por la guardada (objeto nuevo, y un onSave nuevo
      // en cada render): antes eso reprogramaba el autosave en loop, un PUT por segundo.
      const saved = { ...baseNote, title: 'Editada', updated_at: '2025-06-01T10:05:00' }
      rerender(<NoteEditor note={saved} {...defaultProps} onSave={(n) => defaultProps.onSave(n)} />)
      act(() => {
        vi.advanceTimersByTime(10_000)
      })
      expect(defaultProps.onSave).toHaveBeenCalledTimes(1)
    })

    it('guarda lo pendiente al desmontar (cambio de nota)', () => {
      const { unmount } = renderWithProviders(<NoteEditor note={baseNote} {...defaultProps} />)
      fireEvent.change(screen.getByDisplayValue('Test Note'), { target: { value: 'Casi perdida' } })
      unmount()
      expect(defaultProps.onSave).toHaveBeenCalledTimes(1)
      expect(defaultProps.onSave).toHaveBeenCalledWith(expect.objectContaining({ title: 'Casi perdida' }))
    })
  })
})
