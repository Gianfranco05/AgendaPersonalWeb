import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  GraduationCap,
  BookOpen,
  Film,
  Briefcase,
  Plane,
  Car,
  KanbanSquare,
  CheckCircle2,
  CircleAlert,
  X,
  Package,
  ArrowLeft,
} from 'lucide-react';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import { useStore, startCheckout, revalidateAfterPurchase } from '../../hooks/useStore';
import type { StoreItem } from '../../types';

const ICONS: Record<string, typeof Package> = {
  study: GraduationCap,
  library: BookOpen,
  media: Film,
  work: Briefcase,
  travel: Plane,
  vehicle: Car,
  projects: KanbanSquare,
};

function formatPrice(item: StoreItem): string {
  if (item.amount === null) return '';
  const amount = item.amount / 100;
  return amount % 1 === 0 ? `$${amount}` : `$${amount.toFixed(2)}`;
}

function StoreTile({
  item,
  busy,
  onBuy,
}: {
  item: StoreItem;
  busy: boolean;
  onBuy: () => void;
}) {
  const Icon = ICONS[item.key] ?? Package;
  return (
    <div className="flex items-center gap-3 rounded-xl bg-white dark:bg-slate-800 p-4 shadow-sm">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-indigo/10 text-brand-indigo">
        <Icon className="h-5 w-5" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-gray-800 dark:text-slate-100">{item.label}</p>
        <p className="truncate text-xs text-gray-500 dark:text-slate-400">{item.description}</p>
      </div>
      {item.owned ? (
        <span className="flex shrink-0 items-center gap-1 text-xs font-medium text-emerald-600 dark:text-emerald-400">
          <CheckCircle2 className="h-4 w-4" />
          Ya comprado
        </span>
      ) : item.amount !== null ? (
        <button
          onClick={onBuy}
          disabled={busy}
          className="shrink-0 rounded-lg bg-brand-indigo px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-brand-indigo-hover disabled:cursor-not-allowed disabled:opacity-60"
        >
          {busy ? 'Redirigiendo…' : `Comprar ${formatPrice(item)}`}
        </button>
      ) : (
        <span className="shrink-0 text-xs text-gray-400 dark:text-slate-500">Próximamente</span>
      )}
    </div>
  );
}

export default function StorePage() {
  const { data: store, isLoading } = useStore();
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const checkoutStatus = searchParams.get('checkout');

  // Al volver de un checkout exitoso, tienda y selector de módulos quedan
  // desincronizados (el usuario ahora es dueño de una plantilla más) sin esto.
  useEffect(() => {
    if (checkoutStatus === 'ok') {
      void revalidateAfterPurchase();
    }
    // Solo al llegar con ?checkout=ok, no en cada cambio de searchParams.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [checkoutStatus]);

  function dismissBanner() {
    const next = new URLSearchParams(searchParams);
    next.delete('checkout');
    setSearchParams(next, { replace: true });
  }

  async function handleBuy(item: StoreItem) {
    setBusyKey(item.key);
    try {
      await startCheckout(item.key);
      // No hace falta limpiar busyKey en éxito: la página navega afuera
      // (Stripe Checkout) antes de que el usuario vea el botón de nuevo.
    } catch {
      setBusyKey(null);
    }
  }

  const items = store?.items ?? [];
  const available = items.filter((i) => !i.owned);
  const owned = items.filter((i) => i.owned);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-800 dark:text-slate-100">Tienda</h2>
          <p className="text-sm text-gray-500 dark:text-slate-400">
            Cada plantilla se compra una sola vez y queda en tu cuenta para siempre.
          </p>
        </div>
        <Link
          to="/modules"
          className="flex items-center gap-2 rounded-lg border border-gray-200 dark:border-slate-700 px-4 py-2 text-sm font-medium text-gray-600 dark:text-slate-300 transition-colors hover:bg-gray-50 dark:hover:bg-slate-700"
        >
          <ArrowLeft size={16} />
          Módulos
        </Link>
      </div>

      {checkoutStatus === 'ok' && (
        <div className="flex items-center justify-between gap-3 rounded-xl bg-emerald-50 dark:bg-emerald-900/30 p-4 text-emerald-800 dark:text-emerald-300">
          <div className="flex items-center gap-2 text-sm">
            <CheckCircle2 size={18} />
            ¡Compra confirmada! Ya podés activar la plantilla desde Módulos.
          </div>
          <button onClick={dismissBanner} aria-label="Cerrar aviso">
            <X size={16} />
          </button>
        </div>
      )}
      {checkoutStatus === 'cancel' && (
        <div className="flex items-center justify-between gap-3 rounded-xl bg-amber-50 dark:bg-amber-900/30 p-4 text-amber-800 dark:text-amber-300">
          <div className="flex items-center gap-2 text-sm">
            <CircleAlert size={18} />
            El pago se canceló. No se te cobró nada.
          </div>
          <button onClick={dismissBanner} aria-label="Cerrar aviso">
            <X size={16} />
          </button>
        </div>
      )}

      {isLoading ? (
        <div className="space-y-3">
          <LoadingSkeleton type="card" />
          <LoadingSkeleton type="card" />
        </div>
      ) : (
        <>
          {store && !store.billing_enabled && (
            <div className="rounded-xl bg-gray-100 dark:bg-slate-800 p-4 text-sm text-gray-500 dark:text-slate-400">
              Los pagos no están configurados en este entorno.
            </div>
          )}

          {available.length > 0 && (
            <section className="space-y-3">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-slate-400">
                Disponibles
              </h3>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {available.map((item) => (
                  <StoreTile
                    key={item.key}
                    item={item}
                    busy={busyKey === item.key}
                    onBuy={() => handleBuy(item)}
                  />
                ))}
              </div>
            </section>
          )}

          {owned.length > 0 && (
            <section className="space-y-3">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-slate-400">
                Tus plantillas
              </h3>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {owned.map((item) => (
                  <StoreTile key={item.key} item={item} busy={false} onBuy={() => {}} />
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
