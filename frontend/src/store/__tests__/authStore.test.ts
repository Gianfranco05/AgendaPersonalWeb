import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useAuthStore } from '../authStore'
import * as authApi from '../../api/authApi'
import { mutate as swrMutate } from 'swr'

vi.mock('swr', async () => {
  const actual = await vi.importActual('swr')
  return { ...(actual as object), mutate: vi.fn() }
})

vi.mock('../../api/authApi', () => ({
  login: vi.fn(),
  logout: vi.fn(),
  getMe: vi.fn(),
  updateProfile: vi.fn(),
  acceptTerms: vi.fn(),
}))

const user = {
  id: '1',
  email: 'a@b.com',
  full_name: 'A B',
  terms_accepted_version: '1',
  current_terms_version: '1',
}

beforeEach(() => {
  vi.clearAllMocks()
  useAuthStore.setState({ user, isAuthenticated: true, isLoading: false })
})

describe('authStore.logout', () => {
  it('cierra la sesión local y no rechaza aunque el server falle', async () => {
    vi.mocked(authApi.logout).mockRejectedValue(new Error('Network Error'))
    await expect(useAuthStore.getState().logout()).resolves.toBeUndefined()
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
    expect(useAuthStore.getState().user).toBeNull()
  })

  it('cierra la sesión local cuando el server responde', async () => {
    vi.mocked(authApi.logout).mockResolvedValue(undefined)
    await useAuthStore.getState().logout()
    expect(authApi.logout).toHaveBeenCalledTimes(1)
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
  })
})

describe('caché de SWR entre sesiones', () => {
  it('se vacía al cerrar sesión, para que el próximo usuario no vea datos ajenos', async () => {
    vi.mocked(authApi.logout).mockResolvedValue(undefined)
    await useAuthStore.getState().logout()
    expect(swrMutate).toHaveBeenCalledWith(expect.any(Function), undefined, { revalidate: false })
    const matcher = vi.mocked(swrMutate).mock.calls[0][0] as (key: unknown) => boolean
    expect(matcher('finance/summary')).toBe(true)
    expect(matcher(['finance/budgets', 2026, 10])).toBe(true)
  })

  it('se vacía al iniciar sesión', async () => {
    vi.mocked(authApi.login).mockResolvedValue(user)
    await useAuthStore.getState().login('a@b.com', 'x')
    expect(swrMutate).toHaveBeenCalledTimes(1)
  })
})
