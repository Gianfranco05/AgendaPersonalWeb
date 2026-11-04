import { describe, it, expect, vi } from 'vitest'
import { screen, fireEvent } from '@testing-library/react'
import type { ComponentProps } from 'react'
import { renderWithProviders } from '../../../test/test-utils'
import PreviewTable from '../Import/PreviewTable'
import { undoWarning } from '../Import/ImportHistory'
import type { ImportBatch, ParsedImportRow } from '../../../types'

const base = {
  index: 0, source_line: 2, date: '2026-10-01', description: 'Sueldo', amount: '250000.00', type: 'income',
  currency: 'ARS', status: 'ok', errors: [], duplicate_of: null, suggested_category_id: null,
  suggestion_source: 'none',
} as unknown as ParsedImportRow

const rows: ParsedImportRow[] = [
  base,
  { ...base, index: 1, source_line: 3, description: 'Compra Coto', amount: '1234.56', type: 'expense' },
  { ...base, index: 2, source_line: 4, description: 'Repetida', status: 'duplicate', errors: ['Ya importado.'] },
  { ...base, index: 3, source_line: 5, description: 'Rota', date: null, amount: null, type: null, currency: null, status: 'error', errors: ['Fecha invalida'] },
]

function renderTable(over: Partial<ComponentProps<typeof PreviewTable>> = {}) {
  const fns = { onSelectedChange: vi.fn(), onCategoryChange: vi.fn(), onTypeChange: vi.fn() }
  renderWithProviders(
    <PreviewTable rows={rows} selected={new Set([0, 1])} categories={{}} types={{}} {...fns} {...over} />,
  )
  return fns
}

describe('PreviewTable', () => {
  it('deshabilita la casilla de duplicados y errores', () => {
    renderTable()
    expect(screen.getByLabelText('Importar fila 4')).toBeDisabled()
    expect(screen.getByLabelText('Importar fila 5')).toBeDisabled()
    expect(screen.getByLabelText('Importar fila 2')).toBeEnabled()
  })

  it('al tildar una fila avisa la nueva seleccion', () => {
    const props = renderTable({ selected: new Set([0]) })
    fireEvent.click(screen.getByLabelText('Importar fila 3'))
    expect([...(props.onSelectedChange.mock.calls[0][0] as Set<number>)].sort()).toEqual([0, 1])
  })

  it('filtra por estado', () => {
    renderTable()
    fireEvent.click(screen.getByRole('button', { name: /^Error \(1\)/ }))
    expect(screen.getByText('Rota')).toBeInTheDocument()
    expect(screen.queryByText('Sueldo')).not.toBeInTheDocument()
  })

  it('cambiar el tipo de una fila lo avisa', () => {
    const props = renderTable()
    fireEvent.change(screen.getByLabelText('Tipo de la fila 3'), { target: { value: 'income' } })
    expect(props.onTypeChange).toHaveBeenCalledWith(1, 'income')
  })

  it('pagina de a 100 filas', () => {
    const many = Array.from({ length: 150 }, (_, i) => ({ ...base, index: i, source_line: i + 2, description: `Mov ${i}` }))
    renderTable({ rows: many, selected: new Set() })
    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument()
    expect(screen.queryByText('Mov 120')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    expect(screen.getByText('Mov 120')).toBeInTheDocument()
  })
})

describe('undoWarning', () => {
  const batch = { filename: 'mp.csv', imported_count: 12, edited_count: 0 } as ImportBatch
  it('avisa cuantos movimientos se borran', () => {
    expect(undoWarning(batch)).toContain('12 movimientos')
    expect(undoWarning(batch)).not.toContain('editaste')
  })
  it('advierte de los editados despues de importar', () => {
    expect(undoWarning({ ...batch, edited_count: 3 })).toContain('3 de esos movimientos los editaste')
  })
})
