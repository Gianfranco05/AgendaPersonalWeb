import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'

const mockResponseUse = vi.fn()
const mockAxiosInstance = {
  defaults: {} as Record<string, unknown>,
  interceptors: {
    request: { use: vi.fn() },
    response: { use: mockResponseUse },
  },
}

vi.mock('axios', () => {
  const mockAxios = vi.fn()
  mockAxios.create = vi.fn(() => mockAxiosInstance)
  return { default: mockAxios }
})

describe('apiClient', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.resetModules()
    vi.unstubAllEnvs()
  })

  describe('configuration', () => {
    it('uses VITE_API_URL as baseURL when set', async () => {
      vi.stubEnv('VITE_API_URL', 'http://localhost:8000')
      await import('../client')
      expect(axios.create).toHaveBeenCalledWith(
        expect.objectContaining({ baseURL: 'http://localhost:8000' }),
      )
    })

    it('falls back to empty baseURL when VITE_API_URL is not set', async () => {
      await import('../client')
      expect(axios.create).toHaveBeenCalledWith(
        expect.objectContaining({ baseURL: '' }),
      )
    })

    it('sets withCredentials to true', async () => {
      await import('../client')
      expect(axios.create).toHaveBeenCalledWith(
        expect.objectContaining({ withCredentials: true }),
      )
    })

    it('sets Content-Type header to application/json', async () => {
      await import('../client')
      expect(axios.create).toHaveBeenCalledWith(
        expect.objectContaining({
          headers: { 'Content-Type': 'application/json' },
        }),
      )
    })
  })

  describe('401 interceptor', () => {
    let fulfilledFn: (res: unknown) => unknown
    let rejectedFn: (err: unknown) => Promise<unknown>

    beforeEach(async () => {
      mockResponseUse.mockClear()
      vi.resetModules()
      await import('../client')
      fulfilledFn = mockResponseUse.mock.calls[0][0]
      rejectedFn = mockResponseUse.mock.calls[0][1]
    })

    it('passes through successful responses', () => {
      const response = { status: 200, data: 'ok' }
      expect(fulfilledFn(response)).toBe(response)
    })

    it('redirects to /login on 401', async () => {
      const originalLocation = window.location
      const mockLocation = { href: '' } as Location
      delete (window as any).location
      ;(window as any).location = mockLocation

      const error = { response: { status: 401 } }
      await expect(rejectedFn(error)).rejects.toBe(error)
      expect(mockLocation.href).toBe('/login')

      ;(window as any).location = originalLocation
    })

    it('rejects non-401 errors without redirect', async () => {
      const error403 = { response: { status: 403 } }
      await expect(rejectedFn(error403)).rejects.toBe(error403)

      const error500 = { response: { status: 500 } }
      await expect(rejectedFn(error500)).rejects.toBe(error500)
    })
  })
})
