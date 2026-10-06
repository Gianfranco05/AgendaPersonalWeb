import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'

vi.mock('../../../hooks/useStore', () => ({
  useStore: vi.fn(),
  startCheckout: vi.fn(),
  revalidateAfterPurchase: vi.fn(),
}))
vi.mock('../../../api/authApi', () => ({
  requestEmailVerification: vi.fn(),
}))

import { useStore, startCheckout } from '../../../hooks/useStore'
import { requestEmailVerification } from '../../../api/authApi'
import StorePage from '../StorePage'

const store = {
  billing_enabled: true,
  items: [
    { key: 'study', label: 'Estudio', description: 'Materias', icon: 'school', owned: false, amount: 1500000, currency: 'ars' },
  ],
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(useStore).mockReturnValue({ data: store, isLoading: false, error: undefined, isValidating: false, mutate: vi.fn() })
})

describe('StorePage', () => {
  it('ofrece reenviar el mail si la API exige email verificado (403)', async () => {
    vi.mocked(startCheckout).mockRejectedValue({
      response: { status: 403, data: { detail: 'Tenés que verificar tu email antes de comprar una plantilla' } },
    })
    vi.mocked(requestEmailVerification).mockResolvedValue(undefined)
    renderWithProviders(<StorePage />)

    fireEvent.click(screen.getByRole('button', { name: /Comprar/ }))
    expect(await screen.findByText(/verificar tu email/)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Reenviar mail de verificación' }))
    await waitFor(() => expect(requestEmailVerification).toHaveBeenCalledTimes(1))
    expect(await screen.findByText(/Te mandamos el mail/)).toBeInTheDocument()
  })

  it('un error de validación (422, lista) no se muestra como [object Object]', async () => {
    vi.mocked(startCheckout).mockRejectedValue({
      response: { status: 422, data: { detail: [{ msg: 'Plantilla inválida' }] } },
    })
    renderWithProviders(<StorePage />)
    fireEvent.click(screen.getByRole('button', { name: /Comprar/ }))
    expect(await screen.findByText('Plantilla inválida')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Reenviar mail de verificación' })).not.toBeInTheDocument()
  })
})
