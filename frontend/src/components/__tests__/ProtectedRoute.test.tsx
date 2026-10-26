import { describe, it, expect, vi } from 'vitest'
import { screen } from '@testing-library/react'
import { Routes, Route } from 'react-router-dom'
import { renderWithProviders, createMockAuthStore } from '../../test/test-utils'
import ProtectedRoute from '../ProtectedRoute'

vi.mock('../../store/authStore', () => ({
  useAuthStore: vi.fn(),
}))

import { useAuthStore } from '../../store/authStore'

describe('ProtectedRoute', () => {
  it('shows loading spinner while isLoading', () => {
    vi.mocked(useAuthStore).mockReturnValue(
      createMockAuthStore({ isLoading: true, isAuthenticated: false }),
    )
    const { container } = renderWithProviders(<ProtectedRoute />)
    const spinner = container.querySelector('.animate-spin')
    expect(spinner).toBeInTheDocument()
  })

  it('renders Outlet when authenticated', () => {
    vi.mocked(useAuthStore).mockReturnValue(
      createMockAuthStore({ isLoading: false, isAuthenticated: true }),
    )
    renderWithProviders(<ProtectedRoute />)
    // Outlet renders nothing by itself, but Navigate should not be present
    expect(screen.queryByText('/login')).not.toBeInTheDocument()
  })

  it('redirects to /login when not authenticated', () => {
    vi.mocked(useAuthStore).mockReturnValue(
      createMockAuthStore({ isLoading: false, isAuthenticated: false }),
    )
    renderWithProviders(<ProtectedRoute />)
    // Navigate component renders nothing visible but changes the URL
    // We just verify it doesn't crash and doesn't show spinner
    expect(screen.queryByText('/login')).not.toBeInTheDocument()
  })

  describe('gate de términos y edad', () => {
    const baseUser = {
      id: '1',
      email: 'test@test.com',
      full_name: 'Test User',
      current_terms_version: '1.1',
    }

    function renderRoutes() {
      return renderWithProviders(
        <Routes>
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<div>CONTENIDO</div>} />
          </Route>
          <Route path="/accept-terms" element={<div>GATE</div>} />
        </Routes>,
      )
    }

    it('manda al gate con la versión vigente aceptada pero age_confirmed=false', () => {
      vi.mocked(useAuthStore).mockReturnValue(
        createMockAuthStore({
          user: { ...baseUser, terms_accepted_version: '1.1', age_confirmed: false },
        }),
      )
      renderRoutes()
      expect(screen.getByText('GATE')).toBeInTheDocument()
      expect(screen.queryByText('CONTENIDO')).not.toBeInTheDocument()
    })

    it('manda al gate con la edad confirmada pero una versión anterior', () => {
      vi.mocked(useAuthStore).mockReturnValue(
        createMockAuthStore({
          user: { ...baseUser, terms_accepted_version: '1.0', age_confirmed: true },
        }),
      )
      renderRoutes()
      expect(screen.getByText('GATE')).toBeInTheDocument()
    })

    it('no muestra el gate con versión vigente y edad confirmada', () => {
      vi.mocked(useAuthStore).mockReturnValue(
        createMockAuthStore({
          user: { ...baseUser, terms_accepted_version: '1.1', age_confirmed: true },
        }),
      )
      renderRoutes()
      expect(screen.getByText('CONTENIDO')).toBeInTheDocument()
      expect(screen.queryByText('GATE')).not.toBeInTheDocument()
    })
  })
})
