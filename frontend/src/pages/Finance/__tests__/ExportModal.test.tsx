import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../../../test/test-utils'

vi.mock('../../../api/endpoints', async (orig) => ({
  ...(await orig<typeof import('../../../api/endpoints')>()),
  downloadFinanceExport: vi.fn(),
}))
vi.mock('../../../utils/financeTransfer', async (orig) => ({
  ...(await orig<typeof import('../../../utils/financeTransfer')>()),
  saveBlob: vi.fn(),
}))

import { downloadFinanceExport } from '../../../api/endpoints'
import { saveBlob } from '../../../utils/financeTransfer'
import ExportModal, { buildExportParams } from '../ExportModal'

const onClose = vi.fn()
const submitName = /descargar|exportar/i

beforeEach(() => vi.clearAllMocks())

describe('buildExportParams', () => {
  const base = {
    date_from: '2026-10-01', date_to: '2026-10-31', type: '' as const, category_id: '',
    account_id: '', format: 'xlsx' as const, include_investments: false,
  }
  it('omite los filtros vacios', () => {
    expect(buildExportParams(base)).toEqual({ format: 'xlsx', date_from: '2026-10-01', date_to: '2026-10-31' })
  })
  it('incluye solo los filtros elegidos', () => {
    expect(buildExportParams({ ...base, type: 'income', category_id: 'c1', format: 'pdf', include_investments: true })).toEqual({
      format: 'pdf', date_from: '2026-10-01', date_to: '2026-10-31', type: 'income', category_id: 'c1', include_investments: true,
    })
  })
})

describe('ExportModal', () => {
  it('se prellena con los filtros activos', () => {
    renderWithProviders(<ExportModal defaults={{ date_from: '2026-09-01', date_to: '2026-09-30', type: 'expense' }} onClose={onClose} />)
    expect((screen.getByLabelText('Desde') as HTMLInputElement).value).toBe('2026-09-01')
    expect((screen.getByLabelText('Hasta') as HTMLInputElement).value).toBe('2026-09-30')
    expect((screen.getByLabelText('Tipo') as HTMLSelectElement).value).toBe('expense')
  })

  it('rechaza un rango invertido sin llamar al server', async () => {
    renderWithProviders(<ExportModal defaults={{ date_from: '2026-10-10', date_to: '2026-10-01' }} onClose={onClose} />)
    fireEvent.click(screen.getByRole('button', { name: submitName }))
    expect(await screen.findByText(/no puede ser anterior/i)).toBeInTheDocument()
    expect(downloadFinanceExport).not.toHaveBeenCalled()
  })

  it('descarga y guarda el archivo con el nombre del server', async () => {
    const file = { blob: new Blob(['x']), filename: 'cancen-finanzas_2026-10-31.xlsx' }
    vi.mocked(downloadFinanceExport).mockResolvedValue(file)
    renderWithProviders(<ExportModal defaults={{ date_from: '2026-10-01', date_to: '2026-10-31' }} onClose={onClose} />)
    fireEvent.click(screen.getByRole('button', { name: submitName }))
    await waitFor(() => expect(saveBlob).toHaveBeenCalledWith(file.blob, file.filename))
    expect(downloadFinanceExport).toHaveBeenCalledWith(expect.objectContaining({ format: 'xlsx', date_from: '2026-10-01' }))
  })

  it('muestra el error y no guarda nada si falla', async () => {
    vi.mocked(downloadFinanceExport).mockRejectedValue(new Error('boom'))
    renderWithProviders(<ExportModal defaults={{ date_from: '2026-10-01', date_to: '2026-10-31' }} onClose={onClose} />)
    fireEvent.click(screen.getByRole('button', { name: submitName }))
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(saveBlob).not.toHaveBeenCalled()
  })
})
