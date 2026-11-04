import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import * as authApi from '../../api/authApi';
import AuthCard, { authButtonCls, authInputCls, apiErrorMessage } from './AuthCard';

// Mismo mínimo que el registro y que valida la API.
const MIN_PASSWORD = 6;

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') ?? '';
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (submitting) return;
    if (password.length < MIN_PASSWORD) {
      setError(`La contraseña debe tener al menos ${MIN_PASSWORD} caracteres`);
      return;
    }
    if (password !== confirm) {
      setError('Las contraseñas no coinciden');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await authApi.resetPassword(token, password);
      setDone(true);
    } catch (err) {
      setError(apiErrorMessage(err, 'No pudimos cambiar la contraseña. Probá de nuevo.'));
    } finally {
      setSubmitting(false);
    }
  }

  if (!token) {
    return (
      <AuthCard title="Link inválido">
        <p className="text-sm text-gray-600 dark:text-slate-300">
          Este link no tiene el código de recuperación.{' '}
          <Link to="/olvide-password" className="font-medium text-brand-indigo hover:underline">
            Pedí uno nuevo
          </Link>
          .
        </p>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Elegir contraseña nueva">
      {done ? (
        <div className="space-y-4">
          <p className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-700">
            Listo, cambiaste tu contraseña. Por seguridad cerramos todas tus sesiones abiertas.
          </p>
          <Link to="/login" className={`${authButtonCls} block text-center`}>
            Iniciar sesión
          </Link>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">
              {error}{' '}
              <Link to="/olvide-password" className="font-medium underline">
                Pedir un link nuevo
              </Link>
            </div>
          )}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-slate-200">
              Contraseña nueva
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              autoFocus
              className={authInputCls}
              placeholder={`Mínimo ${MIN_PASSWORD} caracteres`}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-slate-200">
              Repetí la contraseña
            </label>
            <input
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              autoComplete="new-password"
              className={authInputCls}
            />
          </div>
          <button type="submit" disabled={submitting || !password} className={authButtonCls}>
            {submitting ? 'Guardando…' : 'Cambiar contraseña'}
          </button>
        </form>
      )}
    </AuthCard>
  );
}
