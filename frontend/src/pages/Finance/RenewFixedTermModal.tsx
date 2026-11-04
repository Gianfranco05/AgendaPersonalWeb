import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { X } from 'lucide-react';
import { useBankAccounts, useCategories } from '../../hooks/useFinance';
import { renewFixedTerm } from '../../hooks/useInvestments';
import type { Investment, RenewFixedTermInput } from '../../types';
import { parseDateOnly, toLocalDateString } from '../../utils/date';
import { apiErrorMessage } from '../../utils/apiError';
import { fixedTermPreview, formatMoney, parseDecimal } from '../../utils/investments';

const MAX_AMOUNT = 9_999_999_999.99;
const TERM_CHIPS = [30, 60, 90, 180, 365];

// Campos numéricos como string (coma decimal) y parseo a mano: z.coerce rompe RHF.
const schema = z
  .object({
    mode: z.enum(['principal_and_interest', 'principal_only']),
    amount_collected: z.string(),
    interest_rate_tna: z.string(),
    term_days: z.string(),
    maturity_date: z.string(),
    start_date: z.string().min(1, 'La fecha de inicio es requerida'),
    register_interest_income: z.boolean(),
    income_category_id: z.string(),
    income_bank_account_id: z.string(),
  })
  .superRefine((v, ctx) => {
    const issue = (path: keyof FormData, message: string) =>
      ctx.addIssue({ code: 'custom', path: [path], message });

    const collected = parseDecimal(v.amount_collected);
    if (collected === null || collected <= 0 || collected > MAX_AMOUNT) {
      issue('amount_collected', 'Ingresá el monto cobrado');
    }
    const tna = parseDecimal(v.interest_rate_tna);
    if (tna === null || tna <= 0 || tna > 999.9999) issue('interest_rate_tna', 'TNA inválida (mayor a 0, hasta 999,9999)');

    if (v.maturity_date) {
      if (v.start_date && v.maturity_date <= v.start_date) {
        issue('maturity_date', 'El vencimiento debe ser posterior al inicio');
      }
    } else {
      const days = Number(v.term_days);
      if (!Number.isInteger(days) || days < 1 || days > 3650) issue('term_days', 'Entre 1 y 3650 días');
    }
  });

type FormData = z.infer<typeof schema>;

interface Props {
  investment: Investment;
  onClose: () => void;
  onDone: () => void;
}

const inputCls =
  'w-full rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:border-brand-indigo focus:outline-none focus:ring-1 focus:ring-brand-indigo';
const labelCls = 'mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400';
const errorCls = 'mt-1 text-xs text-red-500';

const asText = (n: number | null | undefined) => (n === null || n === undefined ? '' : String(n).replace('.', ','));

export default function RenewFixedTermModal({ investment, onClose, onDone }: Props) {
  const { data: categories = [] } = useCategories();
  const { data: accounts = [] } = useBankAccounts();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const today = toLocalDateString();
  const computed = investment.fixed_term?.amount_at_maturity ?? investment.invested_amount;
  const minStart = investment.maturity_date ?? today;

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormData, unknown, FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      mode: 'principal_and_interest',
      amount_collected: asText(computed),
      interest_rate_tna: asText(investment.interest_rate_tna),
      term_days: '30',
      maturity_date: '',
      start_date: today,
      register_interest_income: false,
      income_category_id: '',
      income_bank_account_id: '',
    },
  });

  const v = watch();
  const collected = parseDecimal(v.amount_collected);
  const interest = collected === null ? null : Math.round((collected - investment.invested_amount) * 100) / 100;
  const principalOnly = v.mode === 'principal_only';
  const newCapital = principalOnly ? investment.invested_amount : collected;

  // Vencimiento efectivo del nuevo plazo: la fecha elegida o inicio + días.
  let maturity = v.maturity_date;
  if (!maturity && v.start_date) {
    const days = Number(v.term_days);
    if (Number.isInteger(days) && days >= 1) {
      const d = parseDateOnly(v.start_date);
      d.setDate(d.getDate() + days);
      maturity = toLocalDateString(d);
    }
  }
  const preview = fixedTermPreview(newCapital, parseDecimal(v.interest_rate_tna), v.start_date, maturity);
  const negativeInterest = principalOnly && interest !== null && interest < 0;

  async function onSubmit(data: FormData) {
    setSubmitError(null);
    if (data.start_date < minStart || data.start_date > today) {
      setSubmitError('El inicio tiene que estar entre el vencimiento anterior y hoy.');
      return;
    }
    if (negativeInterest) {
      setSubmitError('El monto cobrado no puede ser menor al capital: el interés sería negativo.');
      return;
    }
    const input: RenewFixedTermInput = {
      mode: data.mode,
      interest_rate_tna: parseDecimal(data.interest_rate_tna) as number,
      // Fecha o días, no las dos: si coinciden mal el server responde 422.
      ...(data.maturity_date
        ? { maturity_date: data.maturity_date }
        : { term_days: Number(data.term_days) }),
      start_date: data.start_date,
      amount_collected: parseDecimal(data.amount_collected) as number,
      ...(data.mode === 'principal_only' &&
        data.register_interest_income && {
          register_interest_income: true,
          income_category_id: data.income_category_id || null,
          income_bank_account_id: data.income_bank_account_id || null,
          income_payment_method: 'transfer',
        }),
    };
    try {
      await renewFixedTerm(investment.id, input);
      onDone();
    } catch (err) {
      setSubmitError(apiErrorMessage(err, 'No se pudo renovar. Probá de nuevo.'));
    }
  }

  const cur = investment.currency;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 px-4 py-8 sm:py-12">
      <div
        role="dialog"
        aria-label="Renovar plazo fijo"
        className="w-full max-w-lg rounded-xl bg-white dark:bg-slate-800 shadow-xl"
      >
        <div className="flex items-center justify-between border-b border-gray-100 dark:border-slate-700 px-6 py-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">Renovar plazo fijo</h3>
            <p className="text-xs text-gray-500 dark:text-slate-400">
              {investment.name} · invertido {formatMoney(investment.invested_amount, cur)}
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
            <label htmlFor="renew-collected" className={labelCls}>Monto cobrado al vencer</label>
            <input
              id="renew-collected"
              {...register('amount_collected')}
              inputMode="decimal"
              className={inputCls}
            />
            <p className="mt-1 text-xs text-gray-400 dark:text-slate-500">
              Calculado: {formatMoney(computed, cur)}. Editalo si el banco acreditó otro importe.
            </p>
            {errors.amount_collected && <p className={errorCls}>{errors.amount_collected.message}</p>}
          </div>

          <fieldset className="space-y-2">
            <legend className={labelCls}>¿Qué reinvertís?</legend>
            <label className="flex items-start gap-2 rounded-lg border border-gray-200 dark:border-slate-700 p-3 text-sm text-gray-700 dark:text-slate-200">
              <input type="radio" value="principal_and_interest" {...register('mode')} className="mt-1" />
              <span>
                Capital + interés
                <span className="block text-xs text-gray-500 dark:text-slate-400">
                  Nuevo capital: {collected === null ? '—' : formatMoney(collected, cur)}
                </span>
              </span>
            </label>
            <label className="flex items-start gap-2 rounded-lg border border-gray-200 dark:border-slate-700 p-3 text-sm text-gray-700 dark:text-slate-200">
              <input type="radio" value="principal_only" {...register('mode')} className="mt-1" />
              <span>
                Solo el capital (retiro el interés)
                <span className="block text-xs text-gray-500 dark:text-slate-400" data-testid="renew-principal-only">
                  Capital {formatMoney(investment.invested_amount, cur)} · interés{' '}
                  {interest === null ? '—' : formatMoney(interest, cur)} · nuevo capital{' '}
                  {formatMoney(investment.invested_amount, cur)}
                </span>
              </span>
            </label>
            {negativeInterest && (
              <p className={errorCls}>El monto cobrado es menor al capital: el interés sería negativo.</p>
            )}
          </fieldset>

          {principalOnly && interest !== null && interest > 0 && (
            <div className="space-y-2 rounded-lg bg-gray-50 dark:bg-slate-900/40 p-3">
              <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-slate-200">
                <input type="checkbox" {...register('register_interest_income')} />
                Registrar el interés como ingreso ({formatMoney(interest, cur)})
              </label>
              {v.register_interest_income && (
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <div>
                    <label htmlFor="renew-category" className={labelCls}>Categoría</label>
                    <select id="renew-category" {...register('income_category_id')} className={inputCls}>
                      <option value="">Sin categoría</option>
                      {categories.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label htmlFor="renew-account" className={labelCls}>Cuenta</label>
                    <select id="renew-account" {...register('income_bank_account_id')} className={inputCls}>
                      <option value="">Sin cuenta</option>
                      {accounts.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="renew-tna" className={labelCls}>Nueva TNA (%)</label>
              <input id="renew-tna" {...register('interest_rate_tna')} inputMode="decimal" className={inputCls} />
              {errors.interest_rate_tna && <p className={errorCls}>{errors.interest_rate_tna.message}</p>}
            </div>
            <div>
              <label htmlFor="renew-start" className={labelCls}>Inicio</label>
              <input
                id="renew-start"
                type="date"
                min={minStart}
                max={today}
                {...register('start_date')}
                className={inputCls}
              />
              {errors.start_date && <p className={errorCls}>{errors.start_date.message}</p>}
            </div>
          </div>

          <div>
            <label htmlFor="renew-days" className={labelCls}>Plazo (días)</label>
            <div className="mb-2 flex flex-wrap gap-2">
              {TERM_CHIPS.map((days) => (
                <button
                  key={days}
                  type="button"
                  onClick={() => {
                    setValue('term_days', String(days), { shouldDirty: true });
                    setValue('maturity_date', '', { shouldDirty: true });
                  }}
                  className={`rounded-full border px-3 py-1 text-xs font-medium ${
                    !v.maturity_date && v.term_days === String(days)
                      ? 'border-brand-charcoal bg-brand-charcoal text-white'
                      : 'border-gray-200 dark:border-slate-700 text-gray-600 dark:text-slate-300'
                  }`}
                >
                  {days}
                </button>
              ))}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <input
                  id="renew-days"
                  {...register('term_days')}
                  inputMode="numeric"
                  disabled={!!v.maturity_date}
                  className={`${inputCls} disabled:opacity-50`}
                />
                {errors.term_days && <p className={errorCls}>{errors.term_days.message}</p>}
              </div>
              <div>
                <input
                  type="date"
                  aria-label="Fecha de vencimiento"
                  {...register('maturity_date')}
                  className={inputCls}
                />
                {errors.maturity_date && <p className={errorCls}>{errors.maturity_date.message}</p>}
              </div>
            </div>
            <p className="mt-1 text-xs text-gray-400 dark:text-slate-500">
              O elegí la fecha de vencimiento (reemplaza a los días).
            </p>
          </div>

          <div
            data-testid="renew-preview"
            className="rounded-lg bg-gray-50 dark:bg-slate-900/40 px-3 py-2 text-xs text-gray-600 dark:text-slate-300"
          >
            {preview ? (
              <>
                <p className="font-medium text-gray-700 dark:text-slate-200">
                  Nuevo plazo de {preview.termDays} días
                </p>
                <p>
                  Interés {formatMoney(preview.interest, cur)} · al vencimiento{' '}
                  {formatMoney(preview.amountAtMaturity, cur)}
                </p>
              </>
            ) : (
              <p className="text-gray-400 dark:text-slate-500">Completá la TNA y el plazo para ver el cálculo.</p>
            )}
          </div>

          {submitError && (
            <p role="alert" className="rounded-lg bg-red-50 dark:bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-400">
              {submitError}
            </p>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-gray-200 dark:border-slate-700 px-4 py-2 text-sm font-medium text-gray-600 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700/50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white hover:bg-brand-charcoal-hover disabled:opacity-50"
            >
              {isSubmitting ? 'Renovando…' : 'Renovar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
