import { AlertTriangle, Landmark } from 'lucide-react';
import type { NetWorth } from '../../types';
import { describeFxRate, formatMoney } from '../../utils/investments';

// Efectivo e inversiones van en colores propios y distintos del verde de
// ingresos y el rojo de egresos de las transacciones.
export const CASH_COLOR = 'bg-emerald-500';
export const INVESTMENTS_COLOR = 'bg-sky-500';

function Amount({ value, currency }: { value: number | null; currency: 'ARS' | 'USD' }) {
  return value === null ? (
    <span className="text-gray-400 dark:text-slate-500">—</span>
  ) : (
    <>{formatMoney(value, currency)}</>
  );
}

/** Patrimonio: disponible, inversiones y total, cada uno en ARS y en USD. */
export default function NetWorthCard({ data }: { data: NetWorth }) {
  const { investments } = data;
  const canTotal = data.net_worth_ars !== null;

  // Sin cotización para valuar las inversiones se muestra solo el efectivo.
  const headline = canTotal ? data.net_worth_ars! : data.cash_balance_ars;
  const headlineLabel = !canTotal
    ? 'Disponible'
    : data.include_investments_in_balance
      ? 'Balance + inversiones'
      : 'Patrimonio';

  const cash = Math.max(data.cash_balance_ars, 0);
  const invested = Math.max(investments.total_ars ?? 0, 0);
  const sum = cash + invested;
  const cashPct = sum > 0 ? (cash / sum) * 100 : 0;

  const missingArs = !canTotal;
  const missingUsdOnly = canTotal && data.net_worth_usd === null;
  const missingRatesText = [
    data.missing_rates.includes('USD') && 'del dólar',
    data.missing_rates.includes('EUR') && 'del euro',
  ]
    .filter(Boolean)
    .join(' y ');

  // Qué dólar se está usando para convertir (solo cuando el server lo informa).
  const { rates } = data;
  const fxLine =
    rates.usd_source !== undefined
      ? describeFxRate(
          'USD',
          rates.usd_ars,
          rates.usd_effective_source,
          rates.usd_provider,
          rates.usd_as_of ?? rates.updated_at,
        )
      : null;

  return (
    <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm" data-testid="net-worth-card">
      <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
        <Landmark size={16} className="text-sky-500" />
        {headlineLabel}
      </div>
      <p className="mt-1 text-3xl font-bold text-gray-800 dark:text-slate-100">
        {formatMoney(headline, 'ARS')}
      </p>
      {canTotal && data.net_worth_usd !== null && (
        <p className="text-sm text-gray-500 dark:text-slate-400">≈ {formatMoney(data.net_worth_usd, 'USD')}</p>
      )}

      {canTotal && sum > 0 && (
        <div className="mt-4">
          <div className="flex h-2.5 overflow-hidden rounded-full bg-gray-100 dark:bg-slate-700" role="img" aria-label="Efectivo e inversiones">
            <div className={CASH_COLOR} style={{ width: `${cashPct}%` }} />
            <div className={INVESTMENTS_COLOR} style={{ width: `${100 - cashPct}%` }} />
          </div>
          <div className="mt-2 flex gap-4 text-xs text-gray-500 dark:text-slate-400">
            <span className="flex items-center gap-1.5">
              <span className={`h-2 w-2 rounded-full ${CASH_COLOR}`} /> Efectivo
            </span>
            <span className="flex items-center gap-1.5">
              <span className={`h-2 w-2 rounded-full ${INVESTMENTS_COLOR}`} /> Inversiones
            </span>
          </div>
        </div>
      )}

      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-gray-400 dark:text-slate-500">
              <th className="pb-1 text-left font-medium" />
              <th className="pb-1 text-right font-medium">ARS</th>
              <th className="pb-1 text-right font-medium">USD</th>
            </tr>
          </thead>
          <tbody className="text-gray-700 dark:text-slate-200">
            <tr>
              <td className="py-1 text-gray-500 dark:text-slate-400">Disponible</td>
              <td className="py-1 text-right"><Amount value={data.cash_balance_ars} currency="ARS" /></td>
              <td className="py-1 text-right"><Amount value={data.cash_balance_usd} currency="USD" /></td>
            </tr>
            <tr>
              <td className="py-1 text-gray-500 dark:text-slate-400">Inversiones</td>
              <td className="py-1 text-right"><Amount value={investments.total_ars} currency="ARS" /></td>
              <td className="py-1 text-right"><Amount value={investments.total_usd} currency="USD" /></td>
            </tr>
            <tr className="border-t border-gray-100 dark:border-slate-700 font-semibold">
              <td className="pt-2">Total</td>
              <td className="pt-2 text-right"><Amount value={data.net_worth_ars} currency="ARS" /></td>
              <td className="pt-2 text-right"><Amount value={data.net_worth_usd} currency="USD" /></td>
            </tr>
          </tbody>
        </table>
      </div>

      {fxLine && (
        <p className="mt-3 text-xs text-gray-400 dark:text-slate-500" data-testid="fx-used">
          {fxLine}
          {rates.usd_stale && (
            <span className="ml-2 rounded-full bg-amber-50 dark:bg-amber-500/15 px-2 py-0.5 font-medium text-amber-700 dark:text-amber-300">
              desactualizada
            </span>
          )}
        </p>
      )}

      {investments.by_currency.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500 dark:text-slate-400">
          <span>Por moneda:</span>
          {investments.by_currency.map((c) => (
            <span key={c.currency}>
              {formatMoney(c.current_value, c.currency)}
            </span>
          ))}
        </div>
      )}

      {(missingArs || missingUsdOnly) && (
        <div
          role="status"
          className="mt-4 flex items-start gap-2 rounded-lg bg-amber-50 dark:bg-amber-500/10 px-3 py-2 text-xs text-amber-800 dark:text-amber-300"
        >
          <AlertTriangle size={14} className="mt-0.5 shrink-0" />
          <span>
            {missingArs
              ? `Cargá la cotización ${missingRatesText} para ver el total.`
              : 'Cargá la cotización del dólar para ver los montos en USD.'}
          </span>
        </div>
      )}
    </div>
  );
}
