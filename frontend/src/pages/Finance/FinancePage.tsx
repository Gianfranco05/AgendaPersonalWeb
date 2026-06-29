import { useState } from 'react';
import { TrendingUp, TrendingDown, Wallet, Plus } from 'lucide-react';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import { useFinanceSummary, useTransactions, removeTransaction } from '../../hooks/useFinance';
import type { Transaction } from '../../types';
import TransactionTable from './TransactionTable';
import TransactionModal from './TransactionModal';
import FinanceCharts from './FinanceCharts';
import TransactionFilters from './TransactionFilters';

interface Filters {
  date_from: string;
  date_to: string;
  category: string;
  type: string;
}

const PER_PAGE = 20;

export default function FinancePage() {
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<Filters>({
    date_from: '',
    date_to: '',
    category: '',
    type: '',
  });
  const [showModal, setShowModal] = useState(false);
  const [editingTx, setEditingTx] = useState<Transaction | null>(null);

  const txParams = {
    page,
    per_page: PER_PAGE,
    ...(filters.type && { type: filters.type }),
    ...(filters.category && { category: filters.category }),
    ...(filters.date_from && { date_from: filters.date_from }),
    ...(filters.date_to && { date_to: filters.date_to }),
  };

  const { data: summary, isLoading: summaryLoading } = useFinanceSummary();
  const { data: txData, isLoading: txLoading } = useTransactions(txParams);

  const transactions = txData?.transactions ?? [];
  const total = txData?.total ?? 0;
  const totalPages = Math.ceil(total / PER_PAGE);
  const loading = summaryLoading || txLoading;

  function handleNew() {
    setEditingTx(null);
    setShowModal(true);
  }

  function handleEdit(tx: Transaction) {
    setEditingTx(tx);
    setShowModal(true);
  }

  async function handleDelete(id: string) {
    await removeTransaction(id, txParams);
  }

  function handleSaved() {
    setShowModal(false);
  }

  function handleFiltersChange(newFilters: Filters) {
    setFilters(newFilters);
    setPage(1);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-800">Finanzas</h2>
        <button
          onClick={handleNew}
          className="flex items-center gap-2 rounded-lg bg-[#7C3AED] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#6D28D9]"
        >
          <Plus size={16} />
          Nueva transacción
        </button>
      </div>

      {/* Summary Cards */}
      {summaryLoading && !summary ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <LoadingSkeleton type="card" />
          <LoadingSkeleton type="card" />
          <LoadingSkeleton type="card" />
        </div>
      ) : summary ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-xl bg-white p-5 shadow-sm">
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <TrendingUp size={16} className="text-emerald-500" />
              Ingresos
            </div>
            <p className="mt-1 text-2xl font-bold text-emerald-500">
              ${summary.total_income.toLocaleString('es-AR')}
            </p>
          </div>
          <div className="rounded-xl bg-white p-5 shadow-sm">
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <TrendingDown size={16} className="text-rose-500" />
              Egresos
            </div>
            <p className="mt-1 text-2xl font-bold text-rose-500">
              ${summary.total_expense.toLocaleString('es-AR')}
            </p>
          </div>
          <div className="rounded-xl bg-white p-5 shadow-sm">
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Wallet size={16} className="text-[#7C3AED]" />
              Balance
            </div>
            <p
              className={`mt-1 text-2xl font-bold ${
                summary.balance >= 0 ? 'text-emerald-500' : 'text-rose-500'
              }`}
            >
              ${summary.balance.toLocaleString('es-AR')}
            </p>
          </div>
        </div>
      ) : null}

      <FinanceCharts transactions={transactions} loading={loading} />

      <TransactionFilters filters={filters} onChange={handleFiltersChange} />

      {txLoading ? (
        <LoadingSkeleton type="table" rows={5} />
      ) : (
        <>
          <TransactionTable
            transactions={transactions}
            onEdit={handleEdit}
            onDelete={handleDelete}
          />

          {total > PER_PAGE && (
            <div className="flex items-center justify-between rounded-xl bg-white p-4 shadow-sm">
              <span className="text-sm text-gray-500">
                Mostrando {(page - 1) * PER_PAGE + 1}–{Math.min(page * PER_PAGE, total)} de {total}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-600 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Anterior
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-600 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Siguiente
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {showModal && (
        <TransactionModal
          transaction={editingTx}
          txParams={txParams}
          onClose={() => setShowModal(false)}
          onSaved={handleSaved}
        />
      )}
    </div>
  );
}
