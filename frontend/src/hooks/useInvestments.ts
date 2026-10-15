import { mutate as globalMutate } from 'swr';
import { useApiSWR } from './useApiSWR';
import {
  fetchInvestments,
  fetchInvestmentSummary,
  fetchNetWorth,
  createInvestment,
  updateInvestment,
  deleteInvestment,
  updateSettings,
} from '../api/endpoints';
import type { Investment, InvestmentInput, Settings } from '../types';

export type InvestmentStatusFilter = 'active' | 'closed';

const LIST_KEY = 'finance/investments';
const SUMMARY_KEY = 'finance/investments/summary';
const NET_WORTH_KEY = 'finance/net-worth';
const FINANCE_SUMMARY_KEY = 'finance/summary';
const SETTINGS_KEY = 'settings';

export function useInvestments(status: InvestmentStatusFilter = 'active') {
  return useApiSWR([LIST_KEY, status], () => fetchInvestments({ status }));
}

export function useInvestmentSummary() {
  return useApiSWR(SUMMARY_KEY, fetchInvestmentSummary);
}

export function useNetWorth() {
  return useApiSWR(NET_WORTH_KEY, fetchNetWorth);
}

// Cualquier cambio en una inversión mueve la lista (activas y cerradas), el
// resumen, el patrimonio y el resumen de Finanzas (Dashboard).
function isInvestmentKey(key: unknown): boolean {
  if (Array.isArray(key)) return key[0] === LIST_KEY;
  return key === SUMMARY_KEY || key === NET_WORTH_KEY || key === FINANCE_SUMMARY_KEY;
}

async function invalidateInvestments(includeSettings = false) {
  await Promise.all([
    globalMutate(isInvestmentKey),
    ...(includeSettings ? [globalMutate(SETTINGS_KEY)] : []),
  ]);
}

export async function saveInvestment(existing: Investment | null, data: InvestmentInput) {
  if (existing) {
    await updateInvestment(existing.id, data);
  } else {
    await createInvestment(data);
  }
  await invalidateInvestments();
}

export async function setInvestmentStatus(id: string, status: 'active' | 'closed') {
  await updateInvestment(id, { status });
  await invalidateInvestments();
}

export async function removeInvestment(id: string) {
  await deleteInvestment(id);
  await invalidateInvestments();
}

/** Cotizaciones (null borra) y toggle "Sumar inversiones al balance": viven en
 *  los ajustes del usuario, así que además de los totales se revalida `settings`. */
export async function saveInvestmentSettings(
  data: Pick<Partial<Settings>, 'fx_usd_ars' | 'fx_eur_ars' | 'include_investments_in_balance'>,
) {
  await updateSettings(data);
  await invalidateInvestments(true);
}
