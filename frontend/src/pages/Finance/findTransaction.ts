import { fetchTransactions } from '../../api/endpoints';
import type { Transaction } from '../../types';

/** Máximo que acepta la API por página. */
export const SCAN_PAGE_SIZE = 200;
/** Tope de seguridad: 50 páginas = 10.000 movimientos. */
const MAX_PAGES = 50;

/**
 * La API no tiene "traer un movimiento por id" y la lista de Finanzas está
 * paginada: si el buscador apunta a un movimiento que no está en la página
 * visible, se recorre el historial de a páginas hasta encontrarlo.
 */
export async function findTransactionById(id: string): Promise<Transaction | null> {
  try {
    for (let page = 1; page <= MAX_PAGES; page++) {
      const res = await fetchTransactions({ page, per_page: SCAN_PAGE_SIZE });
      const hit = res.items.find((t) => t.id === id);
      if (hit) return hit;
      if (res.items.length === 0 || page * SCAN_PAGE_SIZE >= res.total) break;
    }
  } catch {
    // Sin conexión o error de API: se trata como "no se encontró".
  }
  return null;
}
