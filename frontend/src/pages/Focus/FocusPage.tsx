import { useEffect, useState } from 'react';
import { Timer, Play, Square, Trash2, Brain } from 'lucide-react';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import ModuleLockedNotice, { isPaymentRequiredError } from '../../components/ModuleLockedNotice';
import {
  useFocusSummary,
  useFocusSessions,
  startFocus,
  stopFocus,
  removeFocusSession,
} from '../../hooks/useFocus';

/** Segundos transcurridos desde un ISO string, nunca negativo. */
function elapsedSince(startedAt: string): number {
  const started = new Date(startedAt).getTime();
  if (Number.isNaN(started)) return 0;
  return Math.max(0, Math.floor((Date.now() - started) / 1000));
}

function formatTimer(totalSeconds: number): string {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  const pad = (n: number) => n.toString().padStart(2, '0');
  return h > 0 ? `${pad(h)}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`;
}

function formatDuration(totalSeconds: number): string {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function formatWhen(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleString('es-AR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
}

export default function FocusPage() {
  const { data: summary, isLoading: summaryLoading, error: summaryError } = useFocusSummary();
  const { data: sessions, isLoading: sessionsLoading } = useFocusSessions();
  const [label, setLabel] = useState('');
  const [busy, setBusy] = useState(false);
  const [elapsed, setElapsed] = useState(0);

  const active = summary?.active ?? null;

  // El cronómetro corre en el cliente: el server solo guarda started_at, así
  // que no hace falta pegarle cada segundo para ver el tiempo avanzar.
  const activeStartedAt = active?.started_at ?? null;
  useEffect(() => {
    if (!activeStartedAt) {
      setElapsed(0);
      return;
    }
    setElapsed(elapsedSince(activeStartedAt));
    const id = setInterval(() => setElapsed(elapsedSince(activeStartedAt)), 1000);
    return () => clearInterval(id);
  }, [activeStartedAt]);

  if (isPaymentRequiredError(summaryError)) {
    // Focus es gratis: si igual llega un 402 acá, algo está mal configurado
    // server-side, pero se maneja con gracia de todos modos.
    return <ModuleLockedNotice moduleName="Focus" />;
  }

  async function handleStart() {
    setBusy(true);
    try {
      await startFocus(label.trim() || undefined);
      setLabel('');
    } finally {
      setBusy(false);
    }
  }

  async function handleStop() {
    setBusy(true);
    try {
      await stopFocus();
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('¿Seguro que querés borrar esta sesión?')) return;
    await removeFocusSession(id);
  }

  const todayTotal = (summary?.today_seconds ?? 0) + elapsed;
  const weekTotal = (summary?.week_seconds ?? 0) + elapsed;
  const closedSessions = (sessions ?? []).filter((s) => s.duration_seconds !== null);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-800 dark:text-slate-100">Focus</h2>
      </div>

      {summaryLoading && !summary ? (
        <LoadingSkeleton type="widget" />
      ) : (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl bg-white dark:bg-slate-800 p-8 shadow-sm">
          <span className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-slate-400">
            {active ? 'En curso' : 'Sin sesión activa'}
          </span>
          <span className="font-mono text-5xl font-bold text-gray-800 dark:text-slate-100">
            {formatTimer(elapsed)}
          </span>
          {active?.label && <p className="text-sm text-gray-500 dark:text-slate-400">{active.label}</p>}

          {active ? (
            <button
              onClick={handleStop}
              disabled={busy}
              className="mt-2 flex items-center gap-2 rounded-lg bg-rose-500 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-rose-600 disabled:opacity-50"
            >
              <Square size={16} />
              Terminar sesión
            </button>
          ) : (
            <div className="mt-2 flex w-full max-w-sm flex-col gap-3 sm:flex-row">
              <input
                type="text"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleStart();
                }}
                placeholder="¿En qué vas a trabajar? (opcional)"
                className="flex-1 rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-2 text-sm focus:border-brand-focus focus:outline-none focus:ring-1 focus:ring-brand-focus"
              />
              <button
                onClick={handleStart}
                disabled={busy}
                className="flex items-center justify-center gap-2 rounded-lg bg-brand-focus px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90 disabled:opacity-50"
              >
                <Play size={16} />
                Empezar
              </button>
            </div>
          )}
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-xl bg-white dark:bg-slate-800 p-5 text-center shadow-sm">
          <div className="flex items-center justify-center gap-2 text-sm text-gray-500 dark:text-slate-400">
            <Timer size={16} className="text-brand-focus" />
            Hoy
          </div>
          <p className="mt-1 text-2xl font-bold text-brand-focus">{formatDuration(todayTotal)}</p>
        </div>
        <div className="rounded-xl bg-white dark:bg-slate-800 p-5 text-center shadow-sm">
          <div className="flex items-center justify-center gap-2 text-sm text-gray-500 dark:text-slate-400">
            <Brain size={16} className="text-gray-400" />
            Esta semana
          </div>
          <p className="mt-1 text-2xl font-bold text-gray-800 dark:text-slate-100">{formatDuration(weekTotal)}</p>
        </div>
      </div>

      <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-slate-400">
          Sesiones recientes
        </h3>
        {sessionsLoading ? (
          <LoadingSkeleton type="widget" />
        ) : closedSessions.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-slate-400">Todavía no cerraste ninguna sesión.</p>
        ) : (
          <ul className="space-y-2">
            {closedSessions.map((s) => (
              <li key={s.id} className="flex items-center justify-between gap-2 rounded-lg px-1 py-1.5">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm text-gray-800 dark:text-slate-100">{s.label || 'Sesión de foco'}</p>
                  <p className="truncate text-xs text-gray-500 dark:text-slate-400">{formatWhen(s.started_at)}</p>
                </div>
                <span className="shrink-0 text-sm font-semibold text-gray-800 dark:text-slate-100">
                  {formatDuration(s.duration_seconds ?? 0)}
                </span>
                <button
                  onClick={() => handleDelete(s.id)}
                  className="shrink-0 rounded-lg p-1.5 text-gray-400 dark:text-slate-500 transition-colors hover:bg-rose-50 hover:text-rose-500"
                  title="Eliminar"
                >
                  <Trash2 size={13} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
