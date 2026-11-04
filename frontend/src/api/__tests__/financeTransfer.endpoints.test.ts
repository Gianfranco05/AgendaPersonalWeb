import { describe, it, expect, vi, beforeEach } from 'vitest'

const { mockGet, mockPut, mockPost, mockDelete } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPut: vi.fn(),
  mockPost: vi.fn(),
  mockDelete: vi.fn(),
}))

vi.mock('../client', () => ({
  default: { get: mockGet, put: mockPut, post: mockPost, patch: vi.fn(), delete: mockDelete },
}))

import {
  downloadFinanceExport,
  previewImport,
  updateImportMapping,
  confirmImport,
  undoImport,
  discardImportPreview,
} from '../endpoints'

const expectedOffset = -new Date().getTimezoneOffset()

beforeEach(() => vi.clearAllMocks())

describe('downloadFinanceExport', () => {
  it('pide un blob con los filtros y la zona horaria, y toma el nombre del header', async () => {
    const blob = new Blob(['x'])
    mockGet.mockResolvedValue({
      data: blob,
      headers: { 'content-disposition': 'attachment; filename="cancen-finanzas_2026-10-31.xlsx"' },
    })
    const file = await downloadFinanceExport({
      format: 'xlsx', date_from: '2026-10-01', date_to: '2026-10-31', type: 'expense',
    })
    expect(mockGet).toHaveBeenCalledWith('/api/v1/finance/export', {
      params: {
        format: 'xlsx', date_from: '2026-10-01', date_to: '2026-10-31', type: 'expense',
        tz_offset_minutes: expectedOffset,
      },
      responseType: 'blob',
    })
    expect(file.blob).toBe(blob)
    expect(file.filename).toBe('cancen-finanzas_2026-10-31.xlsx')
  })

  it('usa un nombre por defecto con la extension del formato si falta el header', async () => {
    mockGet.mockResolvedValue({ data: new Blob(['x']), headers: {} })
    const file = await downloadFinanceExport({ format: 'pdf', date_from: '2026-10-01', date_to: '2026-10-31' })
    expect(file.filename).toBe('cancen-finanzas.pdf')
  })
})

describe('importacion', () => {
  it('previewImport manda multipart con archivo, preset, cuenta y zona horaria', async () => {
    mockPost.mockResolvedValue({ data: { batch_id: 'b1' } })
    const file = new File(['a;b'], 'mp.csv', { type: 'text/csv' })
    const out = await previewImport(file, { preset: 'mercadopago_release', account_id: 'acc1' })
    const [url, form] = mockPost.mock.calls[0]
    expect(url).toBe('/api/v1/finance/imports/preview')
    expect(form).toBeInstanceOf(FormData)
    expect((form as FormData).get('file')).toBeInstanceOf(File)
    expect((form as FormData).get('preset')).toBe('mercadopago_release')
    expect((form as FormData).get('account_id')).toBe('acc1')
    expect((form as FormData).get('tz_offset_minutes')).toBe(String(expectedOffset))
    expect(out.batch_id).toBe('b1')
  })

  it('previewImport omite preset auto y cuenta vacia', async () => {
    mockPost.mockResolvedValue({ data: {} })
    await previewImport(new File(['x'], 'a.csv'), { preset: 'auto', account_id: '' })
    const form = mockPost.mock.calls[0][1] as FormData
    expect(form.has('preset')).toBe(false)
    expect(form.has('account_id')).toBe(false)
  })

  it('updateImportMapping hace PUT al lote con la zona horaria', async () => {
    mockPut.mockResolvedValue({ data: { batch_id: 'b1' } })
    await updateImportMapping('b1', { header_row: 2 })
    expect(mockPut).toHaveBeenCalledWith('/api/v1/finance/imports/b1/mapping', {
      header_row: 2,
      tz_offset_minutes: expectedOffset,
    })
  })

  it('confirmImport envia las filas elegidas al lote', async () => {
    mockPost.mockResolvedValue({ data: { id: 'b1', status: 'confirmed' } })
    const rows = [{ index: 0, include: true, category_id: '', type: 'expense' as const }]
    await confirmImport('b1', rows)
    expect(mockPost.mock.calls[0][0]).toBe('/api/v1/finance/imports/b1/confirm')
    expect(JSON.stringify(mockPost.mock.calls[0][1])).toContain('"index":0')
  })

  it('undoImport y discardImportPreview usan DELETE sobre el lote', async () => {
    mockDelete.mockResolvedValue({ data: { id: 'b1', status: 'undone' } })
    await undoImport('b1')
    await discardImportPreview('b2')
    expect(mockDelete.mock.calls.map((c) => c[0])).toEqual([
      '/api/v1/finance/imports/b1',
      '/api/v1/finance/imports/b2',
    ])
  })
})
