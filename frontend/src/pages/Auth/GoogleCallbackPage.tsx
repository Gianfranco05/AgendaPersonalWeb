import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';

const ERROR_MESSAGES: Record<string, string> = {
  google_denied: 'Cancelaste el inicio de sesión con Google.',
  google_failed: 'No pudimos verificar tu cuenta de Google. Probá de nuevo.',
  inactive_account: 'Tu cuenta está inactiva. Contactá a soporte.',
};

/**
 * Adonde vuelve el navegador (GOOGLE_CALLBACK_PATH) después de /auth/api/google/login. El backend
 * ya dejó las cookies httpOnly de sesión seteadas en esa respuesta (mismo
 * mecanismo que login/register normal) — acá no hace falta leer ningún
 * token de la query string, solo confirmar la sesión contra /auth/api/me
 * y mandar al usuario adentro. El access_token/refresh_token que también
 * vienen en la URL son para mobile (WebView efímera); la web los ignora.
 */
export default function GoogleCallbackPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const checkAuth = useAuthStore((s) => s.checkAuth);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const errorParam = searchParams.get('error');
    if (errorParam) {
      navigate('/login', {
        replace: true,
        state: { googleError: ERROR_MESSAGES[errorParam] ?? 'No se pudo iniciar sesión con Google.' },
      });
      return;
    }

    checkAuth().then(() => {
      if (useAuthStore.getState().isAuthenticated) {
        navigate('/', { replace: true });
      } else {
        setError('No pudimos confirmar tu sesión. Probá iniciar sesión de nuevo.');
      }
    });
  }, [checkAuth, navigate, searchParams]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-white dark:bg-slate-800">
      {error ? (
        <div className="text-center">
          <p className="mb-4 text-sm text-red-600">{error}</p>
          <button
            type="button"
            onClick={() => navigate('/login', { replace: true })}
            className="text-sm font-medium text-brand-indigo hover:text-brand-indigo-hover"
          >
            Volver al login
          </button>
        </div>
      ) : (
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-indigo border-t-transparent" />
      )}
    </div>
  );
}
