import { useEffect, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { X } from 'lucide-react';
import { saveInvestment } from '../../hooks/useInvestments';
import { useCryptoAssets } from '../../hooks/useMarket';
import type { AssetType, Investment, InvestmentCurrency, InvestmentInput } from '../../types';
import { toLocalDateString } from '../../utils/date';
import { apiErrorMessage } from '../../utils/apiError';
import {
  ASSET_TYPES,
  ASSET_TYPE_LABELS,
  fixedTermPreview,
  formatMoney,
  parseDecimal,
} from '../../utils/investments';

const MAX_AMOUNT = 9_999_999_999.99;

// Qué campos aplican a cada tipo de activo. Los que no aplican se mandan en
// null para que, al cambiar el tipo de una inversión existente, no queden
// datos viejos escondidos.
const HAS_QUANTITY: AssetType[] = ['stock', 'crypto', 'bond', 'fund', 'fx'];
const HAS_TICKER: AssetType[] = ['stock', 'crypto', 'bond', 'fund', 'fx'];
const HAS_TNA: AssetType[] = ['fixed_term', 'bond', 'other'];
// El vencimiento solo tiene sentido en estos; la fecha de inicio/compra en todos
// (con ella se calcula el rendimiento contra la inflación).
const HAS_MATURITY: AssetType[] = ['fixed_term', 'bond', 'fund', 'other'];

// Se usa string en los campos numéricos (coma decimal) y se parsea a mano:
// z.coerce rompe el tipado de react-hook-form con zodResolver.
const schema = z
  .object({
    asset_type: z.enum([
      'stock',
      'fixed_term',
      'crypto',
      'bond',
      'fund',
      'fx',
      'real_estate',
      'vehicle',
      'other',
    ]),
    name: z.string().trim().min(1, 'El nombre es requerido').max(120, 'Máximo 120 caracteres'),
    ticker: z
      .string()
      .trim()
      .max(20, 'Máximo 20 caracteres')
      .regex(/^[A-Za-z0-9.-]*$/, 'Solo letras, números, punto y guion'),
    currency: z.enum(['ARS', 'USD', 'USDT', 'EUR']),
    quantity: z.string(),
    invested_amount: z.string(),
    current_value: z.string(),
    interest_rate_tna: z.string(),
    start_date: z.string(),
    maturity_date: z.string(),
    institution: z.string().max(120, 'Máximo 120 caracteres'),
    notes: z.string().max(2000, 'Máximo 2000 caracteres'),
    notify_maturity: z.boolean(),
    // Cotización automática (CoinGecko), solo cripto.
    auto_quote: z.boolean(),
  })
  .superRefine((v, ctx) => {
    const issue = (path: keyof FormData, message: string) =>
      ctx.addIssue({ code: 'custom', path: [path], message });

    const invested = parseDecimal(v.invested_amount);
    if (invested === null) issue('invested_amount', 'Ingresá el monto invertido');
    else if (invested < 0 || invested > MAX_AMOUNT) issue('invested_amount', 'Monto fuera de rango');

    if (v.current_value.trim()) {
      const n = parseDecimal(v.current_value);
      if (n === null || n < 0 || n > MAX_AMOUNT) issue('current_value', 'Valor inválido');
    }
    if (v.quantity.trim()) {
      const n = parseDecimal(v.quantity);
      if (n === null || n < 0 || n > 999_999_999_999) issue('quantity', 'Cantidad inválida');
    }
    if (v.interest_rate_tna.trim()) {
      const n = parseDecimal(v.interest_rate_tna);
      if (n === null || n < 0 || n > 999.9999) issue('interest_rate_tna', 'TNA inválida (0 a 999,9999)');
    }
    if (v.auto_quote && !v.quantity.trim()) {
      issue('quantity', 'La cotización automática necesita la cantidad');
    }
    if (v.start_date && v.maturity_date && v.maturity_date < v.start_date) {
      issue('maturity_date', 'El vencimiento no puede ser anterior al inicio');
    }
    if (v.asset_type === 'fixed_term') {
      if (!v.start_date) issue('start_date', 'La fecha de inicio es requerida');
      if (!v.maturity_date) issue('maturity_date', 'El vencimiento es requerido');
      else if (v.start_date && v.maturity_date <= v.start_date) {
        issue('maturity_date', 'El vencimiento debe ser posterior al inicio');
      }
      if (!v.interest_rate_tna.trim()) issue('interest_rate_tna', 'La TNA es requerida');
      if (v.currency !== 'ARS' && v.currency !== 'USD') {
        issue('currency', 'El plazo fijo es en pesos o dólares');
      }
    }
  });

type FormData = z.infer<typeof schema>;

interface Props {
  investment: Investment | null;
  onClose: () => void;
  onSaved: () => void;
}

const inputCls =
  'w-full rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:border-brand-indigo focus:outline-none focus:ring-1 focus:ring-brand-indigo';
const labelCls = 'mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400';
const errorCls = 'mt-1 text-xs text-red-500';

function defaultValues(): FormData {
  return {
    asset_type: 'fixed_term',
    name: '',
    ticker: '',
    currency: 'ARS',
    quantity: '',
    invested_amount: '',
    current_value: '',
    interest_rate_tna: '',
    start_date: toLocalDateString(),
    maturity_date: '',
    institution: '',
    notes: '',
    notify_maturity: true,
    auto_quote: false,
  };
}

function toForm(i: Investment): FormData {
  const asText = (n: number | null) => (n === null ? '' : String(n).replace('.', ','));
  return {
    asset_type: i.asset_type,
    name: i.name,
    ticker: i.ticker ?? '',
    currency: i.currency,
    quantity: asText(i.quantity),
    invested_amount: asText(i.invested_amount),
    current_value: asText(i.current_value),
    interest_rate_tna: asText(i.interest_rate_tna),
    start_date: i.start_date ?? '',
    maturity_date: i.maturity_date ?? '',
    institution: i.institution ?? '',
    notes: i.notes ?? '',
    notify_maturity: i.notify_maturity,
    auto_quote: i.price_source === 'coingecko',
  };
}

function toInput(v: FormData): InvestmentInput {
  const type = v.asset_type;
  const hasMaturity = HAS_MATURITY.includes(type);
  const auto = v.auto_quote && type === 'crypto';
  return {
    asset_type: type,
    name: v.name.trim(),
    ticker: HAS_TICKER.includes(type) && v.ticker.trim() ? v.ticker.trim().toUpperCase() : null,
    currency: v.currency,
    quantity: HAS_QUANTITY.includes(type) ? parseDecimal(v.quantity) : null,
    invested_amount: parseDecimal(v.invested_amount) ?? 0,
    // Con cotización automática el valor sale de cantidad × precio.
    current_value: auto ? null : parseDecimal(v.current_value),
    interest_rate_tna: HAS_TNA.includes(type) ? parseDecimal(v.interest_rate_tna) : null,
    start_date: v.start_date || null,
    maturity_date: hasMaturity && v.maturity_date ? v.maturity_date : null,
    institution: v.institution.trim() || null,
    notes: v.notes.trim() || null,
    notify_maturity: v.notify_maturity,
    price_source: auto ? 'coingecko' : 'manual',
  };
}

export default function InvestmentModal({ investment, onClose, onSaved }: Props) {
  const [serverError, setServerError] = useState<string | null>(null);
  // Un plazo fijo se valúa solo; fijar el valor a mano es la excepción.
  const [manualValue, setManualValue] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormData, unknown, FormData>({
    resolver: zodResolver(schema),
    defaultValues: defaultValues(),
  });

  useEffect(() => {
    if (investment) {
      reset(toForm(investment));
      setManualValue(investment.current_value !== null);
    }
  }, [investment, reset]);

  const type = watch('asset_type');
  const currency = watch('currency');
  const invested = watch('invested_amount');
  const tna = watch('interest_rate_tna');
  const start = watch('start_date');
  const maturity = watch('maturity_date');
  const ticker = watch('ticker');
  const autoQuote = watch('auto_quote');

  // Cotización automática: solo cripto con ticker de la lista curada del server.
  const { data: cryptoAssets } = useCryptoAssets();
  const supportedTickers = (cryptoAssets ?? []).map((a) => a.ticker);
  const tickerSupported = supportedTickers.includes(ticker.trim().toUpperCase());
  const canAutoQuote = type === 'crypto' && tickerSupported;
  const autoOn = autoQuote && type === 'crypto';

  // Si el ticker o el tipo ya no admiten cotización automática, se apaga.
  useEffect(() => {
    if (autoQuote && cryptoAssets && !canAutoQuote) setValue('auto_quote', false);
  }, [autoQuote, cryptoAssets, canAutoQuote, setValue]);

  // La fecha de hoy que viene por defecto es la del plazo fijo: al pasar a otro
  // tipo se limpia (una "fecha de compra" inventada falsearía el rendimiento real).
  const defaultStart = useRef(start);
  const previousType = useRef(type);
  useEffect(() => {
    if (
      !investment &&
      previousType.current === 'fixed_term' &&
      type !== 'fixed_term' &&
      start === defaultStart.current
    ) {
      setValue('start_date', '');
    }
    previousType.current = type;
  }, [investment, type, start, setValue]);

  const isFixedTerm = type === 'fixed_term';
  const currencyOptions: InvestmentCurrency[] = isFixedTerm ? ['ARS', 'USD'] : ['ARS', 'USD', 'USDT', 'EUR'];

  // Al pasar a plazo fijo, una moneda que no admite vuelve a pesos.
  useEffect(() => {
    if (isFixedTerm && currency !== 'ARS' && currency !== 'USD') setValue('currency', 'ARS');
  }, [isFixedTerm, currency, setValue]);

  const preview = isFixedTerm
    ? fixedTermPreview(parseDecimal(invested), parseDecimal(tna), start, maturity)
    : null;
  const previewCurrency: InvestmentCurrency = currency === 'USD' ? 'USD' : 'ARS';

  async function onSubmit(values: FormData) {
    setServerError(null);
    const input = toInput(values);
    // Plazo fijo sin valor manual: se manda null para que el server lo devengue.
    if (isFixedTerm && !manualValue) input.current_value = null;
    try {
      await saveInvestment(investment, input);
      onSaved();
    } catch (err) {
      setServerError(apiErrorMessage(err, 'No se pudo guardar la inversión'));
    }
  }

  const showValueField = (!isFixedTerm || manualValue) && !autoOn;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 px-4 py-8 sm:py-12">
      <div className="w-full max-w-lg rounded-xl bg-white dark:bg-slate-800 shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-100 dark:border-slate-800 px-6 py-4">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">
            {investment ? 'Editar inversión' : 'Nueva inversión'}
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

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 px-6 py-4" noValidate>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="inv-type" className={labelCls}>Tipo</label>
              <select id="inv-type" {...register('asset_type')} className={inputCls}>
                {ASSET_TYPES.map((t) => (
                  <option key={t} value={t}>{ASSET_TYPE_LABELS[t]}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="inv-currency" className={labelCls}>Moneda</label>
              <select id="inv-currency" {...register('currency')} className={inputCls}>
                {currencyOptions.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
              {errors.currency && <p className={errorCls}>{errors.currency.message}</p>}
            </div>
          </div>

          <div>
            <label htmlFor="inv-name" className={labelCls}>Nombre</label>
            <input
              id="inv-name"
              {...register('name')}
              type="text"
              className={inputCls}
              placeholder={isFixedTerm ? 'Ej: Plazo fijo Galicia' : 'Ej: Apple CEDEAR'}
            />
            {errors.name && <p className={errorCls}>{errors.name.message}</p>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            {HAS_TICKER.includes(type) && (
              <div>
                <label htmlFor="inv-ticker" className={labelCls}>Ticker (opcional)</label>
                <input
                  id="inv-ticker"
                  {...register('ticker')}
                  type="text"
                  className={inputCls}
                  placeholder={type === 'crypto' ? 'BTC' : 'AAPL'}
                  list={type === 'crypto' ? 'inv-ticker-options' : undefined}
                  autoComplete="off"
                />
                {type === 'crypto' && (
                  <datalist id="inv-ticker-options">
                    {(cryptoAssets ?? []).map((a) => (
                      <option key={a.ticker} value={a.ticker}>{a.name}</option>
                    ))}
                  </datalist>
                )}
                {errors.ticker && <p className={errorCls}>{errors.ticker.message}</p>}
              </div>
            )}
            {HAS_QUANTITY.includes(type) && (
              <div>
                <label htmlFor="inv-quantity" className={labelCls}>
                  Cantidad{autoOn ? '' : ' (opcional)'}
                </label>
                <input
                  id="inv-quantity"
                  {...register('quantity')}
                  type="text"
                  inputMode="decimal"
                  className={inputCls}
                  placeholder="0,00012345"
                />
                {errors.quantity && <p className={errorCls}>{errors.quantity.message}</p>}
              </div>
            )}
          </div>

          {type === 'crypto' && (
            <div className="rounded-lg bg-gray-50 dark:bg-slate-700/40 px-3 py-2.5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p id="inv-auto-label" className="text-sm font-medium text-gray-700 dark:text-slate-200">
                    Cotización automática
                  </p>
                  <p className="mt-0.5 text-xs text-gray-500 dark:text-slate-400">
                    {canAutoQuote
                      ? 'El valor se calcula con la cantidad y el precio del mercado. Datos de CoinGecko.'
                      : ticker.trim()
                        ? 'No tenemos cotización automática para ese ticker: cargá el valor a mano.'
                        : 'Elegí un ticker de la lista (BTC, ETH, USDT…) para cotizarlo solo.'}
                  </p>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={autoOn}
                  aria-labelledby="inv-auto-label"
                  disabled={!canAutoQuote}
                  onClick={() => setValue('auto_quote', !autoQuote, { shouldValidate: true })}
                  className={`relative h-6 w-11 shrink-0 rounded-full transition-colors disabled:opacity-40 ${
                    autoOn ? 'bg-sky-500' : 'bg-gray-300 dark:bg-slate-600'
                  }`}
                >
                  <span
                    className={`absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${
                      autoOn ? 'translate-x-5' : ''
                    }`}
                  />
                </button>
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="inv-invested" className={labelCls}>Monto invertido</label>
              <input
                id="inv-invested"
                {...register('invested_amount')}
                type="text"
                inputMode="decimal"
                className={inputCls}
                placeholder="1000000,00"
              />
              {errors.invested_amount && <p className={errorCls}>{errors.invested_amount.message}</p>}
            </div>
            {showValueField && (
              <div>
                <label htmlFor="inv-value" className={labelCls}>Valor actual (opcional)</label>
                <input
                  id="inv-value"
                  {...register('current_value')}
                  type="text"
                  inputMode="decimal"
                  className={inputCls}
                  placeholder="Si no lo cargás, vale lo invertido"
                />
                {errors.current_value && <p className={errorCls}>{errors.current_value.message}</p>}
              </div>
            )}
          </div>

          {isFixedTerm && !manualValue && (
            <button
              type="button"
              onClick={() => setManualValue(true)}
              className="text-xs font-medium text-brand-indigo hover:underline"
            >
              Fijar el valor actual a mano
            </button>
          )}

          {HAS_TNA.includes(type) && (
            <div>
              <label htmlFor="inv-tna" className={labelCls}>
                TNA %{isFixedTerm ? '' : ' (opcional)'}
              </label>
              <input
                id="inv-tna"
                {...register('interest_rate_tna')}
                type="text"
                inputMode="decimal"
                className={inputCls}
                placeholder="30"
              />
              {errors.interest_rate_tna && <p className={errorCls}>{errors.interest_rate_tna.message}</p>}
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="inv-start" className={labelCls}>
                {isFixedTerm ? 'Fecha de inicio' : 'Fecha de compra (opcional)'}
              </label>
              <input id="inv-start" {...register('start_date')} type="date" className={inputCls} />
              {!isFixedTerm && (
                <p className="mt-1 text-xs text-gray-400 dark:text-slate-500">
                  Sirve para calcular el rendimiento contra la inflación.
                </p>
              )}
              {errors.start_date && <p className={errorCls}>{errors.start_date.message}</p>}
            </div>
            {HAS_MATURITY.includes(type) && (
              <div>
                <label htmlFor="inv-maturity" className={labelCls}>
                  Vencimiento{isFixedTerm ? '' : ' (opcional)'}
                </label>
                <input id="inv-maturity" {...register('maturity_date')} type="date" className={inputCls} />
                {errors.maturity_date && <p className={errorCls}>{errors.maturity_date.message}</p>}
              </div>
            )}
          </div>

          {isFixedTerm && (
            <div
              data-testid="fixed-term-preview"
              className="rounded-lg bg-sky-50 dark:bg-sky-500/10 px-4 py-3 text-sm"
            >
              {preview ? (
                <div className="space-y-1">
                  <div className="flex justify-between">
                    <span className="text-sky-800 dark:text-sky-300">Interés a cobrar ({preview.termDays} días)</span>
                    <span className="font-semibold text-sky-900 dark:text-sky-200">
                      {formatMoney(preview.interest, previewCurrency)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sky-800 dark:text-sky-300">Monto al vencimiento</span>
                    <span className="font-semibold text-sky-900 dark:text-sky-200">
                      {formatMoney(preview.amountAtMaturity, previewCurrency)}
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-sky-800 dark:text-sky-300">
                  Cargá monto, TNA y fechas para ver cuánto vas a cobrar.
                </p>
              )}
            </div>
          )}

          <div>
            <label htmlFor="inv-institution" className={labelCls}>Entidad / broker (opcional)</label>
            <input
              id="inv-institution"
              {...register('institution')}
              type="text"
              className={inputCls}
              placeholder="Ej: Banco Galicia, Balanz, Binance"
            />
          </div>

          <div>
            <label htmlFor="inv-notes" className={labelCls}>Notas (opcional)</label>
            <textarea id="inv-notes" {...register('notes')} rows={2} className={inputCls} />
            {errors.notes && <p className={errorCls}>{errors.notes.message}</p>}
          </div>

          {maturity && (
            <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-slate-300">
              <input type="checkbox" {...register('notify_maturity')} className="rounded" />
              Avisarme del vencimiento (la víspera y el día, desde las 9:00)
            </label>
          )}

          {serverError && (
            <p role="alert" className="rounded-lg bg-red-50 dark:bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-400">
              {serverError}
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
              {isSubmitting ? 'Guardando…' : investment ? 'Actualizar' : 'Crear'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
