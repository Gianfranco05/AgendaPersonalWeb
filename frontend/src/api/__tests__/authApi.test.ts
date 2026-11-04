import { describe, it, expect, vi, beforeEach } from 'vitest'

const { mockPost } = vi.hoisted(() => ({ mockPost: vi.fn() }))

vi.mock('../client', () => ({
  default: { get: vi.fn(), post: mockPost, patch: vi.fn() },
}))

import { register, acceptTerms } from '../authApi'

beforeEach(() => {
  vi.clearAllMocks()
  mockPost.mockResolvedValue({ data: {} })
})

describe('authApi — declaración de edad mínima', () => {
  it('register manda confirm_age junto con accept_terms (misma casilla)', async () => {
    await register('Ana', 'ana@example.com', 'secreta1', true)
    expect(mockPost).toHaveBeenCalledWith('/auth/api/register', {
      full_name: 'Ana',
      email: 'ana@example.com',
      password: 'secreta1',
      accept_terms: true,
      confirm_age: true,
    })
  })

  it('acceptTerms manda la versión que se está mostrando y confirm_age: true', async () => {
    await acceptTerms('1.1')
    expect(mockPost).toHaveBeenCalledWith('/auth/api/accept-terms', {
      version: '1.1',
      confirm_age: true,
    })
  })
})
