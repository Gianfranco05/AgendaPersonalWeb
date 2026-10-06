import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import * as authApi from '../../api/authApi';
import AuthCard, { authButtonCls, apiErrorMessage } from './AuthCard';

type State = { status: 'working' } | { status: 'ok' } | { status: 'error'; message: string };

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') ?? '';
  const [state, setState] = useState<State>(
    token ? { status: 'working' } : { status: 'error', message: 'Este link no tiene el código de verificación.' },
  );
  // El token es de un solo uso: en desarrollo StrictMode corre el efecto dos
  // veces y la segunda llamada fallaba aunque la primera hubiera verificado.
  const ranRef = useRef(false);

  useEffect(() => {
    if (!token || ranRef.current) return;
    ranRef.current = true;
    authApi
      .verifyEmail(token)
      .then(() => setState({ status: 'ok' }))
      .catch((err) =>
        setState({ status: 'error', message: apiErrorMessage(err, 'No pudimos verificar tu email.') }),
      );
  }, [token]);

  return (
    <AuthCard title="Verificación de email">
      {state.status === 'working' && (
        <div className="flex items-center gap-3 text-sm text-gray-600 dark:text-slate-300">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-brand-indigo border-t-transparent" />
          Verificando tu email…
        </div>
      )}
      {state.status === 'ok' && (
        <div className="space-y-4">
          <p className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-700">¡Listo! Confirmamos tu email.</p>
          <Link to="/" className={`${authButtonCls} block text-center`}>
            Ir a la app
          </Link>
        </div>
      )}
      {state.status === 'error' && (
        <div className="space-y-4">
          <p className="rounded-lg bg-red-50 p-3 text-sm text-red-600">{state.message}</p>
          <p className="text-sm text-gray-500 dark:text-slate-400">
            Iniciá sesión y pedí un link nuevo si venció.
          </p>
          <Link to="/login" className="block text-center text-sm font-medium text-brand-indigo hover:underline">
            Iniciar sesión
          </Link>
        </div>
      )}
    </AuthCard>
  );
}
