import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { X } from 'lucide-react';
import { confirmPending, skipPending } from '../../hooks/useRecurring';
import type { InvestmentCurrency, Occurrence } from '../../types';
import { apiErrorMessage } from '../../utils/apiError';
import { formatMoney, parseDecimal } from '../../utils/investments';
import { formatShortDate } from '../../utils/recurring';

const MAX_AMOUNT = 9_999_999_999.99;

// Monto como string (coma decimal) y parseo a mano: z.coerce rompe RHF.
const schema = z
  .object({
    amount: z.string(),
    transaction_date: z.string().min(1, 'La fecha es requerida'),
    notes: z.string().max(2000, 'Máximo 2000 caracteres'),
  })
  .superRefine((v, ctx) => {
    const n = parseDecimal(v.amount);
    if (n === null || n <= 0) {
      ctx.addIssue({ code: 'custom', path: ['amount'], message: 'Ingresá un monto mayor a 0' });
    } else if (n > MAX_AMOUNT) {
      ctx.addIssue({ code: 'custom', path: ['amount'], message: 'Monto fuera de rango' });
    }
  });

type FormData = z.infer<typeof schema>;

interface Props {
  occurrence: Occurrence;
  onClose: () => void;
  onDone: () => void;
}

const inputCls =
  'w-full rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:border-brand-indigo focus:outline-none focus:ring-1 focus:ring-brand-indigo';
const labelCls = 'mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400';
const errorCls = 'mt-1 text-xs text-red-500';

export default function ConfirmOccurrenceModal({ occurrence, onClose, onDone }: Props) {
  const [error, setError] = useState<string | null>(null);
  const [skipping, setSkipping] = useState(false);
  const currency = (occurrence.currency ?? 'ARS') as InvestmentCurrency;

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData, unknown, FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      amount:
        occurrence.suggested_amount === null ? '' : String(occurrence.suggested_amount).replace('.', ','),
      transaction_date: occurrence.occurrence_date,
      notes: '',
    },
  });

  async function onSubmit(data: FormData) {
    setError(null);
    try {
      await confirmPending(occurrence.id, {
        amount: parseDecimal(data.amount) as number,
        transaction_date: data.transaction_date,
        ...(data.notes.trim() && { notes: data.notes.trim() }),
      });
      onDone();
    } catch (err) {
      setError(apiErrorMessage(err, 'No se pudo confirmar. Probá de nuevo.'));
    }
  }

  async function handleSkip() {
    setError(null);
    setSkipping(true);
    try {
      await skipPending(occurrence.id);
      onDone();
    } catch (err) {
      setError(apiErrorMessage(err, 'No se pudo saltear. Probá de nuevo.'));
    } finally {
      setSkipping(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 px-4 py-8 sm:py-12">
      <div
        role="dialog"
        aria-label="Confirmar movimiento"
        className="w-full max-w-md rounded-xl bg-white dark:bg-slate-800 shadow-xl"
      >
        <div className="flex items-center justify-between border-b border-gray-100 dark:border-slate-700 px-6 py-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">
              Confirmar {occurrence.name ?? 'movimiento'}
            </h3>
            <p className="text-xs text-gray-500 dark:text-slate-400">
              Corresponde al {formatShortDate(occurrence.occurrence_date)}
              {occurrence.suggested_amount !== null && (
                <> · sugerido {formatMoney(occurrence.suggested_amount, currency)}</>
              )}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar"
            className="rounded-lg p-1 text-gray-400 dark:text-slate-500 hover:bg-gray-100 dark:hover:bg-slate-700"
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 px-6 py-4">
          <div>
            <label htmlFor="occ-amount" className={labelCls}>Monto</label>
            <input
              id="occ-amount"
              {...register('amount')}
              inputMode="decimal"
              autoFocus
              className={inputCls}
              placeholder="0,00"
            />
            {errors.amount && <p className={errorCls}>{errors.amount.message}</p>}
          </div>
          <div>
            <label htmlFor="occ-date" className={labelCls}>Fecha</label>
            <input id="occ-date" type="date" {...register('transaction_date')} className={inputCls} />
            {errors.transaction_date && <p className={errorCls}>{errors.transaction_date.message}</p>}
          </div>
          <div>
            <label htmlFor="occ-notes" className={labelCls}>Notas (opcional)</label>
            <input id="occ-notes" {...register('notes')} className={inputCls} />
            {errors.notes && <p className={errorCls}>{errors.notes.message}</p>}
          </div>

          {error && (
            <p role="alert" className="rounded-lg bg-red-50 dark:bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-400">
              {error}
            </p>
          )}

          <div className="flex items-center justify-between gap-3 pt-2">
            <button
              type="button"
              onClick={handleSkip}
              disabled={skipping || isSubmitting}
              className="rounded-lg px-3 py-2 text-sm font-medium text-gray-500 dark:text-slate-400 transition-colors hover:bg-gray-100 dark:hover:bg-slate-700 disabled:opacity-50"
            >
              {skipping ? 'Salteando…' : 'Saltear'}
            </button>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg border border-gray-200 dark:border-slate-700 px-4 py-2 text-sm font-medium text-gray-600 dark:text-slate-300 transition-colors hover:bg-gray-50 dark:hover:bg-slate-700/50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={isSubmitting || skipping}
                className="rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-charcoal-hover disabled:opacity-50"
              >
                {isSubmitting ? 'Confirmando…' : 'Confirmar'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
