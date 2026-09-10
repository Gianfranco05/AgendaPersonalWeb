import { describe, it, expect, vi } from 'vitest'
import { screen } from '@testing-library/react'
import { renderWithProviders, createMockAuthStore } from '../../test/test-utils'
import Layout from '../Layout'

vi.mock('../../store/authStore', () => ({
  useAuthStore: vi.fn(),
}))

import { useAuthStore } from '../../store/authStore'

describe('Layout', () => {
  it('renders all nav items', () => {
    vi.mocked(useAuthStore).mockReturnValue(createMockAuthStore())
    renderWithProviders(<Layout />)
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Finanzas')).toBeInTheDocument()
    expect(screen.getByText('Eventos')).toBeInTheDocument()
    expect(screen.getByText('Metas')).toBeInTheDocument()
    expect(screen.getByText('Notas')).toBeInTheDocument()
    expect(screen.getByText('Tareas')).toBeInTheDocument()
    expect(screen.getByText('Configuración')).toBeInTheDocument()
  })

  it('shows user initials and name', () => {
    vi.mocked(useAuthStore).mockReturnValue(
      createMockAuthStore({
        user: {
          id: '1',
          email: 'gf@test.com',
          full_name: 'Gianfranco Ferraro',
          terms_accepted_version: '1.0',
          current_terms_version: '1.0',
        },
      }),
    )
    renderWithProviders(<Layout />)
    expect(screen.getByText('GF')).toBeInTheDocument()
    expect(screen.getByText('Gianfranco Ferraro')).toBeInTheDocument()
  })

  it('shows fallback for null user', () => {
    vi.mocked(useAuthStore).mockReturnValue(
      createMockAuthStore({ user: null, isAuthenticated: false }),
    )
    renderWithProviders(<Layout />)
    expect(screen.getByText('U')).toBeInTheDocument()
    expect(screen.getByText('Usuario')).toBeInTheDocument()
  })
})
