import { Link } from 'react-router-dom';
import { Lock } from 'lucide-react';

interface Props {
  /** Nombre de la plantilla, ej. "Estudio" */
  moduleName: string;
}

/**
 * Se muestra en vez del contenido normal cuando el backend devuelve 402
 * (plantilla de pago no comprada). El gate real de "bloqueada/comprada" vive
 * en la página Módulos; esto es solo la red de contención para quien llega
 * directo por URL sin haber comprado la plantilla.
 */
export default function ModuleLockedNotice({ moduleName }: Props) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl bg-white dark:bg-slate-800 p-12 text-center shadow-sm">
      <Lock size={48} className="text-gray-300 dark:text-slate-600" />
      <p className="text-sm font-medium text-gray-800 dark:text-slate-100">
        No tenés la plantilla de {moduleName}
      </p>
      <p className="max-w-sm text-sm text-gray-500 dark:text-slate-400">
        Esta es una plantilla de pago único. Comprala para empezar a usarla.
      </p>
      <Link
        to="/store"
        className="mt-2 flex items-center gap-2 rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-charcoal-hover"
      >
        Ver en la tienda
      </Link>
    </div>
  );
}

/** true si el error de axios/SWR es un 402 (Payment Required). */
export function isPaymentRequiredError(error: unknown): boolean {
  if (!error || typeof error !== 'object') return false;
  const response = (error as { response?: { status?: number } }).response;
  return response?.status === 402;
}
