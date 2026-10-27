import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { X } from 'lucide-react';
import { useBankAccounts, useCategories } from '../../hooks/useFinance';
import { saveRecurring } from '../../hooks/useRecurring';
import { previewRecurring } from '../../api/endpoints';
import type { Recurring, RecurringFrequency, RecurringInput } from '../../types';
import { toLocalDateString } from '../../utils/date';
import { apiErrorMessage } from '../../utils/apiError';
import { parseDecimal } from '../../utils/investments';
import {
  FREQUENCY_LABELS,
  INTERVAL_UNITS,
  MAX_INTERVAL,
  MONTH_NAMES,
  WEEKDAY_NAMES,
  formatShortDate,
} from '../../utils/recurring';

const MAX_AMOUNT = 9_999_999_999.99;
const PREVIEW_DEBOUNCE_MS = 400;

// Valores del enum PaymentMethod del backend (no las etiquetas en español).
const PAYMENT_METHODS = [
  { value: 'cash', label: 'Efectivo' },
  { value: 'debit_card', label: 'Débito' },
  { value: 'credit_card', label: 'Tarjeta de crédito' },
  { value: 'transfer', label: 'Transferencia' },
  { value: 'other', label: 'Otro' },
] as const;

// Campos numéricos como string (coma decimal) y parseo a mano: z.coerce rompe el
// tipado de react-hook-form con zodResolver.
const schema = z
  .object({
    type: z.enum(['income', 'expense']),
    name: z.string().trim().min(1, 'El nombre es requerido').max(255, 'Máximo 255 caracteres'),
    amount: z.string(),
    currency: z.enum(['ARS', 'USD']),
    category_id: z.string(),
    bank_account_id: z.string(),
    payment_method: z.string().min(1),
    notes: z.string().max(2000, 'Máximo 2000 caracteres'),
    frequency: z.enum(['daily', 'weekly', 'monthly', 'yearly']),
    interval_count: z.string(),
    weekday: z.string(),
    day_of_month: z.string(),
    month_of_year: z.string(),
    start_date: z.string().min(1, 'La fecha de inicio es requerida'),
    end_date: z.string(),
    requires_confirmation: z.boolean(),
    notify: z.boolean(),
    generate_past: z.boolean(),
  })
  .superRefine((v, ctx) => {
    const issue = (path: keyof FormData, message: string) =>
      ctx.addIssue({ code: 'custom', path: [path], message });

    if (v.amount.trim()) {
      const n = parseDecimal(v.amount);
      if (n === null || n <= 0) issue('amount', 'El monto debe ser mayor a 0');
      else if (n > MAX_AMOUNT) issue('amount', 'Monto fuera de rango');
    } else if (!v.requires_confirmation) {
      issue('amount', 'Ingresá el monto o activá «Confirmar el monto antes de registrar»');
    }

    const interval = Number(v.interval_count);
    const max = MAX_INTERVAL[v.frequency];
    if (!Number.isInteger(interval) || interval < 1 || interval > max) {
      issue('interval_count', `Entre 1 y ${max}`);
    }
    if (v.frequency === 'weekly' && v.weekday === '') issue('weekday', 'Elegí el día de la semana');
    if (v.frequency === 'monthly' || v.frequency === 'yearly') {
      const day = Number(v.day_of_month);
      if (!Number.isInteger(day) || day < 1 || day > 31) issue('day_of_month', 'Entre 1 y 31');
      else if (v.frequency === 'yearly' && v.month_of_year !== '') {
        // 29/02 vale (cae el 28 en años no bisiestos); 30/02 y 31/04 no existen nunca.
        const daysInMonth = new Date(2000, Number(v.month_of_year), 0).getDate();
        if (day > daysInMonth) issue('day_of_month', 'Ese día no existe en el mes elegido');
      }
    }
    if (v.frequency === 'yearly' && v.month_of_year === '') issue('month_of_year', 'Elegí el mes');
    if (v.end_date && v.start_date && v.end_date < v.start_date) {
      issue('end_date', 'El fin no puede ser anterior al inicio');
    }
  });

type FormData = z.infer<typeof schema>;

/** Datos con los que se abre el formulario desde una transacción ("Hacer recurrente"). */
export interface RecurringPrefill {
  type?: 'income' | 'expense';
  name?: string;
  amount?: number;
  currency?: string;
  category_id?: string;
  payment_method?: string;
  start_date?: string;
  day_of_month?: number;
}

interface Props {
  recurring: Recurring | null;
  prefill?: RecurringPrefill;
  onClose: () => void;
  onSaved: () => void;
}

const inputCls =
  'w-full rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:border-brand-indigo focus:outline-none focus:ring-1 focus:ring-brand-indigo';
const labelCls = 'mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400';
const errorCls = 'mt-1 text-xs text-red-500';

const asText = (n: number | null | undefined) => (n === null || n === undefined ? '' : String(n).replace('.', ','));

function defaultValues(prefill?: RecurringPrefill): FormData {
  const start = prefill?.start_date ?? toLocalDateString();
  return {
    type: prefill?.type ?? 'expense',
    name: prefill?.name ?? '',
    amount: asText(prefill?.amount),
    currency: prefill?.currency === 'USD' ? 'USD' : 'ARS',
    category_id: prefill?.category_id ?? '',
    bank_account_id: '',
    payment_method: prefill?.payment_method ?? 'cash',
    notes: '',
    frequency: 'monthly',
    interval_count: '1',
    weekday: '0',
    day_of_month: String(prefill?.day_of_month ?? Number(start.slice(8, 10))),
    month_of_year: String(Number(start.slice(5, 7))),
    start_date: start,
    end_date: '',
    requires_confirmation: false,
    notify: true,
    generate_past: false,
  };
}

function toForm(r: Recurring): FormData {
  return {
    type: r.type,
    name: r.name,
    amount: asText(r.amount),
    currency: r.currency === 'USD' ? 'USD' : 'ARS',
    category_id: r.category_id ?? '',
    bank_account_id: r.bank_account_id ?? '',
    payment_method: r.payment_method,
    notes: r.notes ?? '',
    frequency: r.frequency,
    interval_count: String(r.interval_count),
    weekday: r.weekday === null ? '0' : String(r.weekday),
    day_of_month: r.day_of_month === null ? '1' : String(r.day_of_month),
    month_of_year: r.month_of_year === null ? '1' : String(r.month_of_year),
    start_date: r.start_date,
    end_date: r.end_date ?? '',
    requires_confirmation: r.requires_confirmation,
    notify: r.notify,
    generate_past: false,
  };
}

function toInput(v: FormData, existing: Recurring | null): RecurringInput {
  const amount = v.amount.trim() ? parseDecimal(v.amount) : null;
  return {
    type: v.type,
    name: v.name.trim(),
    description: existing?.description ?? null,
    notes: v.notes.trim() || null,
    amount,
    currency: v.currency,
    category_id: v.category_id || null,
    bank_account_id: v.bank_account_id || null,
    account_type: existing?.account_type ?? 'cash',
    payment_method: v.payment_method,
    merchant_name: existing?.merchant_name ?? '',
    merchant_category: existing?.merchant_category ?? 'other',
    frequency: v.frequency,
    interval_count: Number(v.interval_count),
    // Solo los campos que aplican a la frecuencia; el server guarda null en el resto.
    weekday: v.frequency === 'weekly' ? Number(v.weekday) : null,
    day_of_month: v.frequency === 'monthly' || v.frequency === 'yearly' ? Number(v.day_of_month) : null,
    month_of_year: v.frequency === 'yearly' ? Number(v.month_of_year) : null,
    start_date: v.start_date,
    end_date: v.end_date || null,
    requires_confirmation: v.requires_confirmation,
    notify: v.notify,
    ...(existing === null && v.generate_past && { generate_past: true }),
  };
}

/** Vista previa de las próximas fechas con debounce de 400 ms. Usa el cálculo
 *  del server (la UI no reimplementa la regla); si falla, no bloquea el alta. */
function usePreview(values: FormData, valid: boolean) {
  const [dates, setDates] = useState<string[] | null>(null);
  const [failed, setFailed] = useState(false);

  const rule = [
    values.frequency,
    values.interval_count,
    values.weekday,
    values.day_of_month,
    values.month_of_year,
    values.start_date,
    values.end_date,
    values.generate_past,
  ].join('|');

  useEffect(() => {
    if (!valid) {
      setDates(null);
      return;
    }
    let cancelled = false;
    const timer = setTimeout(() => {
      const input = toInput(values, null);
      previewRecurring({
        frequency: input.frequency,
        interval_count: input.interval_count,
        weekday: input.weekday,
        day_of_month: input.day_of_month,
        month_of_year: input.month_of_year,
        start_date: input.start_date,
        end_date: input.end_date,
        generate_past: values.generate_past,
      })
        .then((res) => {
          if (!cancelled) {
            setDates(res.dates);
            setFailed(false);
          }
        })
        .catch(() => {
          if (!cancelled) setFailed(true);
        });
    }, PREVIEW_DEBOUNCE_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
    // `rule` resume todos los campos que cambian el resultado.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rule, valid]);

  return { dates, failed };
}

export default function RecurringModal({ recurring, prefill, onClose, onSaved }: Props) {
  const { data: categories = [] } = useCategories();
  const { data: accounts = [] } = useBankAccounts();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    reset,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormData, unknown, FormData>({
    resolver: zodResolver(schema),
    defaultValues: recurring ? toForm(recurring) : defaultValues(prefill),
  });

  useEffect(() => {
    if (recurring) reset(toForm(recurring));
  }, [recurring, reset]);

  const values = watch();
  const frequency: RecurringFrequency = values.frequency;
  const today = toLocalDateString();
  const rulePreviewValid = isRuleValid(values);
  const { dates, failed } = usePreview(values, rulePreviewValid);

  const dayOfMonth = Number(values.day_of_month);
  const showShortMonthHelp = (frequency === 'monthly' || frequency === 'yearly') && dayOfMonth > 28;
  const showPastOption = recurring === null && values.start_date !== '' && values.start_date < today;

  async function onSubmit(data: FormData) {
    setSubmitError(null);
    try {
      await saveRecurring(recurring, toInput(data, recurring));
      onSaved();
    } catch (err) {
      setSubmitError(apiErrorMessage(err, 'No se pudo guardar. Probá de nuevo.'));
    }
  }

  const [unitSingular, unitPlural] = INTERVAL_UNITS[frequency];

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 px-4 py-8 sm:py-12">
      <div
        role="dialog"
        aria-label={recurring ? 'Editar recurrente' : 'Nueva recurrente'}
        className="w-full max-w-lg rounded-xl bg-white dark:bg-slate-800 shadow-xl"
      >
        <div className="flex items-center justify-between border-b border-gray-100 dark:border-slate-700 px-6 py-4">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">
            {recurring ? 'Editar recurrente' : 'Nuevo movimiento recurrente'}
          </h3>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar"
            className="rounded-lg p-1 text-gray-400 dark:text-slate-500 hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-gray-600 dark:hover:text-slate-200"
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 px-6 py-4">
          <div>
            <label className={labelCls}>Tipo</label>
            <div className="flex rounded-lg border border-gray-200 dark:border-slate-700 p-0.5">
              {(['income', 'expense'] as const).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setValue('type', t, { shouldDirty: true })}
                  className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                    values.type === t
                      ? t === 'income'
                        ? 'bg-emerald-500 text-white'
                        : 'bg-rose-500 text-white'
                      : 'text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-100'
                  }`}
                >
                  {t === 'income' ? 'Ingreso' : 'Egreso'}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label htmlFor="rec-name" className={labelCls}>Nombre</label>
            <input id="rec-name" {...register('name')} className={inputCls} placeholder="Ej: Sueldo, Alquiler, Netflix" />
            {errors.name && <p className={errorCls}>{errors.name.message}</p>}
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2">
              <label htmlFor="rec-amount" className={labelCls}>Monto</label>
              <input
                id="rec-amount"
                {...register('amount')}
                inputMode="decimal"
                className={inputCls}
                placeholder={values.requires_confirmation ? 'Estimado (opcional)' : '0,00'}
              />
              {errors.amount && <p className={errorCls}>{errors.amount.message}</p>}
            </div>
            <div>
              <label htmlFor="rec-currency" className={labelCls}>Moneda</label>
              <select id="rec-currency" {...register('currency')} className={inputCls}>
                <option value="ARS">ARS</option>
                <option value="USD">USD</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label htmlFor="rec-category" className={labelCls}>Categoría</label>
              <select id="rec-category" {...register('category_id')} className={inputCls}>
                <option value="">Sin categoría</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="rec-account" className={labelCls}>Cuenta</label>
              <select id="rec-account" {...register('bank_account_id')} className={inputCls}>
                <option value="">Sin cuenta</option>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="rec-payment" className={labelCls}>Medio de pago</label>
            <select id="rec-payment" {...register('payment_method')} className={inputCls}>
              {PAYMENT_METHODS.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
          </div>

          {/* Frecuencia */}
          <fieldset className="space-y-3 rounded-lg border border-gray-100 dark:border-slate-700 p-3">
            <legend className="px-1 text-xs font-medium text-gray-500 dark:text-slate-400">Se repite</legend>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="rec-frequency" className={labelCls}>Frecuencia</label>
                <select id="rec-frequency" {...register('frequency')} className={inputCls}>
                  {(Object.keys(FREQUENCY_LABELS) as RecurringFrequency[]).map((f) => (
                    <option key={f} value={f}>
                      {FREQUENCY_LABELS[f]}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="rec-interval" className={labelCls}>
                  Cada ({Number(values.interval_count) === 1 ? unitSingular : unitPlural})
                </label>
                <input
                  id="rec-interval"
                  {...register('interval_count')}
                  inputMode="numeric"
                  className={inputCls}
                />
                {errors.interval_count && <p className={errorCls}>{errors.interval_count.message}</p>}
              </div>
            </div>

            {frequency === 'weekly' && (
              <div>
                <label htmlFor="rec-weekday" className={labelCls}>Día de la semana</label>
                <select id="rec-weekday" {...register('weekday')} className={inputCls}>
                  {WEEKDAY_NAMES.map((name, i) => (
                    <option key={name} value={i}>
                      {name}
                    </option>
                  ))}
                </select>
                {errors.weekday && <p className={errorCls}>{errors.weekday.message}</p>}
              </div>
            )}

            {(frequency === 'monthly' || frequency === 'yearly') && (
              <div className={frequency === 'yearly' ? 'grid grid-cols-2 gap-3' : ''}>
                <div>
                  <label htmlFor="rec-dom" className={labelCls}>Día del mes</label>
                  <input id="rec-dom" {...register('day_of_month')} inputMode="numeric" className={inputCls} />
                  {errors.day_of_month && <p className={errorCls}>{errors.day_of_month.message}</p>}
                </div>
                {frequency === 'yearly' && (
                  <div>
                    <label htmlFor="rec-month" className={labelCls}>Mes</label>
                    <select id="rec-month" {...register('month_of_year')} className={inputCls}>
                      {MONTH_NAMES.map((name, i) => (
                        <option key={name} value={i + 1}>
                          {name}
                        </option>
                      ))}
                    </select>
                    {errors.month_of_year && <p className={errorCls}>{errors.month_of_year.message}</p>}
                  </div>
                )}
              </div>
            )}
            {showShortMonthHelp && (
              <p className="text-xs text-gray-500 dark:text-slate-400" data-testid="short-month-help">
                Si el mes es más corto, cae el último día del mes. El día 31 funciona como «último día del mes».
              </p>
            )}

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="rec-start" className={labelCls}>Desde</label>
                <input id="rec-start" type="date" {...register('start_date')} className={inputCls} />
                {errors.start_date && <p className={errorCls}>{errors.start_date.message}</p>}
              </div>
              <div>
                <label htmlFor="rec-end" className={labelCls}>Hasta (opcional)</label>
                <input id="rec-end" type="date" {...register('end_date')} className={inputCls} />
                {errors.end_date && <p className={errorCls}>{errors.end_date.message}</p>}
              </div>
            </div>

            <div data-testid="recurring-preview" className="rounded-lg bg-gray-50 dark:bg-slate-900/40 px-3 py-2 text-xs text-gray-600 dark:text-slate-300">
              <p className="font-medium text-gray-700 dark:text-slate-200">Próximas fechas</p>
              {dates === null ? (
                <p className="text-gray-400 dark:text-slate-500">
                  {failed ? 'No se pudo calcular ahora.' : 'Completá la regla para ver las fechas.'}
                </p>
              ) : dates.length === 0 ? (
                <p className="text-gray-400 dark:text-slate-500">No hay fechas con esta regla.</p>
              ) : (
                <p>{dates.map(formatShortDate).join(' · ')}</p>
              )}
              {recurring && (
                <p className="mt-1 text-gray-400 dark:text-slate-500">
                  Si cambiás la regla, las fechas se recalculan desde hoy: lo ya registrado no se modifica.
                </p>
              )}
            </div>
          </fieldset>

          <div className="space-y-2">
            <label className="flex items-start gap-2 text-sm text-gray-700 dark:text-slate-200">
              <input type="checkbox" {...register('requires_confirmation')} className="mt-0.5" />
              <span>
                Confirmar el monto antes de registrar
                <span className="block text-xs text-gray-500 dark:text-slate-400">
                  Para montos variables (luz, gas): queda pendiente hasta que lo confirmes.
                </span>
              </span>
            </label>
            <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-slate-200">
              <input type="checkbox" {...register('notify')} />
              Avisarme cuando se registre
            </label>
            {showPastOption && (
              <label className="flex items-start gap-2 text-sm text-gray-700 dark:text-slate-200">
                <input type="checkbox" {...register('generate_past')} className="mt-0.5" />
                <span>
                  Registrar también los anteriores
                  <span className="block text-xs text-gray-500 dark:text-slate-400">
                    Crea los movimientos desde la fecha de inicio hasta hoy (máximo 120).
                  </span>
                </span>
              </label>
            )}
          </div>

          <div>
            <label htmlFor="rec-notes" className={labelCls}>Notas (opcional)</label>
            <input id="rec-notes" {...register('notes')} className={inputCls} />
            {errors.notes && <p className={errorCls}>{errors.notes.message}</p>}
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
              className="rounded-lg border border-gray-200 dark:border-slate-700 px-4 py-2 text-sm font-medium text-gray-600 dark:text-slate-300 transition-colors hover:bg-gray-50 dark:hover:bg-slate-700/50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-charcoal-hover disabled:opacity-50"
            >
              {isSubmitting ? 'Guardando…' : recurring ? 'Actualizar' : 'Crear'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/** Solo los campos de la regla: la vista previa no espera a que el resto del
 *  formulario (nombre, monto) esté completo. */
function isRuleValid(v: FormData): boolean {
  if (!v.start_date) return false;
  const interval = Number(v.interval_count);
  if (!Number.isInteger(interval) || interval < 1 || interval > MAX_INTERVAL[v.frequency]) return false;
  if (v.frequency === 'weekly') return v.weekday !== '';
  if (v.frequency === 'monthly' || v.frequency === 'yearly') {
    const day = Number(v.day_of_month);
    if (!Number.isInteger(day) || day < 1 || day > 31) return false;
    if (v.frequency === 'yearly') {
      if (v.month_of_year === '') return false;
      return day <= new Date(2000, Number(v.month_of_year), 0).getDate();
    }
  }
  return !v.end_date || v.end_date >= v.start_date;
}
