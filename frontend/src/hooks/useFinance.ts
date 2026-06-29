import useSWR, { mutate as globalMutate } from 'swr';
import {
  fetchFinanceSummary,
  fetchTransactions,
  fetchCategories,
  createTransaction,
  updateTransaction,
  deleteTransaction,
} from '../api/endpoints';
import type { Transaction } from '../types';

const SUMMARY_KEY = 'finance/summary';
const CATEGORIES_KEY = 'finance/categories';

function txKey(params: Parameters<typeof fetchTransactions>[0]) {
  return ['finance/transactions', JSON.stringify(params)] as const;
}

export function useFinanceSummary() {
  return useSWR(SUMMARY_KEY, fetchFinanceSummary);
}

export function useTransactions(params: Parameters<typeof fetchTransactions>[0]) {
  return useSWR(txKey(params), () => fetchTransactions(params));
}

export function useCategories() {
  return useSWR(CATEGORIES_KEY, fetchCategories);
}

async function invalidateFinance(params: Parameters<typeof fetchTransactions>[0]) {
  await Promise.all([
    globalMutate(SUMMARY_KEY),
    globalMutate(txKey(params)),
  ]);
}

export async function saveTransaction(
  transaction: Transaction | null,
  data: Omit<Transaction, 'id'>,
  txParams: Parameters<typeof fetchTransactions>[0],
) {
  if (transaction) {
    await updateTransaction(transaction.id, data);
  } else {
    await createTransaction(data);
  }
  await invalidateFinance(txParams);
}

export async function removeTransaction(
  id: string,
  txParams: Parameters<typeof fetchTransactions>[0],
) {
  await deleteTransaction(id);
  await invalidateFinance(txParams);
}
