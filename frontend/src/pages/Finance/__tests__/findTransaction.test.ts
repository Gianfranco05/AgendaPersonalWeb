import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { Transaction } from '../../../types'

vi.mock('../../../api/endpoints', () => ({ fetchTransactions: vi.fn() }))

import { fetchTransactions } from '../../../api/endpoints'
import { findTransactionById, SCAN_PAGE_SIZE } from '../findTransaction'

const tx = (id: string) => ({ id, product_name: `Mov ${id}` }) as Transaction
const page = (ids: string[], total: number, n: number) => ({ items: ids.map(tx), total, page: n, page_size: SCAN_PAGE_SIZE })

beforeEach(() => vi.clearAllMocks())

describe('findTransactionById', () => {
  it('lo encuentra en la primera página sin pedir más', async () => {
    vi.mocked(fetchTransactions).mockResolvedValueOnce(page(['a', 'b'], 2, 1))
    expect((await findTransactionById('b'))?.id).toBe('b')
    expect(fetchTransactions).toHaveBeenCalledTimes(1)
    expect(fetchTransactions).toHaveBeenCalledWith({ page: 1, per_page: SCAN_PAGE_SIZE })
  })

  it('sigue con la página siguiente si hay más movimientos y no estaba', async () => {
    vi.mocked(fetchTransactions)
      .mockResolvedValueOnce(page(['a'], SCAN_PAGE_SIZE + 1, 1))
      .mockResolvedValueOnce(page(['z'], SCAN_PAGE_SIZE + 1, 2))
    expect((await findTransactionById('z'))?.id).toBe('z')
    expect(fetchTransactions).toHaveBeenNthCalledWith(2, { page: 2, per_page: SCAN_PAGE_SIZE })
  })

  it('devuelve null cuando recorrió todo y no está', async () => {
    vi.mocked(fetchTransactions).mockResolvedValueOnce(page(['a'], 1, 1))
    expect(await findTransactionById('nope')).toBeNull()
    expect(fetchTransactions).toHaveBeenCalledTimes(1)
  })

  it('devuelve null si la API falla', async () => {
    vi.mocked(fetchTransactions).mockRejectedValueOnce(new Error('boom'))
    expect(await findTransactionById('a')).toBeNull()
  })
})
