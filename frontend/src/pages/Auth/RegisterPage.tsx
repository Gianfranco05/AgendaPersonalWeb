import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate, Link } from 'react-router-dom';
import * as authApi from '../../api/authApi';

const registerSchema = z.object({
  name: z.string().min(1, 'El nombre es requerido'),
  email: z.string().email('Email inválido'),
  password: z.string().min(6, 'La contraseña debe tener al menos 6 caracteres'),
});

type RegisterForm = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const navigate = useNavigate();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError,
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
  });

  async function onSubmit(data: RegisterForm) {
    try {
      await authApi.register(data.name, data.email, data.password);
      navigate('/login', { state: { registered: true } });
    } catch (err: unknown) {
      const data = (err as any)?.response?.data;
      const detail = Array.isArray(data?.detail) ? data.detail[0]?.msg : data?.detail;
      setError('root', { message: detail ?? 'Error al registrarse' });
    }
  }

  return (
    <div className="flex min-h-screen bg-white dark:bg-slate-800">
      {/* Panel de marca — oculto en mobile, split-screen desde lg */}
      <div className="hidden w-1/2 flex-col items-center justify-center bg-brand-charcoal px-12 text-center lg:flex">
        <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-white/10">
          <span className="text-2xl font-bold text-white">VP</span>
        </div>
        <h1 className="text-3xl font-bold text-white">Vida Personal</h1>
        <p className="mt-3 max-w-xs text-sm text-white/70">
          Organizá tus finanzas, notas, eventos y metas en un solo lugar.
        </p>
      </div>

      {/* Panel de formulario */}
      <div className="flex w-full flex-col items-center justify-center px-6 py-12 lg:w-1/2">
        <div className="w-full max-w-md">
          <div className="mb-8 text-center lg:hidden">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-charcoal">
              <span className="text-2xl font-bold text-white">VP</span>
            </div>
            <h1 className="text-2xl font-bold text-gray-800 dark:text-slate-100">Crear cuenta</h1>
            <p className="mt-1 text-sm text-gray-500 dark:text-slate-400">Registrate para empezar</p>
          </div>

          <div className="mb-8 hidden text-left lg:block">
            <h2 className="text-2xl font-bold text-gray-800 dark:text-slate-100">Crear cuenta</h2>
            <p className="mt-1 text-sm text-gray-500 dark:text-slate-400">Registrate para empezar</p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {errors.root && (
              <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">
                {errors.root.message}
              </div>
            )}

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-slate-200">Nombre</label>
              <input
                {...register('name')}
                type="text"
                autoFocus
                className="w-full rounded-lg border border-brand-border px-3 py-2.5 text-sm transition-colors focus:border-brand-indigo focus:outline-none focus:ring-1 focus:ring-brand-indigo"
                placeholder="Tu nombre"
              />
              {errors.name && (
                <p className="mt-1 text-xs text-red-500">{errors.name.message}</p>
              )}
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-slate-200">Email</label>
              <input
                {...register('email')}
                type="email"
                autoComplete="email"
                className="w-full rounded-lg border border-brand-border px-3 py-2.5 text-sm transition-colors focus:border-brand-indigo focus:outline-none focus:ring-1 focus:ring-brand-indigo"
                placeholder="tu@email.com"
              />
              {errors.email && (
                <p className="mt-1 text-xs text-red-500">{errors.email.message}</p>
              )}
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-slate-200">Contraseña</label>
              <input
                {...register('password')}
                type="password"
                autoComplete="new-password"
                className="w-full rounded-lg border border-brand-border px-3 py-2.5 text-sm transition-colors focus:border-brand-indigo focus:outline-none focus:ring-1 focus:ring-brand-indigo"
                placeholder="Mínimo 6 caracteres"
              />
              {errors.password && (
                <p className="mt-1 text-xs text-red-500">{errors.password.message}</p>
              )}
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="mt-2 w-full rounded-lg bg-brand-charcoal py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-charcoal-hover disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting ? 'Creando cuenta…' : 'Crear cuenta'}
            </button>
          </form>

          <p className="mt-4 text-center text-xs text-gray-400 dark:text-slate-500">
            Al crear una cuenta aceptás los{' '}
            <Link to="/terms" className="hover:underline">
              Términos y Condiciones
            </Link>{' '}
            y la{' '}
            <Link to="/privacy" className="hover:underline">
              Política de Privacidad
            </Link>
            .
          </p>

          <p className="mt-6 text-center text-sm text-gray-500 dark:text-slate-400">
            ¿Ya tenés cuenta?{' '}
            <Link to="/login" className="font-medium text-brand-indigo hover:text-brand-indigo-hover">
              Iniciá sesión
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
