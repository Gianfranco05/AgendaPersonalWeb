import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useAuthStore } from '../authStore'
import * as authApi from '../../api/authApi'

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
