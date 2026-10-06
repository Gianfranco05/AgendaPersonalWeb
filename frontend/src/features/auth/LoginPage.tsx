import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import GoogleIcon from '../../components/icons/GoogleIcon';
import PublicFooter from '../../components/PublicFooter';
import { GOOGLE_CALLBACK_PATH } from '../../api/client';

const API_BASE = import.meta.env.VITE_API_URL ?? '';

const loginSchema = z.object({
  email: z.string().email('Email inválido'),
  password: z.string().min(1, 'La contraseña es requerida'),
});

type LoginForm = z.infer<typeof loginSchema>;

function handleGoogleLogin() {
  const redirectUri = `${window.location.origin}${GOOGLE_CALLBACK_PATH}`;
  window.location.href = `${API_BASE}/auth/api/google/login?app_redirect=${encodeURIComponent(redirectUri)}`;
}

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const locationState = location.state as { googleError?: string; registered?: boolean } | null;
  const googleError = locationState?.googleError;
  const registered = locationState?.registered;
  const { login, isAuthenticated } = useAuthStore();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError,
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  useEffect(() => {
    if (isAuthenticated) navigate('/', { replace: true });
  }, [isAuthenticated, navigate]);

  async function onSubmit(data: LoginForm) {
    try {
      await login(data.email, data.password);
      navigate('/');
    } catch (err: unknown) {
      const data = (err as any)?.response?.data;
      const detail = Array.isArray(data?.detail) ? data.detail[0]?.msg : data?.detail;
      setError('root', { message: detail ?? 'Error al iniciar sesión' });
    }
  }

  return (
    <div className="flex min-h-screen bg-white dark:bg-slate-800">
      {/* Panel de marca — oculto en mobile, split-screen desde lg */}
      <div className="hidden w-1/2 flex-col items-center justify-center bg-brand-charcoal px-12 text-center lg:flex">
        <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-white/10">
          <span className="text-2xl font-bold text-white">C</span>
        </div>
        <h1 className="text-3xl font-bold text-white">Can_cen</h1>
        <p className="mt-3 max-w-xs text-sm text-white/70">
          Organizá tus finanzas, notas, eventos y metas en un solo lugar.
        </p>
      </div>

      {/* Panel de formulario */}
      <div className="flex w-full flex-col items-center justify-center px-6 py-12 lg:w-1/2">
        <div className="animate-scale-in w-full max-w-md">
          <div className="mb-8 text-center lg:hidden">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-charcoal">
              <span className="text-2xl font-bold text-white">C</span>
            </div>
            <h1 className="text-2xl font-bold text-gray-800 dark:text-slate-100">Can_cen</h1>
          </div>

          <div className="mb-8 hidden text-left lg:block">
            <h2 className="text-2xl font-bold text-gray-800 dark:text-slate-100">Iniciar sesión</h2>
            <p className="mt-1 text-sm text-gray-500 dark:text-slate-400">Ingresá tus credenciales para continuar</p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {registered && (
              <div className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-700">
                Cuenta creada. Iniciá sesión para empezar.
              </div>
            )}
            {googleError && (
              <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">{googleError}</div>
            )}
            {errors.root && (
              <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">
                {errors.root.message}
              </div>
            )}

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-slate-200">Email</label>
              <input
                {...register('email')}
                type="email"
                autoComplete="email"
                autoFocus
                className="w-full rounded-lg border border-brand-border px-3 py-2.5 text-sm transition-colors focus:border-brand-indigo focus:outline-none focus:ring-1 focus:ring-brand-indigo"
                placeholder="tu@email.com"
              />
              {errors.email && (
                <p className="mt-1 text-xs text-red-500">{errors.email.message}</p>
              )}
            </div>

            <div>
              <div className="mb-1 flex items-center justify-between">
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-200">Contraseña</label>
                <Link to="/olvide-password" className="text-xs font-medium text-brand-indigo hover:text-brand-indigo-hover">
                  ¿Olvidaste tu contraseña?
                </Link>
              </div>
              <input
                {...register('password')}
                type="password"
                autoComplete="current-password"
                className="w-full rounded-lg border border-brand-border px-3 py-2.5 text-sm transition-colors focus:border-brand-indigo focus:outline-none focus:ring-1 focus:ring-brand-indigo"
                placeholder="Tu contraseña"
              />
              {errors.password && (
                <p className="mt-1 text-xs text-red-500">{errors.password.message}</p>
              )}
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="press-effect mt-2 w-full rounded-lg bg-brand-charcoal py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-charcoal-hover disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting ? 'Iniciando sesión…' : 'Iniciar sesión'}
            </button>
          </form>

          <div className="my-5 flex items-center gap-3">
            <div className="h-px flex-1 bg-brand-border" />
            <span className="text-xs text-gray-400 dark:text-slate-500">o</span>
            <div className="h-px flex-1 bg-brand-border" />
          </div>

          <button
            type="button"
            onClick={handleGoogleLogin}
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-brand-border bg-white py-2.5 text-sm font-semibold text-gray-700 transition-colors hover:bg-gray-50 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
          >
            <GoogleIcon />
            Continuar con Google
          </button>

          <p className="mt-6 text-center text-sm text-gray-500 dark:text-slate-400">
            ¿No tenés cuenta?{' '}
            <Link to="/register" className="font-medium text-brand-indigo hover:text-brand-indigo-hover">
              Registrate
            </Link>
          </p>

          <PublicFooter className="mt-8" />
        </div>
      </div>
    </div>
  );
}
