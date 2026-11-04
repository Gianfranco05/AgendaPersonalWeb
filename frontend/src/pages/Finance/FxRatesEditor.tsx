import { useState } from 'react';
import { AlertTriangle, Pencil } from 'lucide-react';
import { saveInvestmentSettings } from '../../hooks/useInvestments';
import { apiErrorMessage } from '../../utils/apiError';
import {
  EUR_SOURCE_OPTIONS,
  USD_SOURCE_OPTIONS,
  ageLabel,
  daysSince,
  formatMoney,
  fxKindLabel,
  parseDecimal,
  providerLabel,
  relativeTime,
} from '../../utils/investments';
import type { FxQuote, MarketFx, NetWorthRates } from '../../types';

const STALE_DAYS = 7;
const MAX_RATE = 9_999_999.9999;

interface Props {
  rates: NetWorthRates;
  /** Cotizaciones automáticas guardadas en el server (null mientras cargan). */
  market: MarketFx | null | undefined;
  /** El euro solo se muestra cuando hay activos en EUR. */
  showEur: boolean;
}

const inputCls =
  'w-full rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-sm focus:border-brand-indigo focus:outline-none focus:ring-1 focus:ring-brand-indigo';

function toText(n: number | null): string {
  return n === null ? '' : String(n).replace('.', ',');
}

// '' borra la cotización; cualquier otra cosa tiene que ser un número válido.
function parseRate(text: string): { ok: true; value: number | null } | { ok: false } {
  if (!text.trim()) return { ok: true, value: null };
  const n = parseDecimal(text);
  if (n === null || n <= 0 || n > MAX_RATE) return { ok: false };
  return { ok: true, value: n };
}

interface BlockProps {
  currency: 'USD' | 'EUR';
  /** Lo que pidió el usuario. Sin dato (server viejo) se trata como manual. */
  source: string;
  options: readonly string[];
  effective: string | null | undefined;
  rate: number | null;
  asOf: string | null | undefined;
  provider: string | null | undefined;
  stale: boolean | undefined;
  quotes: FxQuote[];
  degraded: boolean;
  /** `manual_fallback`: se usa la manual porque aún no hay datos del mercado. */
  manualUpdatedAt: string | null;
}

/** Selector de fuente + cotizaciones (o campo manual) de una moneda. */
function CurrencyRate({
  currency,
  source,
  options,
  effective,
  rate,
  asOf,
  provider,
  stale,
  quotes,
  degraded,
  manualUpdatedAt,
}: BlockProps) {
  const usd = currency === 'USD';
  const name = usd ? 'Dólar' : 'Euro';
  const field = usd ? 'fx_usd_ars' : 'fx_eur_ars';
  const sourceField = usd ? 'fx_usd_source' : 'fx_eur_source';
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const manualMode = source === 'manual';
  const manualRate = effective === 'manual' ? rate : null;
  const age = manualUpdatedAt ? daysSince(manualUpdatedAt) : null;
  const manualStale = age !== null && age > STALE_DAYS;

  async function choose(next: string) {
    if (next === source) return;
    setError(null);
    try {
      await saveInvestmentSettings({ [sourceField]: next });
    } catch (err) {
      setError(apiErrorMessage(err, 'No se pudo cambiar la cotización'));
    }
  }

  function startEditing() {
    setText(toText(manualRate));
    setError(null);
    setEditing(true);
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    const parsed = parseRate(text);
    if (!parsed.ok) {
      setError(`Ingresá una cotización mayor a 0 (por ejemplo ${usd ? '1450,50' : '1600,00'}).`);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      // Editar el valor a mano también pasa la fuente a "manual".
      await saveInvestmentSettings({ [field]: parsed.value, [sourceField]: 'manual' });
      setEditing(false);
    } catch (err) {
      setError(apiErrorMessage(err, 'No se pudo guardar la cotización'));
    } finally {
      setSaving(false);
    }
  }

  const selector = (
    <div
      role="radiogroup"
      aria-label={`Fuente del ${name.toLowerCase()}`}
      className="inline-flex rounded-lg border border-gray-200 dark:border-slate-700 p-0.5"
    >
      {options.map((opt) => (
        <button
          key={opt}
          type="button"
          role="radio"
          aria-checked={source === opt}
          onClick={() => choose(opt)}
          className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
            source === opt
              ? 'bg-brand-charcoal text-white'
              : 'text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-100'
          }`}
        >
          {fxKindLabel(opt)}
        </button>
      ))}
    </div>
  );

  const errorLine = error && (
    <p role="alert" className="text-xs text-red-500">
      {error}
    </p>
  );

  if (manualMode && editing) {
    return (
      <div className="space-y-2">
        {selector}
        <form onSubmit={handleSave} className="space-y-3" data-testid={usd ? 'fx-form' : 'fx-form-eur'}>
          <div>
            <label
              htmlFor={`fx-${currency.toLowerCase()}`}
              className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400"
            >
              {usd ? 'Dólar (ARS por US$ 1)' : 'Euro (ARS por € 1)'}
            </label>
            <input
              id={`fx-${currency.toLowerCase()}`}
              value={text}
              onChange={(e) => setText(e.target.value)}
              inputMode="decimal"
              className={inputCls}
              placeholder={usd ? '1450,50' : '1600,00'}
              autoFocus
            />
          </div>
          <p className="text-xs text-gray-400 dark:text-slate-500">
            Dejalo vacío para borrarla.{usd ? ' USDT se toma 1 a 1 con el dólar.' : ''}
          </p>
          {errorLine}
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setEditing(false)}
              className="rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700/50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-brand-charcoal px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-charcoal-hover disabled:opacity-50"
            >
              {saving ? 'Guardando…' : 'Guardar'}
            </button>
          </div>
        </form>
      </div>
    );
  }

  if (manualMode) {
    return (
      <div className="space-y-2">
        {selector}
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-0.5 text-sm text-gray-700 dark:text-slate-200">
            <p>
              {name}:{' '}
              {manualRate === null ? (
                <span className="text-gray-400 dark:text-slate-500">sin cargar</span>
              ) : (
                <span className="font-semibold">{formatMoney(manualRate)}</span>
              )}
            </p>
            {age !== null && (
              <p
                className={`text-xs ${manualStale ? 'text-amber-600 dark:text-amber-400' : 'text-gray-400 dark:text-slate-500'}`}
              >
                Actualizada {ageLabel(age)}
                {manualStale ? ' · conviene actualizarla' : ''}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={startEditing}
            aria-label={usd ? 'Editar cotización' : 'Editar cotización del euro'}
            className="flex shrink-0 items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-brand-indigo hover:bg-gray-100 dark:hover:bg-slate-700"
          >
            <Pencil size={12} />
            {manualRate === null ? 'Cargar' : 'Editar'}
          </button>
        </div>
        {errorLine}
      </div>
    );
  }

  // Fuente automática.
  const fallback = effective === 'manual_fallback';
  const shown = quotes.filter((q) => options.includes(q.kind));
  return (
    <div className="space-y-2">
      {selector}
      {shown.length > 0 && (
        <ul className="divide-y divide-gray-100 dark:divide-slate-700 rounded-lg border border-gray-100 dark:border-slate-700">
          {shown.map((q) => (
            <li
              key={q.kind}
              data-testid={`fx-quote-${currency.toLowerCase()}-${q.kind}`}
              className={`flex items-baseline justify-between gap-3 px-3 py-1.5 text-sm ${
                q.kind === source ? 'bg-sky-50/60 dark:bg-sky-500/10' : ''
              }`}
            >
              <span className="text-gray-600 dark:text-slate-300">{q.label}</span>
              <span className="text-right">
                <span className="font-semibold text-gray-800 dark:text-slate-100">{formatMoney(q.sell)}</span>
                {q.buy !== null && (
                  <span className="ml-2 text-xs text-gray-400 dark:text-slate-500">
                    compra {formatMoney(q.buy)}
                  </span>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
      <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500 dark:text-slate-400">
        {fallback ? (
          <span>
            Usamos tu cotización manual ({rate !== null ? formatMoney(rate) : 'sin cargar'}) porque todavía no
            hay datos del mercado.
          </span>
        ) : rate === null ? (
          <span>Todavía no hay datos del mercado.</span>
        ) : (
          <span>
            {name} {fxKindLabel(effective)} {formatMoney(rate)}
            {provider ? ` · ${providerLabel(provider)}` : ''}
            {asOf ? ` · ${relativeTime(asOf)}` : ''}
          </span>
        )}
        {stale && (
          <span className="rounded-full bg-amber-50 dark:bg-amber-500/15 px-2 py-0.5 font-medium text-amber-700 dark:text-amber-300">
            desactualizada
          </span>
        )}
      </div>
      {degraded && !fallback && rate !== null && (
        <p className="flex items-start gap-1.5 text-xs text-amber-700 dark:text-amber-300">
          <AlertTriangle size={12} className="mt-0.5 shrink-0" />
          No pudimos actualizar la cotización; usamos la última conocida.
        </p>
      )}
      {errorLine}
    </div>
  );
}

/** Cotización del dólar (y del euro si hace falta): elegís de dónde sale o la cargás vos. */
export default function FxRatesEditor({ rates, market, showEur }: Props) {
  const degraded = market?.degraded ?? false;
  return (
    <div className="space-y-5" data-testid="fx-card">
      <CurrencyRate
        currency="USD"
        source={rates.usd_source ?? 'manual'}
        options={USD_SOURCE_OPTIONS}
        effective={rates.usd_effective_source ?? (rates.usd_ars === null ? null : 'manual')}
        rate={rates.usd_ars}
        asOf={rates.usd_as_of ?? rates.updated_at}
        provider={rates.usd_provider}
        stale={rates.usd_stale}
        quotes={market?.usd ?? []}
        degraded={degraded}
        manualUpdatedAt={rates.updated_at}
      />
      {showEur && (
        <CurrencyRate
          currency="EUR"
          source={rates.eur_source ?? 'manual'}
          options={EUR_SOURCE_OPTIONS}
          effective={rates.eur_effective_source ?? (rates.eur_ars === null ? null : 'manual')}
          rate={rates.eur_ars}
          asOf={rates.eur_as_of ?? rates.updated_at}
          provider={rates.eur_provider}
          stale={rates.eur_stale}
          quotes={market?.eur ?? []}
          degraded={degraded}
          manualUpdatedAt={rates.updated_at}
        />
      )}
    </div>
  );
}
