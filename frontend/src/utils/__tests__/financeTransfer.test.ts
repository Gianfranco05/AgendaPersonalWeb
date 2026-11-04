import { describe, it, expect } from 'vitest';
import {
  buildConfirmRows,
  defaultSelection,
  formatCents,
  selectedTotals,
  toCents,
} from '../financeTransfer';
import type { ParsedImportRow } from '../../types';

function row(over: Partial<ParsedImportRow>): ParsedImportRow {
  return {
    index: 0,
    source_line: 2,
    date: '2026-10-01',
    time: null,
    description: 'x',
    amount: '10.00',
    type: 'expense',
    currency: 'ARS',
    reference: '',
    status: 'ok',
    errors: [],
    row_hash: 'h',
    duplicate_of: null,
    suggested_category_id: null,
    suggestion_source: 'none',
    merchant_category: 'other',
    ...over,
  };
}

describe('toCents / formatCents', () => {
  it('parsea el decimal del server sin pasar por float', () => {
    expect(toCents('1234.56')).toBe(123456);
    expect(toCents('0.10') + toCents('0.20')).toBe(30); // 0.1 + 0.2 en float no da 0.3
    expect(toCents('250000.00')).toBe(25000000);
    expect(toCents('7')).toBe(700);
    expect(toCents('1.5')).toBe(150);
  });

  it('formatea es-AR con símbolo por moneda', () => {
    expect(formatCents(123456, 'ARS')).toBe('$ 1.234,56');
    expect(formatCents(100, 'USD')).toBe('US$ 1,00');
    expect(formatCents(-5, 'EUR')).toBe('-€ 0,05');
    expect(formatCents(100000000, 'ARS')).toBe('$ 1.000.000,00');
  });
});

describe('defaultSelection', () => {
  it('tilda las filas ok y deja destildados duplicados, posibles y con error', () => {
    const rows = [
      row({ index: 0, status: 'ok' }),
      row({ index: 1, status: 'duplicate' }),
      row({ index: 2, status: 'possible_duplicate' }),
      row({ index: 3, status: 'error' }),
      row({ index: 4, status: 'skipped' }),
      row({ index: 5, status: 'ok' }),
    ];
    expect([...defaultSelection(rows)].sort()).toEqual([0, 5]);
  });
});

describe('buildConfirmRows', () => {
  const rows = [
    row({ index: 0, type: 'expense' }),
    row({ index: 1, type: 'income' }),
    row({ index: 2, status: 'possible_duplicate' }),
    row({ index: 3, status: 'error' }),
  ];

  it('manda solo las seleccionadas y sin overrides si no se tocó nada', () => {
    const out = buildConfirmRows(rows, new Set([0, 2]), {}, {});
    expect(out).toEqual([
      { index: 0, include: true },
      { index: 2, include: true },
    ]);
  });

  it('incluye categoría ("" = sin categoría) y tipo solo cuando difieren', () => {
    const out = buildConfirmRows(rows, new Set([0, 1]), { 0: 'cat-1', 1: '' }, { 0: 'income', 1: 'income' });
    expect(out).toEqual([
      { index: 0, include: true, category_id: 'cat-1', type: 'income' },
      { index: 1, include: true, category_id: '' }, // el tipo es el original: no se manda
    ]);
  });

  it('nunca incluye filas con error aunque estén en la selección', () => {
    expect(buildConfirmRows(rows, new Set([3]), {}, {})).toEqual([]);
  });
});

describe('selectedTotals', () => {
  it('suma por moneda en centavos exactos y respeta el tipo elegido', () => {
    const rows = [
      row({ index: 0, amount: '0.10', type: 'expense' }),
      row({ index: 1, amount: '0.20', type: 'expense' }),
      row({ index: 2, amount: '100.00', type: 'income' }),
      row({ index: 3, amount: '5.00', type: 'expense', currency: 'USD' }),
      row({ index: 4, amount: '999.00', type: 'expense' }), // no seleccionada
    ];
    const totals = selectedTotals(rows, new Set([0, 1, 2, 3]), { 2: 'expense' });
    expect(totals).toEqual([
      { currency: 'ARS', income: 0, expense: 10030, count: 3 },
      { currency: 'USD', income: 0, expense: 500, count: 1 },
    ]);
  });
});
