import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';

const loginSchema = z.object({
  email: z.string().email('Email inválido'),
  password: z.string().min(1, 'La contraseña es requerida'),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const navigate = useNavigate();
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
      const detail =
        err && typeof err === 'object' && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      setError('root', { message: detail ?? 'Error al iniciar sesión' });
    }
  }

  return (
    <div className="flex h-screen items-center justify-center bg-gray-50">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-lg">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[#7C3AED]">
            <span className="text-2xl font-bold text-white">VP</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-800">Vida Personal</h1>
          <p className="mt-1 text-sm text-gray-500">Iniciá sesión para continuar</p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {errors.root && (
            <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">
              {errors.root.message}
            </div>
          )}

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Email</label>
            <input
              {...register('email')}
              type="email"
              autoComplete="email"
              autoFocus
              className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm transition-colors focus:border-[#7C3AED] focus:outline-none focus:ring-1 focus:ring-[#7C3AED]"
              placeholder="tu@email.com"
            />
            {errors.email && (
              <p className="mt-1 text-xs text-red-500">{errors.email.message}</p>
            )}
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Contraseña</label>
            <input
              {...register('password')}
              type="password"
              autoComplete="current-password"
              className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm transition-colors focus:border-[#7C3AED] focus:outline-none focus:ring-1 focus:ring-[#7C3AED]"
              placeholder="Tu contraseña"
            />
            {errors.password && (
              <p className="mt-1 text-xs text-red-500">{errors.password.message}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="mt-2 w-full rounded-lg bg-[#7C3AED] py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#6D28D9] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? 'Iniciando sesión…' : 'Iniciar sesión'}
          </button>
        </form>

        <p className="mt-6 text-center text-xs text-gray-400">
          ¿No tenés cuenta?{' '}
          <a href="/auth/register" className="text-[#7C3AED] hover:underline">
            Registrate
          </a>
        </p>
      </div>
    </div>
  );
}
