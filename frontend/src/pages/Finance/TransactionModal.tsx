import { useState, useEffect, type FormEvent } from 'react';
import { X } from 'lucide-react';
import { createTransaction, updateTransaction, fetchCategories } from '../../api/endpoints';
import type { Transaction, Category } from '../../types';

interface TransactionModalProps {
  transaction: Transaction | null;
  onClose: () => void;
  onSaved: () => void;
}

interface FormData {
  product_name: string;
  amount: string;
  type: 'income' | 'expense';
  transaction_date: string;
  merchant_name: string;
  category_name: string;
  payment_method: string;
}

export default function TransactionModal({ transaction, onClose, onSaved }: TransactionModalProps) {
  const [categories, setCategories] = useState<Category[]>([]);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<FormData>({
    product_name: '',
    amount: '',
    type: 'expense',
    transaction_date: new Date().toISOString().split('T')[0],
    merchant_name: '',
    category_name: '',
    payment_method: 'Efectivo',
  });

  useEffect(() => {
    fetchCategories().then(setCategories).catch(() => {});
  }, []);

  useEffect(() => {
    if (transaction) {
      setForm({
        product_name: transaction.product_name,
        amount: String(transaction.amount),
        type: transaction.type,
        transaction_date: transaction.transaction_date,
        merchant_name: transaction.merchant_name || '',
        category_name: transaction.category_name || '',
        payment_method: transaction.payment_method || 'Efectivo',
      });
    }
  }, [transaction]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    const data = {
      amount: Number(form.amount),
      currency: 'ARS' as const,
      type: form.type,
      transaction_date: form.transaction_date,
      product_name: form.product_name,
      merchant_name: form.merchant_name,
      payment_method: form.payment_method,
      category_name: form.category_name || undefined,
    };

    if (transaction) {
      await updateTransaction(transaction.id, data);
    } else {
      await createTransaction(data as Omit<Transaction, 'id'>);
    }
    setSaving(false);
    onSaved();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-lg rounded-xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
          <h3 className="text-lg font-semibold text-gray-800">
            {transaction ? 'Editar transacción' : 'Nueva transacción'}
          </h3>
          <button onClick={onClose} className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 px-6 py-4">
          {/* Type toggle */}
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500">Tipo</label>
            <div className="flex rounded-lg border border-gray-200 p-0.5">
              <button
                type="button"
                onClick={() => setForm((f) => ({ ...f, type: 'income' }))}
                className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                  form.type === 'income'
                    ? 'bg-emerald-500 text-white'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                Ingreso
              </button>
              <button
                type="button"
                onClick={() => setForm((f) => ({ ...f, type: 'expense' }))}
                className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                  form.type === 'expense'
                    ? 'bg-rose-500 text-white'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                Egreso
              </button>
            </div>
          </div>

          {/* Amount */}
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500">Monto</label>
            <input
              type="number"
              step="0.01"
              required
              value={form.amount}
              onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-[#7C3AED] focus:outline-none focus:ring-1 focus:ring-[#7C3AED]"
              placeholder="0.00"
            />
          </div>

          {/* Date */}
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500">Fecha</label>
            <input
              type="date"
              required
              value={form.transaction_date}
              onChange={(e) => setForm((f) => ({ ...f, transaction_date: e.target.value }))}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-[#7C3AED] focus:outline-none focus:ring-1 focus:ring-[#7C3AED]"
            />
          </div>

          {/* Description */}
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500">Descripción</label>
            <input
              type="text"
              required
              value={form.product_name}
              onChange={(e) => setForm((f) => ({ ...f, product_name: e.target.value }))}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-[#7C3AED] focus:outline-none focus:ring-1 focus:ring-[#7C3AED]"
              placeholder="Ej: Compra supermercado"
            />
          </div>

          {/* Merchant */}
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500">Comercio</label>
            <input
              type="text"
              value={form.merchant_name}
              onChange={(e) => setForm((f) => ({ ...f, merchant_name: e.target.value }))}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-[#7C3AED] focus:outline-none focus:ring-1 focus:ring-[#7C3AED]"
              placeholder="Ej: Carrefour"
            />
          </div>

          {/* Category */}
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500">Categoría</label>
            <select
              value={form.category_name}
              onChange={(e) => setForm((f) => ({ ...f, category_name: e.target.value }))}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-[#7C3AED] focus:outline-none focus:ring-1 focus:ring-[#7C3AED]"
            >
              <option value="">Sin categoría</option>
              {categories.map((cat) => (
                <option key={cat.id} value={cat.name}>
                  {cat.name}
                </option>
              ))}
            </select>
          </div>

          {/* Payment method */}
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500">Método de pago</label>
            <select
              value={form.payment_method}
              onChange={(e) => setForm((f) => ({ ...f, payment_method: e.target.value }))}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-[#7C3AED] focus:outline-none focus:ring-1 focus:ring-[#7C3AED]"
            >
              <option value="Efectivo">Efectivo</option>
              <option value="Tarjeta">Tarjeta</option>
              <option value="Transferencia">Transferencia</option>
              <option value="Débito">Débito</option>
            </select>
          </div>

          {/* Buttons */}
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-[#7C3AED] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#6D28D9] disabled:opacity-50"
            >
              {saving ? 'Guardando...' : transaction ? 'Actualizar' : 'Crear'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
