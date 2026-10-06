import type { ReactNode } from 'react';
import PublicFooter from '../../components/PublicFooter';

interface AuthCardProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
}

/** Tarjeta centrada de las pantallas cortas de cuenta (recuperar contraseña,
 *  verificar email): sin sesión y sin el panel de marca del login. */
export default function AuthCard({ title, subtitle, children }: AuthCardProps) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 px-4 py-10 dark:bg-slate-900">
      <div className="w-full max-w-md rounded-xl bg-white p-8 shadow-sm dark:bg-slate-800">
        <h1 className="text-xl font-bold text-gray-800 dark:text-slate-100">{title}</h1>
        {subtitle && <p className="mt-2 text-sm text-gray-500 dark:text-slate-400">{subtitle}</p>}
        <div className="mt-5">{children}</div>
      </div>
      <PublicFooter className="mt-6" />
    </div>
  );
}

export const authInputCls =
  'w-full rounded-lg border border-brand-border px-3 py-2.5 text-sm transition-colors focus:border-brand-indigo focus:outline-none focus:ring-1 focus:ring-brand-indigo';

export const authButtonCls =
  'w-full rounded-lg bg-brand-charcoal py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-charcoal-hover disabled:cursor-not-allowed disabled:opacity-60';

/** Mensaje de error de una respuesta de la API (detail string o lista de 422). */
export function apiErrorMessage(err: unknown, fallback: string): string {
  const data = (err as { response?: { data?: { detail?: unknown } } })?.response?.data;
  const detail = data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && typeof detail[0]?.msg === 'string') return detail[0].msg;
  return fallback;
}
