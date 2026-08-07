import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import axios from 'axios'

const mockResponseUse = vi.fn()
const mockPost = vi.fn()

// La instancia tiene que ser invocable: el interceptor reintenta con `apiClient(config)`.
const mockAxiosInstance = Object.assign(vi.fn(), {
  defaults: {} as Record<string, unknown>,
  post: mockPost,
  interceptors: {
    request: { use: vi.fn() },
    response: { use: mockResponseUse },
  },
})

vi.mock('axios', () => {
  const mockAxios = Object.assign(vi.fn(), {
    create: vi.fn(() => mockAxiosInstance),
  })
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
    let originalLocation: Location
    let mockLocation: Location

    beforeEach(async () => {
      mockResponseUse.mockClear()
      mockPost.mockReset()
      mockAxiosInstance.mockReset()
      vi.resetModules()
      await import('../client')
      fulfilledFn = mockResponseUse.mock.calls[0][0]
      rejectedFn = mockResponseUse.mock.calls[0][1]

      originalLocation = window.location
      mockLocation = { href: '', pathname: '/dashboard' } as Location
      delete (window as any).location
      ;(window as any).location = mockLocation
    })

    afterEach(() => {
      ;(window as any).location = originalLocation
    })

    it('passes through successful responses', () => {
      const response = { status: 200, data: 'ok' }
      expect(fulfilledFn(response)).toBe(response)
    })

    it('refreshes and retries the original request on 401', async () => {
      mockPost.mockResolvedValue({ status: 200 })
      mockAxiosInstance.mockResolvedValue({ status: 200, data: 'retried' })

      const config = { url: '/api/v1/tasks' }
      const error = { response: { status: 401 }, config }

      await expect(rejectedFn(error)).resolves.toEqual({
        status: 200,
        data: 'retried',
      })
      expect(mockPost).toHaveBeenCalledWith('/auth/api/refresh', {})
      expect(mockAxiosInstance).toHaveBeenCalledWith(config)
      expect(mockLocation.href).toBe('')
    })

    it('logs out when the refresh itself fails', async () => {
      mockPost.mockRejectedValue(new Error('refresh expirado'))

      const error = { response: { status: 401 }, config: { url: '/api/v1/tasks' } }
      await expect(rejectedFn(error)).rejects.toBe(error)
      expect(mockLocation.href).toBe('/login')
    })

    it('does not retry a request that was already retried', async () => {
      const error = {
        response: { status: 401 },
        config: { url: '/api/v1/tasks', _retried: true },
      }
      await expect(rejectedFn(error)).rejects.toBe(error)
      expect(mockPost).not.toHaveBeenCalled()
    })

    it('does not attempt refresh on login failures', async () => {
      const error = { response: { status: 401 }, config: { url: '/auth/api/login' } }
      await expect(rejectedFn(error)).rejects.toBe(error)
      expect(mockPost).not.toHaveBeenCalled()
      expect(mockLocation.href).toBe('')
    })

    it('shares a single refresh across concurrent 401s', async () => {
      mockPost.mockResolvedValue({ status: 200 })
      mockAxiosInstance.mockResolvedValue({ status: 200 })

      await Promise.all([
        rejectedFn({ response: { status: 401 }, config: { url: '/api/v1/tasks' } }),
        rejectedFn({ response: { status: 401 }, config: { url: '/api/v1/notes' } }),
        rejectedFn({ response: { status: 401 }, config: { url: '/api/v1/goals' } }),
      ])

      // Sin single-flight serían 3 refreshes, y la rotación de tokens del backend
      // invalidaría los dos últimos cerrando la sesión.
      expect(mockPost).toHaveBeenCalledTimes(1)
    })

    it('rejects non-401 errors without refresh or redirect', async () => {
      const error403 = { response: { status: 403 }, config: { url: '/api/v1/tasks' } }
      await expect(rejectedFn(error403)).rejects.toBe(error403)

      const error500 = { response: { status: 500 }, config: { url: '/api/v1/tasks' } }
      await expect(rejectedFn(error500)).rejects.toBe(error500)

      expect(mockPost).not.toHaveBeenCalled()
      expect(mockLocation.href).toBe('')
    })
  })
})
