import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'
import ForgotPasswordPage from '../ForgotPasswordPage'
import ResetPasswordPage from '../ResetPasswordPage'
import VerifyEmailPage from '../VerifyEmailPage'
import * as authApi from '../../../api/authApi'

vi.mock('../../../api/authApi', () => ({
  forgotPassword: vi.fn(),
  resetPassword: vi.fn(),
  verifyEmail: vi.fn(),
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('ForgotPasswordPage', () => {
  it('pide el link y muestra el aviso genérico', async () => {
    vi.mocked(authApi.forgotPassword).mockResolvedValue(undefined)
    renderWithProviders(<ForgotPasswordPage />)
    fireEvent.change(screen.getByPlaceholderText('tu@email.com'), { target: { value: 'a@b.com' } })
    fireEvent.click(screen.getByRole('button', { name: 'Enviar link' }))
    await waitFor(() => expect(authApi.forgotPassword).toHaveBeenCalledWith('a@b.com'))
    expect(await screen.findByText(/Si el email está registrado/)).toBeInTheDocument()
  })
})

describe('ResetPasswordPage', () => {
  const route = { router: { initialEntries: ['/resetear-password?token=tok123'] } }

  it('sin token en el link avisa que es inválido', () => {
    renderWithProviders(<ResetPasswordPage />)
    expect(screen.getByText('Link inválido')).toBeInTheDocument()
  })

  it('no manda nada si las contraseñas no coinciden', async () => {
    renderWithProviders(<ResetPasswordPage />, route)
    const [pw, repeat] = Array.from(document.querySelectorAll('input[type=password]'))
    fireEvent.change(pw, { target: { value: 'secreta1' } })
    fireEvent.change(repeat, { target: { value: 'otra-cosa' } })
    fireEvent.click(screen.getByRole('button', { name: 'Cambiar contraseña' }))
    expect(await screen.findByText(/no coinciden/)).toBeInTheDocument()
    expect(authApi.resetPassword).not.toHaveBeenCalled()
  })

  it('cambia la contraseña con el token del link', async () => {
    vi.mocked(authApi.resetPassword).mockResolvedValue(undefined)
    renderWithProviders(<ResetPasswordPage />, route)
    const [pw, repeat] = Array.from(document.querySelectorAll('input[type=password]'))
    fireEvent.change(pw, { target: { value: 'secreta1' } })
    fireEvent.change(repeat, { target: { value: 'secreta1' } })
    fireEvent.click(screen.getByRole('button', { name: 'Cambiar contraseña' }))
    await waitFor(() => expect(authApi.resetPassword).toHaveBeenCalledWith('tok123', 'secreta1'))
    expect(await screen.findByText(/cambiaste tu contraseña/)).toBeInTheDocument()
  })

  it('muestra el error de la API (link vencido)', async () => {
    vi.mocked(authApi.resetPassword).mockRejectedValue({
      response: { data: { detail: 'Link de recuperación inválido o vencido' } },
    })
    renderWithProviders(<ResetPasswordPage />, route)
    const [pw, repeat] = Array.from(document.querySelectorAll('input[type=password]'))
    fireEvent.change(pw, { target: { value: 'secreta1' } })
    fireEvent.change(repeat, { target: { value: 'secreta1' } })
    fireEvent.click(screen.getByRole('button', { name: 'Cambiar contraseña' }))
    expect(await screen.findByText(/inválido o vencido/)).toBeInTheDocument()
  })
})

describe('VerifyEmailPage', () => {
  it('verifica el token del link una sola vez', async () => {
    vi.mocked(authApi.verifyEmail).mockResolvedValue(undefined)
    renderWithProviders(<VerifyEmailPage />, { router: { initialEntries: ['/verificar-email?token=abc'] } })
    expect(await screen.findByText(/Confirmamos tu email/)).toBeInTheDocument()
    expect(authApi.verifyEmail).toHaveBeenCalledTimes(1)
    expect(authApi.verifyEmail).toHaveBeenCalledWith('abc')
  })

  it('muestra el error si el link venció', async () => {
    vi.mocked(authApi.verifyEmail).mockRejectedValue({
      response: { data: { detail: 'Link de verificación inválido o vencido' } },
    })
    renderWithProviders(<VerifyEmailPage />, { router: { initialEntries: ['/verificar-email?token=abc'] } })
    expect(await screen.findByText(/inválido o vencido/)).toBeInTheDocument()
  })
})
