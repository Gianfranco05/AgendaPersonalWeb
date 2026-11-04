import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders, createMockAuthStore } from '../../../test/test-utils'
import AcceptTermsPage from '../AcceptTermsPage'

vi.mock('../../../store/authStore', () => ({
  useAuthStore: vi.fn(),
}))

import { useAuthStore } from '../../../store/authStore'

function mockStore(overrides?: Parameters<typeof createMockAuthStore>[0]) {
  const store = createMockAuthStore(overrides)
  vi.mocked(useAuthStore).mockImplementation(((selector?: (s: typeof store) => unknown) =>
    selector ? selector(store) : store) as never)
  return store
}

const baseUser = {
  id: '1',
  email: 'a@b.com',
  full_name: 'A B',
  current_terms_version: '1.1',
}

describe('AcceptTermsPage — edad mínima', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('el botón queda deshabilitado hasta tildar la casilla de 16 años', async () => {
    mockStore({ user: { ...baseUser, terms_accepted_version: '1.0', age_confirmed: false } })
    const user = userEvent.setup()
    renderWithProviders(<AcceptTermsPage />)

    expect(
      screen.getByText(/Tengo 16 años o más y acepto los Términos y Condiciones/),
    ).toBeInTheDocument()
    expect(
      screen.getByText('Si tenés menos de 18, necesitás el consentimiento de tu madre, padre o tutor.'),
    ).toBeInTheDocument()
    const button = screen.getByRole('button', { name: 'Aceptar y continuar' })
    expect(button).toBeDisabled()

    await user.click(screen.getByRole('checkbox'))
    expect(button).toBeEnabled()
  })

  it('cuenta nueva (sin versión aceptada): título "Antes de empezar"', () => {
    mockStore({ user: { ...baseUser, terms_accepted_version: null, age_confirmed: false } })
    renderWithProviders(<AcceptTermsPage />)
    expect(screen.getByRole('heading', { name: 'Antes de empezar' })).toBeInTheDocument()
  })

  it('cuenta con una versión anterior: título "Actualizamos nuestros Términos"', () => {
    mockStore({ user: { ...baseUser, terms_accepted_version: '1.0', age_confirmed: false } })
    renderWithProviders(<AcceptTermsPage />)
    expect(
      screen.getByRole('heading', { name: 'Actualizamos nuestros Términos' }),
    ).toBeInTheDocument()
  })

  it('al aceptar llama a acceptTerms del store', async () => {
    const store = mockStore({
      user: { ...baseUser, terms_accepted_version: null, age_confirmed: false },
    })
    store.acceptTerms.mockResolvedValue(undefined)
    const user = userEvent.setup()
    renderWithProviders(<AcceptTermsPage />)

    await user.click(screen.getByRole('checkbox'))
    await user.click(screen.getByRole('button', { name: 'Aceptar y continuar' }))
    await waitFor(() => expect(store.acceptTerms).toHaveBeenCalledTimes(1))
  })
})
