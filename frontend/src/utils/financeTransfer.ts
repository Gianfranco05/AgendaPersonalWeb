import type { ImportConfirmRow, ParsedImportRow } from '../types';

const SYMBOLS: Record<string, string> = { ARS: '$', USD: 'US$', EUR: '€' };
const IMPORTABLE = new Set(['ok', 'possible_duplicate']);

/** Centavos exactos de un decimal que viene como string del server ("1234.56"):
 *  no pasa por float (0.1 + 0.2 ≠ 0.3). */
export function toCents(value: string): number {
  const negative = value.startsWith('-');
  const [int, frac = ''] = value.replace('-', '').split('.');
  const cents = Number(int) * 100 + Number(`${frac}00`.slice(0, 2));
  return negative ? -cents : cents;
}

function groupThousands(int: string): string {
  return int.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

/** "$ 1.234,56", "US$ 1,00", "€ 0,05" (sin `toLocaleString`: no depende del ICU del navegador). */
export function formatCents(cents: number, currency: string): string {
  const abs = Math.abs(cents);
  const text = `${groupThousands(String(Math.floor(abs / 100)))},${String(abs % 100).padStart(2, '0')}`;
  return `${cents < 0 ? '-' : ''}${SYMBOLS[currency] ?? currency} ${text}`;
}

/** Las filas ok vienen tildadas; duplicados, posibles duplicados, errores e
 *  informativas, no (sumar una es fácil, limpiar dobles no). */
export function defaultSelection(rows: ParsedImportRow[]): Set<number> {
  return new Set(rows.filter((r) => r.status === 'ok').map((r) => r.index));
}

/** Cuerpo de `POST /imports/{id}/confirm`: solo las filas tildadas e importables.
 *  La categoría solo viaja si el usuario la tocó (`''` = sin categoría; ausente =
 *  la sugerida) y el tipo solo si difiere del original. Los montos nunca viajan:
 *  el server los vuelve a leer del archivo. */
export function buildConfirmRows(
  rows: ParsedImportRow[],
  selected: Set<number>,
  categories: Record<number, string>,
  types: Record<number, 'income' | 'expense'>,
): ImportConfirmRow[] {
  const out: ImportConfirmRow[] = [];
  for (const r of rows) {
    if (!selected.has(r.index) || !IMPORTABLE.has(r.status)) continue;
    const item: ImportConfirmRow = { index: r.index, include: true };
    if (r.index in categories) item.category_id = categories[r.index];
    const type = types[r.index];
    if (type && type !== r.type) item.type = type;
    out.push(item);
  }
  return out;
}

export interface SelectedTotal {
  currency: string;
  income: number;
  expense: number;
  count: number;
}

/** Totales (en centavos) de lo tildado, por moneda y sin mezclarlas. */
export function selectedTotals(
  rows: ParsedImportRow[],
  selected: Set<number>,
  types: Record<number, 'income' | 'expense'>,
): SelectedTotal[] {
  const by = new Map<string, SelectedTotal>();
  for (const r of rows) {
    if (!selected.has(r.index) || !IMPORTABLE.has(r.status) || r.amount === null) continue;
    const currency = r.currency ?? 'ARS';
    const t = by.get(currency) ?? { currency, income: 0, expense: 0, count: 0 };
    const type = types[r.index] ?? r.type;
    t[type === 'income' ? 'income' : 'expense'] += toCents(r.amount);
    t.count += 1;
    by.set(currency, t);
  }
  return [...by.values()].sort((a, b) => a.currency.localeCompare(b.currency));
}

/** Descarga un archivo generado en el cliente (blob del export). */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
