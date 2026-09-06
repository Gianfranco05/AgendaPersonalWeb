import { useState } from 'react';
import { Smartphone, Monitor, Loader2, X } from 'lucide-react';
import { useSessions, revokeSession } from '../../hooks/useSessions';
import type { Session } from '../../types';

function formatDate(value: string | null): string {
  if (!value) return '—';
  return new Date(value).toLocaleString('es-AR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/** El User-Agent completo es ilegible en una lista; se queda con lo útil. */
function shortDevice(info: string | null): { label: string; mobile: boolean } {
  if (!info) return { label: 'Dispositivo desconocido', mobile: false };
  if (/okhttp|android/i.test(info)) return { label: 'Android', mobile: true };
  if (/iphone|ios/i.test(info)) return { label: 'iPhone', mobile: true };
  if (/chrome/i.test(info)) return { label: 'Chrome', mobile: false };
  if (/firefox/i.test(info)) return { label: 'Firefox', mobile: false };
  if (/safari/i.test(info)) return { label: 'Safari', mobile: false };
  return { label: info.slice(0, 40), mobile: false };
}

function SessionRow({ session }: { session: Session }) {
  const [revoking, setRevoking] = useState(false);
  const { label, mobile } = shortDevice(session.device_info);

  async function handleRevoke() {
    if (revoking) return;
    if (!window.confirm(`¿Cerrar la sesión de ${label}?`)) return;
    setRevoking(true);
    try {
      await revokeSession(session.id);
    } finally {
      setRevoking(false);
    }
  }

  return (
    <div className="flex items-center justify-between rounded-lg border border-gray-200 dark:border-slate-700 px-4 py-3">
      <div className="flex items-center gap-3">
        {mobile ? (
          <Smartphone size={18} className="text-gray-400 dark:text-slate-500" />
        ) : (
          <Monitor size={18} className="text-gray-400 dark:text-slate-500" />
        )}
        <div>
          <p className="text-sm text-gray-700 dark:text-slate-200">{label}</p>
          <p className="text-xs text-gray-500 dark:text-slate-400">
            Último uso: {formatDate(session.last_used_at ?? session.created_at)}
          </p>
        </div>
      </div>
      <button
        type="button"
        onClick={handleRevoke}
        disabled={revoking}
        className="flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium text-rose-500 transition-colors hover:bg-rose-50 dark:hover:bg-rose-900/20 disabled:opacity-50"
      >
        {revoking ? <Loader2 size={14} className="animate-spin" /> : <X size={14} />}
        Cerrar sesión
      </button>
    </div>
  );
}

export default function SessionsSection() {
  const { data: sessions, isLoading } = useSessions();

  return (
    <div className="space-y-4 rounded-xl bg-white dark:bg-slate-800 p-6 shadow-sm">
      <div className="flex items-center gap-2">
        <Smartphone size={18} className="text-brand-indigo" />
        <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-200">Sesiones</h3>
      </div>
      <p className="text-sm text-gray-500 dark:text-slate-400">
        Dispositivos con sesión abierta en tu cuenta. Cerrá las que no reconozcas.
      </p>

      {isLoading ? (
        <p className="text-sm text-gray-400 dark:text-slate-500">Cargando…</p>
      ) : !sessions || sessions.length === 0 ? (
        <p className="text-sm text-gray-400 dark:text-slate-500">No hay sesiones activas</p>
      ) : (
        <div className="space-y-2">
          {sessions.map((s) => (
            <SessionRow key={s.id} session={s} />
          ))}
        </div>
      )}
    </div>
  );
}
