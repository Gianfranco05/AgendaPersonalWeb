import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen } from '@testing-library/react'
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
})
