import { describe, it, expect, vi } from 'vitest'
import { screen } from '@testing-library/react'
import { renderWithProviders, createMockAuthStore } from '../../test/test-utils'
import PublicFooter from '../PublicFooter'
import Layout from '../Layout'

vi.mock('../../store/authStore', () => ({
  useAuthStore: vi.fn(),
}))

import { useAuthStore } from '../../store/authStore'

describe('PublicFooter', () => {
  it('shows the legal links, including the withdrawal button', () => {
    renderWithProviders(<PublicFooter />)
    expect(screen.getByRole('link', { name: 'Términos y Condiciones' })).toHaveAttribute('href', '/terms')
    expect(screen.getByRole('link', { name: 'Política de Privacidad' })).toHaveAttribute('href', '/privacy')
    expect(screen.getByRole('link', { name: /Botón de arrepentimiento/ })).toHaveAttribute(
      'href',
      '/arrepentimiento',
    )
  })

  it('is also reachable from the authenticated app layout', () => {
    vi.mocked(useAuthStore).mockReturnValue(createMockAuthStore())
    renderWithProviders(<Layout />)
    const links = screen.getAllByRole('link', { name: /Botón de arrepentimiento/ })
    expect(links.length).toBeGreaterThanOrEqual(1)
    links.forEach((l) => expect(l).toHaveAttribute('href', '/arrepentimiento'))
  })
})
