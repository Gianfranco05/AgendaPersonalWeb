import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders, createMockAuthStore } from '../../../test/test-utils'
import WithdrawalPage from '../WithdrawalPage'

vi.mock('../../../store/authStore', () => ({
  useAuthStore: vi.fn(),
}))

vi.mock('../../../api/endpoints', () => ({
  createWithdrawalRequest: vi.fn(),
}))

import { useAuthStore } from '../../../store/authStore'
import { createWithdrawalRequest } from '../../../api/endpoints'

function mockStore(overrides?: Parameters<typeof createMockAuthStore>[0]) {
  const store = createMockAuthStore(overrides)
  vi.mocked(useAuthStore).mockImplementation(((selector: (s: typeof store) => unknown) =>
    selector(store)) as never)
}

async function fillAndSubmit(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText('Nombre y apellido'), 'Ana Perez')
  await user.type(screen.getByLabelText('Email'), 'ana@example.com')
  await user.type(screen.getByLabelText('Plantilla / compra'), 'Estudio, 3/10, op 123')
  await user.click(screen.getByRole('button', { name: 'Solicitar la revocación' }))
}

describe('WithdrawalPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockStore({ user: null, isAuthenticated: false })
  })

  it('is usable without a session and links back to the legal footer', () => {
    renderWithProviders(<WithdrawalPage />)
    expect(screen.getByRole('heading', { name: 'Botón de arrepentimiento' })).toBeInTheDocument()
    expect(screen.getByText(/No hace falta tener cuenta/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Botón de arrepentimiento/ })).toHaveAttribute(
      'href',
      '/arrepentimiento',
    )
  })

  it('shows the tracking code after a successful request', async () => {
    vi.mocked(createWithdrawalRequest).mockResolvedValue({
      code: 'ARR-ABC234',
      created_at: '2026-10-06T12:00:00Z',
    })
    const user = userEvent.setup()
    renderWithProviders(<WithdrawalPage />)

    await fillAndSubmit(user)

    expect(await screen.findByTestId('withdrawal-code')).toHaveTextContent('ARR-ABC234')
    expect(screen.getByText('ana@example.com')).toBeInTheDocument()
    expect(createWithdrawalRequest).toHaveBeenCalledWith({
      full_name: 'Ana Perez',
      email: 'ana@example.com',
      purchase_detail: 'Estudio, 3/10, op 123',
      message: undefined,
    })
  })

  it('validates required fields before calling the API', async () => {
    const user = userEvent.setup()
    renderWithProviders(<WithdrawalPage />)

    await user.click(screen.getByRole('button', { name: 'Solicitar la revocación' }))

    expect(await screen.findByText('Ingresá tu nombre y apellido')).toBeInTheDocument()
    expect(screen.getByText('Email inválido')).toBeInTheDocument()
    expect(screen.getByText('Contanos qué compra querés revocar')).toBeInTheDocument()
    expect(createWithdrawalRequest).not.toHaveBeenCalled()
  })

  it('shows a friendly message on 429', async () => {
    vi.mocked(createWithdrawalRequest).mockRejectedValue({ response: { status: 429 } })
    const user = userEvent.setup()
    renderWithProviders(<WithdrawalPage />)

    await fillAndSubmit(user)

    expect(await screen.findByRole('alert')).toHaveTextContent(/varios pedidos seguidos/)
    expect(screen.queryByTestId('withdrawal-code')).not.toBeInTheDocument()
  })

  it('shows a generic message on network errors', async () => {
    vi.mocked(createWithdrawalRequest).mockRejectedValue(new Error('Network Error'))
    const user = userEvent.setup()
    renderWithProviders(<WithdrawalPage />)

    await fillAndSubmit(user)

    expect(await screen.findByRole('alert')).toHaveTextContent(/No pudimos registrar/)
  })

  it('prefills name and email when there is a session', async () => {
    mockStore()
    renderWithProviders(<WithdrawalPage />)

    await waitFor(() => expect(screen.getByLabelText('Email')).toHaveValue('test@test.com'))
    expect(screen.getByLabelText('Nombre y apellido')).toHaveValue('Test User')
  })
})
