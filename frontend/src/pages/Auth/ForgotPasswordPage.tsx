import { useState } from 'react';
import { Link } from 'react-router-dom';
import * as authApi from '../../api/authApi';
import AuthCard, { authButtonCls, authInputCls, apiErrorMessage } from './AuthCard';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (submitting || !email.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await authApi.forgotPassword(email.trim());
      setSent(true);
    } catch (err) {
      setError(apiErrorMessage(err, 'No pudimos enviar el mail. Probá de nuevo.'));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthCard
      title="Recuperar contraseña"
      subtitle="Ingresá tu email y te mandamos un link para elegir una contraseña nueva."
    >
      {sent ? (
        <div className="space-y-4">
          <p className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-700">
            Si el email está registrado, en unos minutos te llega un mail con el link. Revisá también la
            carpeta de spam.
          </p>
          <Link to="/login" className="block text-center text-sm font-medium text-brand-indigo hover:underline">
            Volver a iniciar sesión
          </Link>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-slate-200">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              autoFocus
              required
              className={authInputCls}
              placeholder="tu@email.com"
            />
          </div>
          <button type="submit" disabled={submitting || !email.trim()} className={authButtonCls}>
            {submitting ? 'Enviando…' : 'Enviar link'}
          </button>
          <Link to="/login" className="block text-center text-sm text-gray-500 hover:underline dark:text-slate-400">
            Volver
          </Link>
        </form>
      )}
    </AuthCard>
  );
}
