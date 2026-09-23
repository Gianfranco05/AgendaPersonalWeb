import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';

/**
 * Gate obligatorio: se muestra cuando `user.terms_accepted_version` no
 * coincide con `user.current_terms_version` (cuenta nueva creada por Google,
 * que no pasa por el checkbox del registro normal, o versión de términos que
 * subió mientras el usuario ya tenía sesión). Ver el redirect en ProtectedRoute.
 */
export default function AcceptTermsPage() {
  const navigate = useNavigate();
  const { acceptTerms, logout } = useAuthStore();
  const [checked, setChecked] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAccept() {
    setIsSubmitting(true);
    setError(null);
    try {
      await acceptTerms();
      navigate('/', { replace: true });
    } catch (err: unknown) {
      const data = (err as any)?.response?.data;
      setError(data?.detail ?? 'No pudimos registrar tu aceptación. Probá de nuevo.');
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleLogout() {
    await logout();
    navigate('/login', { replace: true });
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-10 dark:bg-slate-900">
      <div className="w-full max-w-md rounded-xl bg-white p-8 shadow-sm dark:bg-slate-800">
        <h1 className="text-xl font-bold text-gray-800 dark:text-slate-100">
          Actualizamos nuestros Términos
        </h1>
        <p className="mt-2 text-sm text-gray-500 dark:text-slate-400">
          Antes de seguir usando Can_cen, necesitamos que confirmes que leíste y
          aceptás los Términos y Condiciones y la Política de Privacidad vigentes.
        </p>

        <p className="mt-4 text-sm text-gray-600 dark:text-slate-300">
          Podés leer el texto completo en{' '}
          <Link to="/terms" target="_blank" rel="noopener noreferrer" className="text-brand-indigo hover:underline">
            Términos y Condiciones
          </Link>{' '}
          y{' '}
          <Link to="/privacy" target="_blank" rel="noopener noreferrer" className="text-brand-indigo hover:underline">
            Política de Privacidad
          </Link>
          .
        </p>

        {error && (
          <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>
        )}

        <label className="mt-5 flex items-start gap-2 text-sm text-gray-700 dark:text-slate-200">
          <input
            type="checkbox"
            checked={checked}
            onChange={(e) => setChecked(e.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-brand-border text-brand-indigo focus:ring-brand-indigo"
          />
          <span>Leí y acepto los Términos y Condiciones y la Política de Privacidad.</span>
        </label>

        <button
          type="button"
          onClick={handleAccept}
          disabled={!checked || isSubmitting}
          className="mt-5 w-full rounded-lg bg-brand-charcoal py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-charcoal-hover disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting ? 'Guardando…' : 'Aceptar y continuar'}
        </button>

        <button
          type="button"
          onClick={handleLogout}
          className="mt-3 w-full text-center text-sm text-gray-500 hover:text-brand-indigo dark:text-slate-400"
        >
          Cerrar sesión
        </button>
      </div>
    </div>
  );
}
