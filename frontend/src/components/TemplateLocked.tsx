import { Lock } from 'lucide-react';
import { Link } from 'react-router-dom';

interface Props {
  title: string;
}

/**
 * Estado que se muestra cuando el backend devuelve 402 en una plantilla de
 * pago único (require_module) porque el usuario todavía no la compró.
 */
export default function TemplateLocked({ title }: Props) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl bg-white dark:bg-slate-800 p-12 text-center shadow-sm">
      <div className="rounded-full bg-gray-100 dark:bg-slate-700 p-4">
        <Lock size={28} className="text-gray-400 dark:text-slate-500" />
      </div>
      <h2 className="text-lg font-semibold text-gray-800 dark:text-slate-100">{title}</h2>
      <p className="text-sm text-gray-500 dark:text-slate-400">No tenés esta plantilla.</p>
      <Link
        to="/store"
        className="mt-2 rounded-lg bg-brand-indigo px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90"
      >
        Ver en la tienda
      </Link>
    </div>
  );
}

/** Helper para detectar el 402 sin acoplar cada página al shape de axios. */
export function isPaymentRequired(error: unknown): boolean {
  return (
    typeof error === 'object' &&
    error !== null &&
    'response' in error &&
    (error as { response?: { status?: number } }).response?.status === 402
  );
}
