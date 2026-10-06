import { useState, lazy, Suspense } from 'react';
import { TrendingUp, TrendingDown, Wallet, Plus } from 'lucide-react';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import { useFinanceSummary, useTransactions, removeTransaction } from '../../hooks/useFinance';
import type { Transaction } from '../../types';
import TransactionTable from './TransactionTable';
import TransactionModal from './TransactionModal';
import TransactionFilters from './TransactionFilters';
import BudgetsSection from './BudgetsSection';
import SavingsGoalsSection from './SavingsGoalsSection';
import CategoriesSection from './CategoriesSection';
import ReportsSection from './ReportsSection';
import AccountsSection from './AccountsSection';

const FinanceCharts = lazy(() => import('./FinanceCharts'));

interface Filters {
  date_from: string;
  date_to: string;
  category: string;
  type: string;
}

const PER_PAGE = 20;

type Tab = 'transacciones' | 'presupuestos' | 'ahorro' | 'categorias' | 'reportes' | 'cuentas';

export default function FinancePage() {
  const [tab, setTab] = useState<Tab>('transacciones');
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

  const transactions = txData?.items ?? [];
  const total = txData?.total ?? 0;
  const totalPages = Math.ceil(total / PER_PAGE);

  function handleNew() {
    setEditingTx(null);
    setShowModal(true);
  }

  function handleEdit(tx: Transaction) {
    setEditingTx(tx);
    setShowModal(true);
  }

  async function handleDelete(id: string) {
    if (!window.confirm('¿Eliminar esta transacción?')) return;
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
        <h2 className="text-2xl font-bold text-gray-800 dark:text-slate-100">Finanzas</h2>
        {tab === 'transacciones' && (
          <button
            onClick={handleNew}
            className="flex items-center gap-2 rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-charcoal-hover"
          >
            <Plus size={16} />
            Nueva transacción
          </button>
        )}
      </div>

      <div className="flex max-w-full overflow-x-auto rounded-lg border border-gray-200 dark:border-slate-700 p-0.5 w-fit">
        {([
          ['transacciones', 'Transacciones'],
          ['presupuestos', 'Presupuestos'],
          ['ahorro', 'Ahorro'],
          ['categorias', 'Categorías'],
          ['reportes', 'Reportes'],
          ['cuentas', 'Cuentas'],
        ] as const).map(([value, label]) => (
          <button
            key={value}
            onClick={() => setTab(value)}
            className={`shrink-0 rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
              tab === value
                ? 'bg-brand-charcoal text-white'
                : 'text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-100'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'presupuestos' && <BudgetsSection />}
      {tab === 'ahorro' && <SavingsGoalsSection />}
      {tab === 'categorias' && <CategoriesSection />}
      {tab === 'reportes' && <ReportsSection />}
      {tab === 'cuentas' && <AccountsSection />}

      {tab === 'transacciones' && (
      <>
      {/* Summary Cards */}
      {summaryLoading && !summary ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <LoadingSkeleton type="card" />
          <LoadingSkeleton type="card" />
          <LoadingSkeleton type="card" />
        </div>
      ) : summary ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
              <TrendingUp size={16} className="text-emerald-500" />
              Ingresos
            </div>
            <p className="mt-1 text-2xl font-bold text-emerald-500">
              ${summary.total_income.toLocaleString('es-AR')}
            </p>
          </div>
          <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
              <TrendingDown size={16} className="text-rose-500" />
              Egresos
            </div>
            <p className="mt-1 text-2xl font-bold text-rose-500">
              ${(summary.total_expenses ?? 0).toLocaleString('es-AR')}
            </p>
          </div>
          <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
              <Wallet size={16} className="text-brand-indigo" />
              Balance
            </div>
            <p
              className={`mt-1 text-2xl font-bold ${
                summary.balance >= 0 ? 'text-emerald-500' : 'text-rose-500'
              }`}
            >
              {summary.balance < 0 ? '-' : ''}${Math.abs(summary.balance).toLocaleString('es-AR')}
            </p>
          </div>
        </div>
      ) : null}

      <Suspense fallback={<LoadingSkeleton type="card" />}>
        <FinanceCharts />
      </Suspense>

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
            <div className="flex items-center justify-between rounded-xl bg-white dark:bg-slate-800 p-4 shadow-sm">
              <span className="text-sm text-gray-500 dark:text-slate-400">
                Mostrando {(page - 1) * PER_PAGE + 1}–{Math.min(page * PER_PAGE, total)} de {total}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-1.5 text-sm text-gray-600 dark:text-slate-300 transition-colors hover:bg-gray-50 dark:hover:bg-slate-700/50 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Anterior
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-1.5 text-sm text-gray-600 dark:text-slate-300 transition-colors hover:bg-gray-50 dark:hover:bg-slate-700/50 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Siguiente
                </button>
              </div>
            </div>
          )}
        </>
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
