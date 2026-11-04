import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '../../../test/test-utils'
import RegisterPage from '../RegisterPage'
import * as authApi from '../../../api/authApi'

vi.mock('../../../api/authApi', () => ({
  register: vi.fn(),
}))

async function fillForm(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByPlaceholderText('Tu nombre'), 'Ana')
  await user.type(screen.getByPlaceholderText('tu@email.com'), 'ana@example.com')
  await user.type(screen.getByPlaceholderText('Mínimo 6 caracteres'), 'secreta1')
}

describe('RegisterPage — edad mínima', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('muestra una sola casilla con la declaración de 16 años y la ayuda para menores de 18', () => {
    renderWithProviders(<RegisterPage />)
    expect(screen.getAllByRole('checkbox')).toHaveLength(1)
    expect(screen.getByText(/Tengo 16 años o más y acepto los/)).toBeInTheDocument()
    expect(
      screen.getByText('Si tenés menos de 18, necesitás el consentimiento de tu madre, padre o tutor.'),
    ).toBeInTheDocument()
  })

  it('no envía sin tildar la casilla y muestra el error', async () => {
    const user = userEvent.setup()
    renderWithProviders(<RegisterPage />)
    await fillForm(user)
    await user.click(screen.getByRole('button', { name: 'Crear cuenta' }))

    expect(
      await screen.findByText('Tenés que confirmar tu edad y aceptar los Términos para continuar'),
    ).toBeInTheDocument()
    expect(authApi.register).not.toHaveBeenCalled()
  })

  it('al tildarla envía la aceptación (accept_terms y confirm_age en true)', async () => {
    vi.mocked(authApi.register).mockResolvedValue(undefined)
    const user = userEvent.setup()
    renderWithProviders(<RegisterPage />)
    await fillForm(user)
    await user.click(screen.getByRole('checkbox'))
    await user.click(screen.getByRole('button', { name: 'Crear cuenta' }))

    await waitFor(() =>
      expect(authApi.register).toHaveBeenCalledWith('Ana', 'ana@example.com', 'secreta1', true),
    )
  })
})
