import { type ReactElement } from 'react'
import { render, type RenderOptions } from '@testing-library/react'
import { MemoryRouter, type MemoryRouterProps } from 'react-router-dom'
import { SWRConfig } from 'swr'
import { ThemeProvider } from '../context/ThemeContext'

interface WrapperOptions {
  router?: MemoryRouterProps
  swrFallback?: Record<string, unknown>
}

function createWrapper({ router, swrFallback }: WrapperOptions = {}) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <SWRConfig value={{ provider: () => new Map(), fallback: swrFallback }}>
        <ThemeProvider>
          <MemoryRouter {...router}>{children}</MemoryRouter>
        </ThemeProvider>
      </SWRConfig>
    )
  }
}

export function renderWithProviders(
  ui: ReactElement,
  options?: WrapperOptions & Omit<RenderOptions, 'wrapper'>,
) {
  const { router, swrFallback, ...renderOptions } = options ?? {}
  return render(ui, { wrapper: createWrapper({ router, swrFallback }), ...renderOptions })
}

export function createMockAuthStore(overrides?: Partial<{
  user: { id: string; email: string; full_name: string } | null
  isAuthenticated: boolean
  isLoading: boolean
}>) {
  return {
    user: { id: '1', email: 'test@test.com', full_name: 'Test User' },
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    checkAuth: vi.fn(),
    ...overrides,
  }
}
