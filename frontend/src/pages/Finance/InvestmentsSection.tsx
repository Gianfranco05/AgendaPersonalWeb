import { useState, useRef } from 'react';
import { Plus, Pencil, Trash2, Archive, ArchiveRestore, LineChart, RefreshCw, History } from 'lucide-react';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import { useMarketFx } from '../../hooks/useMarket';
import {
  useInvestments,
  useNetWorth,
  removeInvestment,
  setInvestmentStatus,
  saveInvestmentSettings,
  useRenewals,
  type InvestmentStatusFilter,
} from '../../hooks/useInvestments';
import type { Investment, InvestmentCurrency, PortfolioRealReturn } from '../../types';
import {
  ASSET_TYPES,
  ASSET_TYPE_LABELS,
  formatMoney,
  formatPct,
  formatQuantity,
  maturityLabel,
  maturityTone,
  monthLabel,
  realReturnReasonText,
  relativeTime,
} from '../../utils/investments';
import { formatShortDate } from '../../utils/recurring';
import InvestmentModal from './InvestmentModal';
import RenewFixedTermModal from './RenewFixedTermModal';
import NetWorthCard from './NetWorthCard';
import FxRatesEditor from './FxRatesEditor';
import { useOpenParam } from '../../hooks/useOpenParam';

const TONE_CLASSES = {
  urgent: 'bg-rose-50 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300',
  soon: 'bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300',
  calm: 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-300',
};

function groupSubtotal(items: Investment[]): string {
  const byCurrency = new Map<InvestmentCurrency, number>();
  for (const i of items) {
    byCurrency.set(i.currency, (byCurrency.get(i.currency) ?? 0) + i.effective_value);
  }
  return [...byCurrency.entries()].map(([c, v]) => formatMoney(v, c)).join(' · ');
}

const COINGECKO_URL = 'https://www.coingecko.com';

/** Chip "Real ±x %" con el detalle nominal / inflación y la marca "estimado". */
function RealReturnInfo({ investment: i }: { investment: Investment }) {
  const rr = i.real_return;
  if (!rr) {
    const reason = realReturnReasonText(i.real_return_unavailable_reason);
    return reason ? (
      <p className="mt-2 text-xs text-gray-400 dark:text-slate-500" data-testid="real-return-reason">
        {reason}
      </p>
    ) : null;
  }
  const positive = rr.real_pct >= 0;
  const period = monthLabel(rr.period_end.slice(0, 7));
  const projection = rr.projected_at_maturity;
  const hint = rr.estimated
    ? `El IPC de ${rr.estimated_months.map(monthLabel).join(' y ')} todavía no está publicado: lo estimamos con el último dato.`
    : null;
  return (
    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs" data-testid="real-return">
      <span
        title={`Nominal ${formatPct(rr.nominal_pct, false)} · Inflación ${formatPct(rr.inflation_pct, false)} (${period})`}
        className={`rounded-full px-2 py-0.5 font-medium ${
          positive
            ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300'
            : 'bg-rose-50 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300'
        }`}
      >
        Real {formatPct(rr.real_pct)}
      </span>
      <span className="text-gray-400 dark:text-slate-500">
        nominal {formatPct(rr.nominal_pct, false)} · inflación {formatPct(rr.inflation_pct, false)}
      </span>
      {rr.estimated && (
        <span
          title={hint ?? undefined}
          className="rounded-full bg-amber-50 dark:bg-amber-500/15 px-2 py-0.5 font-medium text-amber-700 dark:text-amber-300"
        >
          estimado
        </span>
      )}
      {projection && (
        <span className="text-gray-500 dark:text-slate-400">
          Al vencimiento: real ≈ {formatPct(projection.real_pct)}
        </span>
      )}
    </div>
  );
}

/** Cotización automática de cripto: antigüedad y atribución obligatoria. */
function QuoteInfo({ investment: i }: { investment: Investment }) {
  if (i.price_source !== 'coingecko') return null;
  return (
    <p className="mt-2 text-xs text-gray-500 dark:text-slate-400" data-testid="auto-quote">
      {i.last_price_at ? (
        <span className={i.quote_stale ? 'text-amber-600 dark:text-amber-400' : ''}>
          Cotización automática · {relativeTime(i.last_price_at)}
          {i.quote_stale ? ' (desactualizada)' : ''}
        </span>
      ) : (
        <span>Esperando cotización…</span>
      )}
      {' · '}
      <a
        href={COINGECKO_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="text-brand-indigo hover:underline"
      >
        Datos de CoinGecko
      </a>
    </p>
  );
}

function RealReturnSummary({ data }: { data: PortfolioRealReturn }) {
  const wins = data.real_pct >= 0;
  return (
    <div
      data-testid="real-return-summary"
      className="rounded-xl bg-white dark:bg-slate-800 px-5 py-3 text-sm text-gray-700 dark:text-slate-200 shadow-sm"
    >
      Tus inversiones en pesos le {wins ? 'ganan' : 'pierden'}{' '}
      <span className={`font-semibold ${wins ? 'text-emerald-500' : 'text-rose-500'}`}>
        {formatPct(Math.abs(data.real_pct), false)}
      </span>{' '}
      a la inflación ({data.included_count} {data.included_count === 1 ? 'activo' : 'activos'}
      {data.estimated ? ', estimado' : ''}).
      <span className="ml-1 text-xs text-gray-400 dark:text-slate-500">
        Nominal {formatPct(data.nominal_pct, false)} · inflación {formatPct(data.inflation_pct, false)}
      </span>
    </div>
  );
}

/** Cadena de renovaciones de un plazo fijo, de la más vieja a la más nueva. */
function RenewalHistory({ investment: i }: { investment: Investment }) {
  const { data, isLoading, error } = useRenewals(i.id);
  if (isLoading && !data) return <p className="mt-3 text-xs text-gray-400 dark:text-slate-500">Cargando…</p>;
  if (error && !data) {
    return (
      <p role="alert" className="mt-3 text-xs text-red-500">
        No se pudo cargar el historial.
      </p>
    );
  }
  if (!data) return null;
  const currency = data.currency as InvestmentCurrency;
  return (
    <div className="mt-3 rounded-lg bg-gray-50 dark:bg-slate-900/40 p-3 text-xs" data-testid="renewal-history">
      <ol className="space-y-2">
        {data.items.map((t, index) => (
          <li key={t.id} className={t.id === i.id ? 'font-medium text-gray-800 dark:text-slate-100' : 'text-gray-600 dark:text-slate-300'}>
            <span className="mr-1 text-gray-400 dark:text-slate-500">{index + 1}.</span>
            {t.start_date ? formatShortDate(t.start_date) : '—'} → {t.maturity_date ? formatShortDate(t.maturity_date) : '—'}
            {' · '}
            {formatMoney(t.invested_amount, currency)}
            {t.interest_rate_tna !== null && ` · TNA ${t.interest_rate_tna.toLocaleString('es-AR', { maximumFractionDigits: 4 })}%`}
            {t.interest !== null && (
              <span className="text-emerald-600 dark:text-emerald-400">
                {' '}
                · interés {t.status === 'closed' ? '' : 'previsto '}
                {formatMoney(t.interest, currency)}
              </span>
            )}
          </li>
        ))}
      </ol>
      <p className="mt-2 text-gray-500 dark:text-slate-400">
        Interés acumulado cobrado: <span className="font-medium">{formatMoney(data.accumulated_interest, currency)}</span>
      </p>
    </div>
  );
}

function InvestmentCard({
  investment: i,
  onEdit,
  onToggleStatus,
  onDelete,
  onRenew,
}: {
  investment: Investment;
  onEdit: () => void;
  onToggleStatus: () => void;
  onDelete: () => void;
  onRenew: () => void;
}) {
  const [showHistory, setShowHistory] = useState(false);
  const hasRenewals = !!(i.renewed_from_id || i.renewed_to_id);
  const chip = maturityLabel(i.days_to_maturity);
  const closed = i.status === 'closed';
  const gainPositive = i.gain >= 0;

  return (
    <div
      className={`rounded-xl bg-white dark:bg-slate-800 p-4 shadow-sm ${closed ? 'opacity-70' : ''}`}
      data-testid="investment-card"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h4 className="truncate font-semibold text-gray-800 dark:text-slate-100">
            {i.name}
            {i.ticker && (
              <span className="ml-2 rounded bg-gray-100 dark:bg-slate-700 px-1.5 py-0.5 text-xs font-medium text-gray-500 dark:text-slate-300">
                {i.ticker}
              </span>
            )}
          </h4>
          <p className="text-xs text-gray-500 dark:text-slate-400">
            {[i.institution, i.quantity !== null ? `${formatQuantity(i.quantity)} u.` : null, i.currency]
              .filter(Boolean)
              .join(' · ')}
          </p>
        </div>
        <div className="flex shrink-0 gap-1">
          <button
            onClick={onEdit}
            aria-label={`Editar ${i.name}`}
            className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-brand-indigo"
          >
            <Pencil size={14} />
          </button>
          <button
            onClick={onToggleStatus}
            aria-label={closed ? `Reabrir ${i.name}` : `Cerrar ${i.name}`}
            title={closed ? 'Reabrir' : 'Cerrar (deja de sumar)'}
            className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-brand-indigo"
          >
            {closed ? <ArchiveRestore size={14} /> : <Archive size={14} />}
          </button>
          <button
            onClick={onDelete}
            aria-label={`Eliminar ${i.name}`}
            className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 hover:bg-rose-50 hover:text-rose-500"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      <div className="mt-3 flex items-end justify-between gap-3">
        <div>
          <p className="text-xs text-gray-400 dark:text-slate-500">
            Invertido {formatMoney(i.invested_amount, i.currency)}
          </p>
          <p className="text-lg font-bold text-gray-800 dark:text-slate-100">
            {formatMoney(i.effective_value, i.currency)}
          </p>
          {i.value_source === 'fixed_term_accrued' && (
            <p className="text-xs text-gray-400 dark:text-slate-500">con interés devengado a hoy</p>
          )}
        </div>
        <div className="text-right">
          <p className={`text-sm font-semibold ${gainPositive ? 'text-emerald-500' : 'text-rose-500'}`}>
            {gainPositive ? '+' : ''}
            {formatMoney(i.gain, i.currency)}
            {i.gain_pct !== null && (
              <span className="ml-1 text-xs">
                ({gainPositive ? '+' : ''}
                {i.gain_pct.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%)
              </span>
            )}
          </p>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
        {i.interest_rate_tna !== null && (
          <span className="rounded-full bg-sky-50 dark:bg-sky-500/15 px-2 py-0.5 font-medium text-sky-700 dark:text-sky-300">
            TNA {i.interest_rate_tna.toLocaleString('es-AR', { maximumFractionDigits: 4 })}%
          </span>
        )}
        {i.fixed_term && (
          <span className="text-gray-500 dark:text-slate-400">
            Al vencimiento {formatMoney(i.fixed_term.amount_at_maturity, i.currency)}
          </span>
        )}
        {chip && !closed && (
          <span className={`rounded-full px-2 py-0.5 font-medium ${TONE_CLASSES[maturityTone(i.days_to_maturity)]}`}>
            {chip}
          </span>
        )}
        {closed && (
          <span className="rounded-full bg-gray-100 dark:bg-slate-700 px-2 py-0.5 font-medium text-gray-500 dark:text-slate-300">
            cerrada
          </span>
        )}
      </div>
      <QuoteInfo investment={i} />
      <RealReturnInfo investment={i} />
      {(i.can_renew || hasRenewals) && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {i.can_renew && (
            <button
              onClick={onRenew}
              className="flex items-center gap-1.5 rounded-lg bg-brand-charcoal px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-brand-charcoal-hover"
            >
              <RefreshCw size={12} />
              Renovar
            </button>
          )}
          {hasRenewals && (
            <button
              onClick={() => setShowHistory((s) => !s)}
              aria-expanded={showHistory}
              className="flex items-center gap-1.5 rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700/50"
            >
              <History size={12} />
              Historial de renovaciones
            </button>
          )}
        </div>
      )}
      {showHistory && hasRenewals && <RenewalHistory investment={i} />}
    </div>
  );
}

export default function InvestmentsSection() {
  const [filter, setFilter] = useState<InvestmentStatusFilter>('active');
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<Investment | null>(null);
  const [renewing, setRenewing] = useState<Investment | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const { data: investments, isLoading, error } = useInvestments(filter);
  const { data: netWorth } = useNetWorth();
  const { data: market } = useMarketFx();

  // Desde el buscador: la inversión puede estar entre las activas o entre las
  // cerradas. Si no está en el filtro actual se prueba el otro antes de rendirse.
  const openTried = useRef<{ id: string; filters: Set<InvestmentStatusFilter> } | null>(null);
  useOpenParam({
    ready: !isLoading,
    onOpen: ({ id }) => {
      const found = investments?.find((i) => i.id === id);
      if (found) {
        openTried.current = null;
        handleEdit(found);
        return true;
      }
      if (openTried.current?.id !== id) openTried.current = { id, filters: new Set() };
      openTried.current.filters.add(filter);
      const other: InvestmentStatusFilter = filter === 'active' ? 'closed' : 'active';
      if (!openTried.current.filters.has(other)) {
        setFilter(other);
        return 'wait';
      }
      openTried.current = null;
      return false;
    },
  });

  function handleNew() {
    setEditing(null);
    setShowModal(true);
  }

  function handleEdit(i: Investment) {
    setEditing(i);
    setShowModal(true);
  }

  async function run(action: () => Promise<void>) {
    setActionError(null);
    try {
      await action();
    } catch {
      setActionError('No se pudo completar la acción. Probá de nuevo.');
    }
  }

  async function handleDelete(i: Investment) {
    if (!window.confirm(`¿Eliminar "${i.name}"? Esta acción no se puede deshacer.`)) return;
    await run(() => removeInvestment(i.id));
  }

  const includeInBalance = netWorth?.include_investments_in_balance ?? false;
  const hasEur = (netWorth?.investments.by_currency ?? []).some((c) => c.currency === 'EUR');

  const groups = ASSET_TYPES.map((type) => ({
    type,
    items: (investments ?? []).filter((i) => i.asset_type === type),
  })).filter((g) => g.items.length > 0);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {netWorth ? <NetWorthCard data={netWorth} /> : <LoadingSkeleton type="card" />}

        <div className="space-y-4 rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
          <div>
            <h3 className="mb-2 text-sm font-semibold text-gray-800 dark:text-slate-100">Cotización</h3>
            {netWorth ? (
              <FxRatesEditor
                key={`${netWorth.rates.usd_source}-${netWorth.rates.eur_source}-${netWorth.rates.usd_ars}-${netWorth.rates.eur_ars}-${netWorth.rates.updated_at}`}
                rates={netWorth.rates}
                market={market}
                showEur={hasEur}
              />
            ) : (
              <LoadingSkeleton type="card" />
            )}
          </div>

          <div className="border-t border-gray-100 dark:border-slate-700 pt-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p id="include-label" className="text-sm font-semibold text-gray-800 dark:text-slate-100">
                  Sumar inversiones al balance
                </p>
                <p className="mt-0.5 text-xs text-gray-500 dark:text-slate-400">
                  En el Dashboard muestra el balance junto con tus inversiones, en colores distintos. El
                  balance de tus transacciones no cambia.
                </p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={includeInBalance}
                aria-labelledby="include-label"
                disabled={!netWorth}
                onClick={() =>
                  run(() => saveInvestmentSettings({ include_investments_in_balance: !includeInBalance }))
                }
                className={`relative h-6 w-11 shrink-0 rounded-full transition-colors disabled:opacity-50 ${
                  includeInBalance ? 'bg-sky-500' : 'bg-gray-300 dark:bg-slate-600'
                }`}
              >
                <span
                  className={`absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${
                    includeInBalance ? 'translate-x-5' : ''
                  }`}
                />
              </button>
            </div>
          </div>
        </div>
      </div>

      {netWorth?.investments.real_return_ars && (
        <RealReturnSummary data={netWorth.investments.real_return_ars} />
      )}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex rounded-lg border border-gray-200 dark:border-slate-700 p-0.5">
          {(
            [
              ['active', 'Activas'],
              ['closed', 'Cerradas'],
            ] as const
          ).map(([value, label]) => (
            <button
              key={value}
              onClick={() => setFilter(value)}
              className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
                filter === value
                  ? 'bg-brand-charcoal text-white'
                  : 'text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-100'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <button
          onClick={handleNew}
          className="flex items-center gap-2 rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-charcoal-hover"
        >
          <Plus size={16} />
          Nueva inversión
        </button>
      </div>

      {actionError && (
        <p role="alert" className="rounded-lg bg-red-50 dark:bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-400">
          {actionError}
        </p>
      )}

      {isLoading && !investments ? (
        <LoadingSkeleton type="card" />
      ) : error && !investments ? (
        <p role="alert" className="rounded-xl bg-white dark:bg-slate-800 p-6 text-sm text-red-500 shadow-sm">
          No se pudieron cargar las inversiones.
        </p>
      ) : groups.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl bg-white dark:bg-slate-800 p-12 shadow-sm">
          <LineChart size={48} className="text-gray-300 dark:text-slate-600" />
          <p className="text-sm text-gray-500 dark:text-slate-400">
            {filter === 'active' ? 'Todavía no cargaste inversiones' : 'No hay inversiones cerradas'}
          </p>
        </div>
      ) : (
        groups.map(({ type, items }) => (
          <section key={type} className="space-y-3" aria-label={ASSET_TYPE_LABELS[type]}>
            <div className="flex items-baseline justify-between gap-3">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-200">
                {ASSET_TYPE_LABELS[type]}
              </h3>
              <span className="text-xs text-gray-500 dark:text-slate-400">{groupSubtotal(items)}</span>
            </div>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {items.map((i) => (
                <InvestmentCard
                  key={i.id}
                  investment={i}
                  onEdit={() => handleEdit(i)}
                  onToggleStatus={() =>
                    run(() => setInvestmentStatus(i.id, i.status === 'active' ? 'closed' : 'active'))
                  }
                  onDelete={() => handleDelete(i)}
                  onRenew={() => setRenewing(i)}
                />
              ))}
            </div>
          </section>
        ))
      )}

      {renewing && (
        <RenewFixedTermModal
          investment={renewing}
          onClose={() => setRenewing(null)}
          onDone={() => setRenewing(null)}
        />
      )}

      {showModal && (
        <InvestmentModal
          investment={editing}
          onClose={() => setShowModal(false)}
          onSaved={() => setShowModal(false)}
        />
      )}
    </div>
  );
}
