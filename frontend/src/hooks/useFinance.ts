import { mutate as globalMutate } from 'swr';
import { useApiSWR } from './useApiSWR';
import {
  fetchFinanceSummary,
  fetchTransactions,
  fetchCategories,
  createTransaction,
  updateTransaction,
  deleteTransaction,
  fetchBudgets,
  createBudget,
  updateBudget,
  deleteBudget,
  createCategory,
  updateCategory,
  deleteCategory,
  fetchFinanceReports,
  fetchBankAccounts,
  createBankAccount,
  updateBankAccount,
  deleteBankAccount,
} from '../api/endpoints';
import type { Transaction, Budget, Category, BankAccount } from '../types';

const SUMMARY_KEY = 'finance/summary';
const CATEGORIES_KEY = 'finance/categories';
const REPORTS_KEY = 'finance/reports';
const ACCOUNTS_KEY = 'finance/accounts';

function budgetsKey(year: number, month: number) {
  return ['finance/budgets', year, month] as const;
}

function txKey(params: Parameters<typeof fetchTransactions>[0]) {
  return ['finance/transactions', JSON.stringify(params)] as const;
}

export function useFinanceSummary() {
  return useApiSWR(SUMMARY_KEY, fetchFinanceSummary);
}

export function useTransactions(params: Parameters<typeof fetchTransactions>[0]) {
  return useApiSWR(txKey(params), () => fetchTransactions(params));
}

export function useCategories() {
  return useApiSWR(CATEGORIES_KEY, fetchCategories);
}

async function invalidateFinance(params: Parameters<typeof fetchTransactions>[0]) {
  await Promise.all([
    globalMutate(SUMMARY_KEY),
    globalMutate(txKey(params)),
    // Los gráficos salen de /reports: sin esto quedaban viejos hasta recargar.
    globalMutate(REPORTS_KEY),
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

export function useBudgets(year: number, month: number) {
  return useApiSWR(budgetsKey(year, month), () => fetchBudgets(year, month));
}

export async function saveBudget(
  existing: Budget | null,
  data: Omit<Budget, 'id'>,
  year: number,
  month: number,
) {
  if (existing) {
    await updateBudget(existing.id, data);
  } else {
    await createBudget(data);
  }
  await globalMutate(budgetsKey(year, month));
}

export async function removeBudget(id: string, year: number, month: number) {
  await deleteBudget(id);
  await globalMutate(budgetsKey(year, month));
}

export async function saveCategory(existing: Category | null, data: Omit<Category, 'id'>) {
  if (existing) {
    await updateCategory(existing.id, data);
  } else {
    await createCategory(data);
  }
  // Renombrar o recolorear una categoría cambia cómo se ve en los reportes.
  await Promise.all([globalMutate(CATEGORIES_KEY), globalMutate(REPORTS_KEY)]);
}

export async function removeCategory(id: string) {
  await deleteCategory(id);
  await Promise.all([globalMutate(CATEGORIES_KEY), globalMutate(REPORTS_KEY)]);
}

export function useFinanceReports() {
  return useApiSWR(REPORTS_KEY, fetchFinanceReports);
}

export function useBankAccounts() {
  return useApiSWR(ACCOUNTS_KEY, fetchBankAccounts);
}

export async function saveBankAccount(
  existing: BankAccount | null,
  data: Omit<BankAccount, 'id' | 'user_id' | 'created_at'>,
) {
  if (existing) {
    await updateBankAccount(existing.id, data);
  } else {
    await createBankAccount(data);
  }
  await globalMutate(ACCOUNTS_KEY);
}

export async function removeBankAccount(id: string) {
  await deleteBankAccount(id);
  await globalMutate(ACCOUNTS_KEY);
}
