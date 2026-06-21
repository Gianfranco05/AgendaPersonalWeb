import { useEffect, useState, useCallback } from 'react';
import { TrendingUp, TrendingDown, Wallet, Plus } from 'lucide-react';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import { fetchFinanceSummary, fetchTransactions, deleteTransaction } from '../../api/endpoints';
import type { Transaction } from '../../types';
import type { FinanceSummary } from '../../types';
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

export default function FinancePage() {
  const [summary, setSummary] = useState<FinanceSummary | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<Filters>({ date_from: '', date_to: '', category: '', type: '' });
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingTx, setEditingTx] = useState<Transaction | null>(null);

  const perPage = 20;

  const loadData = useCallback(async (currentPage: number, currentFilters: Filters) => {
    setLoading(true);
    const [summaryData, txData] = await Promise.all([
      fetchFinanceSummary(),
      fetchTransactions({
        page: currentPage,
        per_page: perPage,
        ...(currentFilters.type && { type: currentFilters.type }),
        ...(currentFilters.category && { category: currentFilters.category }),
        ...(currentFilters.date_from && { date_from: currentFilters.date_from }),
        ...(currentFilters.date_to && { date_to: currentFilters.date_to }),
      }),
    ]);
    setSummary(summaryData);
    setTransactions(txData.transactions);
    setTotal(txData.total);
    setLoading(false);
  }, []);

  useEffect(() => {
    loadData(page, filters);
  }, [page, filters, loadData]);

  function handleNew() {
    setEditingTx(null);
    setShowModal(true);
  }

  function handleEdit(tx: Transaction) {
    setEditingTx(tx);
    setShowModal(true);
  }

  async function handleDelete(id: string) {
    await deleteTransaction(id);
    loadData(page, filters);
  }

  function handleSaved() {
    setShowModal(false);
    loadData(page, filters);
  }

  function handleFiltersChange(newFilters: Filters) {
    setFilters(newFilters);
    setPage(1);
  }

  const totalPages = Math.ceil(total / perPage);

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
      {loading && !summary ? (
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
            <p className={`mt-1 text-2xl font-bold ${summary.balance >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
              ${summary.balance.toLocaleString('es-AR')}
            </p>
          </div>
        </div>
      ) : null}

      {/* Charts */}
      <FinanceCharts transactions={transactions} loading={loading} />

      {/* Filters */}
      <TransactionFilters filters={filters} onChange={handleFiltersChange} />

      {/* Table */}
      {loading ? (
        <LoadingSkeleton type="table" rows={5} />
      ) : (
        <>
          <TransactionTable
            transactions={transactions}
            onEdit={handleEdit}
            onDelete={handleDelete}
          />

          {/* Pagination */}
          {total > perPage && (
            <div className="flex items-center justify-between rounded-xl bg-white p-4 shadow-sm">
              <span className="text-sm text-gray-500">
                Mostrando {(page - 1) * perPage + 1}-{Math.min(page * perPage, total)} de {total}
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

      {/* Modal */}
      {showModal && (
        <TransactionModal
          transaction={editingTx}
          onClose={() => setShowModal(false)}
          onSaved={handleSaved}
        />
      )}
    </div>
  );
}
