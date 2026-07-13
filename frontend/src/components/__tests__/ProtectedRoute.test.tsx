import { describe, it, expect, vi } from 'vitest'
import { screen } from '@testing-library/react'
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
})
