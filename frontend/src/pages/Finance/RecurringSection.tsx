import { useMemo, useState } from 'react';
import { Pause, Pencil, Play, Plus, Repeat, ListChecks, Trash2 } from 'lucide-react';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import {
  removeRecurring,
  setRecurringPaused,
  skipPending,
  usePendingOccurrences,
  useRecurring,
  useUpcomingRecurring,
} from '../../hooks/useRecurring';
import type { InvestmentCurrency, Occurrence, Recurring, RecurringState, Upcoming } from '../../types';
import { apiErrorMessage } from '../../utils/apiError';
import { formatMoney } from '../../utils/investments';
import { formatShortDate } from '../../utils/recurring';
import ConfirmOccurrenceModal from './ConfirmOccurrenceModal';
import RecurringModal from './RecurringModal';

const STATE_CHIP: Record<RecurringState, { label: string; cls: string }> = {
  active: {
    label: 'Activa',
    cls: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300',
  },
  paused: {
    label: 'Pausada',
    cls: 'bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300',
  },
  finished: {
    label: 'Finalizada',
    cls: 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-300',
  },
};

const asCurrency = (c: string | null | undefined) => (c ?? 'ARS') as InvestmentCurrency;

function totalsLabel(upcoming: Upcoming | undefined): string {
  if (!upcoming || upcoming.totals.length === 0) return 'Sin movimientos con monto fijo';
  const income = upcoming.totals.filter((t) => t.type === 'income');
  const expense = upcoming.totals.filter((t) => t.type === 'expense');
  const join = (items: typeof income) => items.map((t) => formatMoney(t.total, asCurrency(t.currency))).join(' + ');
  return [income.length ? `+${join(income)}` : null, expense.length ? `−${join(expense)}` : null]
    .filter(Boolean)
    .join(' / ');
}

interface Props {
  /** Abre la pestaña Transacciones filtrada por esta recurrencia. */
  onViewMovements?: (recurrence: Recurring) => void;
}

export default function RecurringSection({ onViewMovements }: Props) {
  const { data: recurring, isLoading, error } = useRecurring('all');
  const { data: pending } = usePendingOccurrences();
  const { data: upcoming } = useUpcomingRecurring(30);

  const [editing, setEditing] = useState<Recurring | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [confirming, setConfirming] = useState<Occurrence | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const items = useMemo(() => recurring ?? [], [recurring]);

  async function run(action: () => Promise<void>) {
    setActionError(null);
    try {
      await action();
    } catch (err) {
      setActionError(apiErrorMessage(err, 'No se pudo completar la acción. Probá de nuevo.'));
    }
  }

  function handleNew() {
    setEditing(null);
    setShowModal(true);
  }

  function handleEdit(r: Recurring) {
    setEditing(r);
    setShowModal(true);
  }

  async function handleDelete(r: Recurring) {
    if (
      !window.confirm(
        `¿Eliminar "${r.name}"? Las transacciones ya registradas se conservan; solo dejan de generarse nuevas.`,
      )
    )
      return;
    await run(() => removeRecurring(r.id));
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-gray-500 dark:text-slate-400">
          Sueldo, alquiler, suscripciones, servicios: se registran solos el día que corresponde.
        </p>
        <button
          onClick={handleNew}
          className="flex shrink-0 items-center gap-2 rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-charcoal-hover"
        >
          <Plus size={16} />
          Nueva recurrente
        </button>
      </div>

      {actionError && (
        <p role="alert" className="rounded-lg bg-red-50 dark:bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-400">
          {actionError}
        </p>
      )}

      {pending && pending.length > 0 && (
        <section
          aria-label="Para confirmar"
          data-testid="pending-card"
          className="rounded-xl border border-amber-200 dark:border-amber-500/30 bg-amber-50/60 dark:bg-amber-500/10 p-4"
        >
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-amber-800 dark:text-amber-200">
            <ListChecks size={16} />
            Para confirmar ({pending.length})
          </h3>
          <ul className="space-y-2">
            {pending.map((o) => (
              <li
                key={o.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-white dark:bg-slate-800 px-3 py-2"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-gray-800 dark:text-slate-100">{o.name}</p>
                  <p className="text-xs text-gray-500 dark:text-slate-400">
                    {formatShortDate(o.occurrence_date)} ·{' '}
                    {o.suggested_amount !== null
                      ? `sugerido ${formatMoney(o.suggested_amount, asCurrency(o.currency))}`
                      : 'sin monto estimado'}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setConfirming(o)}
                    className="rounded-lg bg-brand-charcoal px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-charcoal-hover"
                  >
                    Confirmar
                  </button>
                  <button
                    onClick={() => run(() => skipPending(o.id))}
                    className="rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700/50"
                  >
                    Saltear
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section aria-label="Próximos 30 días" className="rounded-xl bg-white dark:bg-slate-800 p-4 shadow-sm">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h3 className="text-sm font-semibold text-gray-800 dark:text-slate-100">Próximos 30 días</h3>
          <span className="text-sm font-medium text-gray-600 dark:text-slate-300" data-testid="upcoming-totals">
            {totalsLabel(upcoming)}
          </span>
        </div>
        {upcoming && upcoming.items.length > 0 ? (
          <ul className="mt-3 space-y-1 text-sm">
            {upcoming.items.slice(0, 8).map((u) => (
              <li key={`${u.recurrence_id}-${u.date}`} className="flex justify-between gap-3">
                <span className="text-gray-600 dark:text-slate-300">
                  {formatShortDate(u.date)} · {u.name}
                </span>
                <span
                  className={`shrink-0 font-medium ${u.type === 'income' ? 'text-emerald-500' : 'text-rose-500'}`}
                >
                  {u.amount === null
                    ? 'Monto variable'
                    : `${u.type === 'income' ? '+' : '−'}${formatMoney(u.amount, asCurrency(u.currency))}`}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-xs text-gray-400 dark:text-slate-500">No hay movimientos programados.</p>
        )}
      </section>

      {isLoading && !recurring ? (
        <LoadingSkeleton type="card" />
      ) : error && !recurring ? (
        <p role="alert" className="rounded-xl bg-white dark:bg-slate-800 p-6 text-sm text-red-500 shadow-sm">
          No se pudieron cargar los movimientos recurrentes.
        </p>
      ) : items.length === 0 ? (
        <div
          data-testid="recurring-empty"
          className="flex flex-col items-center justify-center gap-3 rounded-xl bg-white dark:bg-slate-800 p-12 text-center shadow-sm"
        >
          <Repeat size={48} className="text-gray-300 dark:text-slate-600" />
          <p className="text-sm font-medium text-gray-600 dark:text-slate-300">
            Todavía no tenés movimientos recurrentes
          </p>
          <p className="max-w-sm text-xs text-gray-500 dark:text-slate-400">
            Por ejemplo: tu sueldo el día 5, el alquiler el día 10, Netflix todos los meses o la luz cada dos
            meses (con confirmación del monto).
          </p>
        </div>
      ) : (
        <ul className="space-y-3">
          {items.map((r) => {
            const chip = STATE_CHIP[r.state];
            return (
              <li
                key={r.id}
                data-testid="recurring-item"
                className={`rounded-xl bg-white dark:bg-slate-800 p-4 shadow-sm ${r.state !== 'active' ? 'opacity-80' : ''}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h4 className="truncate font-semibold text-gray-800 dark:text-slate-100">
                      {r.name}
                      <span className={`ml-2 rounded-full px-2 py-0.5 text-xs font-medium ${chip.cls}`}>
                        {chip.label}
                      </span>
                    </h4>
                    <p className="text-xs text-gray-500 dark:text-slate-400">{r.rule_label}</p>
                  </div>
                  <p
                    className={`shrink-0 text-lg font-bold ${r.type === 'income' ? 'text-emerald-500' : 'text-rose-500'}`}
                  >
                    {r.amount === null
                      ? 'Monto variable'
                      : `${r.type === 'income' ? '+' : '−'}${formatMoney(r.amount, asCurrency(r.currency))}`}
                  </p>
                </div>
                <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-gray-500 dark:text-slate-400">
                  <span>
                    {r.next_occurrence_date && r.state === 'active'
                      ? `Próxima: ${formatShortDate(r.next_occurrence_date)}`
                      : r.state === 'paused'
                        ? 'Pausada: no genera movimientos'
                        : 'Terminó'}
                    {r.requires_confirmation && ' · pide confirmación'}
                    {r.pending_count > 0 && ` · ${r.pending_count} para confirmar`}
                  </span>
                  <div className="flex gap-1">
                    {onViewMovements && (
                      <button
                        onClick={() => onViewMovements(r)}
                        className="rounded-lg px-2 py-1 font-medium text-brand-indigo hover:bg-gray-100 dark:hover:bg-slate-700"
                      >
                        Ver movimientos
                      </button>
                    )}
                    <button
                      onClick={() => handleEdit(r)}
                      aria-label={`Editar ${r.name}`}
                      className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-brand-indigo"
                    >
                      <Pencil size={14} />
                    </button>
                    {r.state !== 'finished' && (
                      <button
                        onClick={() => run(() => setRecurringPaused(r.id, r.status === 'active'))}
                        aria-label={r.status === 'active' ? `Pausar ${r.name}` : `Reanudar ${r.name}`}
                        title={r.status === 'active' ? 'Pausar' : 'Reanudar'}
                        className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-brand-indigo"
                      >
                        {r.status === 'active' ? <Pause size={14} /> : <Play size={14} />}
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(r)}
                      aria-label={`Eliminar ${r.name}`}
                      className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 hover:bg-rose-50 hover:text-rose-500"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {showModal && (
        <RecurringModal
          recurring={editing}
          onClose={() => setShowModal(false)}
          onSaved={() => setShowModal(false)}
        />
      )}
      {confirming && (
        <ConfirmOccurrenceModal
          occurrence={confirming}
          onClose={() => setConfirming(null)}
          onDone={() => setConfirming(null)}
        />
      )}
    </div>
  );
}
