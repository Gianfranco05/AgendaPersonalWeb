import { useState } from 'react';
import { Plus, Pencil, Trash2, Landmark } from 'lucide-react';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import { useBankAccounts, saveBankAccount, removeBankAccount } from '../../hooks/useFinance';
import type { BankAccount, BankAccountType } from '../../types';

const ACCOUNT_TYPE_LABELS: Record<BankAccountType, string> = {
  checking: 'Cuenta corriente',
  savings: 'Caja de ahorro',
  credit: 'Tarjeta de crédito',
  cash: 'Efectivo',
  investment: 'Inversión',
};

const ACCOUNT_TYPES = Object.keys(ACCOUNT_TYPE_LABELS) as BankAccountType[];

const inputCls =
  'w-full rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-2 text-sm focus:border-brand-indigo focus:outline-none focus:ring-1 focus:ring-brand-indigo';

function AccountForm({
  account,
  onClose,
}: {
  account: BankAccount | null;
  onClose: () => void;
}) {
  const [name, setName] = useState(account?.name ?? '');
  const [bankName, setBankName] = useState(account?.bank_name ?? '');
  const [accountType, setAccountType] = useState<BankAccountType>(account?.account_type ?? 'checking');
  const [accountNumber, setAccountNumber] = useState(account?.account_number ?? '');
  const [currency, setCurrency] = useState(account?.currency ?? 'ARS');
  const [balance, setBalance] = useState(account ? String(account.balance) : '0');
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    await saveBankAccount(account, {
      name: name.trim(),
      bank_name: bankName.trim() || undefined,
      account_type: accountType,
      account_number: accountNumber.trim() || undefined,
      currency: currency.trim() || 'ARS',
      balance: Number(balance) || 0,
    });
    setSaving(false);
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 px-4 py-8 sm:py-12">
      <div className="w-full max-w-md rounded-xl bg-white dark:bg-slate-800 shadow-xl">
        <div className="border-b border-gray-100 dark:border-slate-800 px-6 py-4">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">
            {account ? 'Editar cuenta' : 'Nueva cuenta'}
          </h3>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4 px-6 py-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Nombre</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className={inputCls}
              placeholder="Cuenta sueldo"
              autoFocus
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Banco</label>
            <input
              type="text"
              value={bankName}
              onChange={(e) => setBankName(e.target.value)}
              className={inputCls}
              placeholder="Banco Nación"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Tipo de cuenta</label>
            <select
              value={accountType}
              onChange={(e) => setAccountType(e.target.value as BankAccountType)}
              className={inputCls}
            >
              {ACCOUNT_TYPES.map((type) => (
                <option key={type} value={type}>{ACCOUNT_TYPE_LABELS[type]}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Número de cuenta</label>
            <input
              type="text"
              value={accountNumber}
              onChange={(e) => setAccountNumber(e.target.value)}
              className={inputCls}
              placeholder="Opcional"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Moneda</label>
              <input
                type="text"
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className={inputCls}
                placeholder="ARS"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Saldo</label>
              <input
                type="number"
                value={balance}
                onChange={(e) => setBalance(e.target.value)}
                className={inputCls}
                placeholder="0"
              />
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-gray-200 dark:border-slate-700 px-4 py-2 text-sm font-medium text-gray-600 dark:text-slate-300 transition-colors hover:bg-gray-50 dark:hover:bg-slate-700/50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving || !name.trim()}
              className="rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-charcoal-hover disabled:opacity-50"
            >
              {saving ? 'Guardando…' : account ? 'Actualizar' : 'Crear'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function AccountsSection() {
  const { data: accounts, isLoading } = useBankAccounts();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<BankAccount | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  function handleNew() {
    setEditing(null);
    setShowForm(true);
  }

  function handleEdit(account: BankAccount) {
    setEditing(account);
    setShowForm(true);
  }

  async function handleConfirmDelete() {
    if (!deletingId) return;
    await removeBankAccount(deletingId);
    setDeletingId(null);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-end">
        <button
          onClick={handleNew}
          className="flex items-center gap-2 rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-charcoal-hover"
        >
          <Plus size={16} />
          Nueva cuenta
        </button>
      </div>

      {isLoading ? (
        <LoadingSkeleton type="card" />
      ) : !accounts || accounts.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl bg-white dark:bg-slate-800 p-12 shadow-sm">
          <Landmark size={48} className="text-gray-300 dark:text-slate-600" />
          <p className="text-sm text-gray-500 dark:text-slate-400">No hay cuentas bancarias aún</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {accounts.map((account) => (
            <div key={account.id} className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-semibold text-gray-800 dark:text-slate-100">{account.name}</h4>
                  <p className="text-xs text-gray-500 dark:text-slate-400">
                    {account.bank_name ? `${account.bank_name} · ` : ''}
                    {ACCOUNT_TYPE_LABELS[account.account_type]}
                    {account.last4 ? ` · ****${account.last4}` : ''}
                  </p>
                </div>
                <div className="flex gap-1">
                  <button
                    onClick={() => handleEdit(account)}
                    className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-brand-indigo"
                  >
                    <Pencil size={14} />
                  </button>
                  <button
                    onClick={() => setDeletingId(account.id)}
                    className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 hover:bg-rose-50 hover:text-rose-500"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
              <div className="mt-3 flex items-center justify-between text-sm">
                <span className="text-gray-500 dark:text-slate-400">{account.currency}</span>
                <span className="font-semibold text-gray-800 dark:text-slate-100">
                  ${account.balance.toLocaleString('es-AR')}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {showForm && <AccountForm account={editing} onClose={() => setShowForm(false)} />}

      {deletingId && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 px-4 py-8 sm:py-12">
          <div className="w-full max-w-sm rounded-xl bg-white dark:bg-slate-800 p-6 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">Eliminar cuenta</h3>
            <p className="mt-2 text-sm text-gray-500 dark:text-slate-400">
              ¿Estás seguro de que querés eliminar esta cuenta bancaria? Esta acción no se puede deshacer.
            </p>
            <div className="mt-4 flex justify-end gap-3">
              <button
                onClick={() => setDeletingId(null)}
                className="rounded-lg border border-gray-200 dark:border-slate-700 px-4 py-2 text-sm font-medium text-gray-600 dark:text-slate-300 transition-colors hover:bg-gray-50 dark:hover:bg-slate-700/50"
              >
                Cancelar
              </button>
              <button
                onClick={handleConfirmDelete}
                className="rounded-lg bg-rose-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-rose-600"
              >
                Eliminar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
