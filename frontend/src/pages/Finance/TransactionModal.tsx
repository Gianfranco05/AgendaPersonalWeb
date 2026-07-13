import { useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { X } from 'lucide-react';
import { useCategories, saveTransaction } from '../../hooks/useFinance';
import type { Transaction } from '../../types';

const schema = z.object({
  type: z.enum(['income', 'expense']),
  amount: z.number().positive('El monto debe ser positivo'),
  currency: z.enum(['ARS', 'USD']),
  transaction_date: z.string().min(1, 'La fecha es requerida'),
  product_name: z.string().min(1, 'La descripción es requerida'),
  merchant_name: z.string(),
  category_name: z.string(),
  payment_method: z.string().min(1, 'El método de pago es requerido'),
});

type FormData = z.infer<typeof schema>;

interface Props {
  transaction: Transaction | null;
  txParams: Parameters<typeof saveTransaction>[2];
  onClose: () => void;
  onSaved: () => void;
}

const inputCls =
  'w-full rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-2 text-sm focus:border-brand-indigo focus:outline-none focus:ring-1 focus:ring-brand-indigo';
const errorCls = 'mt-1 text-xs text-red-500';

export default function TransactionModal({ transaction, txParams, onClose, onSaved }: Props) {
  const { data: categories = [] } = useCategories();

  const {
    register,
    handleSubmit,
    control,
    reset,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormData, unknown, FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      type: 'expense' as const,
      amount: 0,
      currency: 'ARS' as const,
      transaction_date: new Date().toISOString().split('T')[0],
      product_name: '',
      merchant_name: '',
      category_name: '',
      payment_method: 'Efectivo',
    },
  });

  const txType = watch('type');

  useEffect(() => {
    if (transaction) {
      reset({
        type: transaction.type,
        amount: transaction.amount,
        currency: transaction.currency === 'USD' ? 'USD' : 'ARS',
        transaction_date: transaction.transaction_date,
        product_name: transaction.product_name,
        merchant_name: transaction.merchant_name ?? '',
        category_name: transaction.category_name ?? '',
        payment_method: transaction.payment_method ?? 'Efectivo',
      });
    }
  }, [transaction, reset]);

  async function onSubmit(data: FormData) {
    await saveTransaction(transaction, data as Omit<Transaction, 'id'>, txParams);
    onSaved();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 px-4 py-8 sm:py-12">
      <div className="w-full max-w-lg rounded-xl bg-white dark:bg-slate-800 shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-100 dark:border-slate-800 px-6 py-4">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">
            {transaction ? 'Editar transacción' : 'Nueva transacción'}
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-gray-400 dark:text-slate-500 hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-gray-600 dark:hover:text-slate-200"
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 px-6 py-4">
          {/* Type toggle */}
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Tipo</label>
            <Controller
              name="type"
              control={control}
              render={({ field }) => (
                <div className="flex rounded-lg border border-gray-200 dark:border-slate-700 p-0.5">
                  <button
                    type="button"
                    onClick={() => field.onChange('income')}
                    className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                      txType === 'income'
                        ? 'bg-emerald-500 text-white'
                        : 'text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-100'
                    }`}
                  >
                    Ingreso
                  </button>
                  <button
                    type="button"
                    onClick={() => field.onChange('expense')}
                    className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                      txType === 'expense'
                        ? 'bg-rose-500 text-white'
                        : 'text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-100'
                    }`}
                  >
                    Egreso
                  </button>
                </div>
              )}
            />
          </div>

          {/* Amount */}
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Monto</label>
            <input
              {...register('amount', { valueAsNumber: true })}
              type="number"
              step="0.01"
              className={inputCls}
              placeholder="0.00"
            />
            {errors.amount && <p className={errorCls}>{errors.amount.message}</p>}
          </div>

          {/* Date */}
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Fecha</label>
            <input
              {...register('transaction_date')}
              type="date"
              className={inputCls}
            />
            {errors.transaction_date && (
              <p className={errorCls}>{errors.transaction_date.message}</p>
            )}
          </div>

          {/* Description */}
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Descripción</label>
            <input
              {...register('product_name')}
              type="text"
              className={inputCls}
              placeholder="Ej: Compra supermercado"
            />
            {errors.product_name && <p className={errorCls}>{errors.product_name.message}</p>}
          </div>

          {/* Merchant */}
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Comercio</label>
            <input
              {...register('merchant_name')}
              type="text"
              className={inputCls}
              placeholder="Ej: Carrefour"
            />
          </div>

          {/* Category */}
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Categoría</label>
            <select {...register('category_name')} className={inputCls}>
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
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Método de pago</label>
            <select {...register('payment_method')} className={inputCls}>
              <option value="Efectivo">Efectivo</option>
              <option value="Tarjeta">Tarjeta</option>
              <option value="Transferencia">Transferencia</option>
              <option value="Débito">Débito</option>
            </select>
            {errors.payment_method && (
              <p className={errorCls}>{errors.payment_method.message}</p>
            )}
          </div>

          {/* Actions */}
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
              disabled={isSubmitting}
              className="rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-charcoal-hover disabled:opacity-50"
            >
              {isSubmitting ? 'Guardando…' : transaction ? 'Actualizar' : 'Crear'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
