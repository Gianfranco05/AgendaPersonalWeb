import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { CheckCircle2, Copy } from 'lucide-react';
import LegalLayout from './LegalLayout';
import { createWithdrawalRequest } from '../../api/endpoints';
import { useAuthStore } from '../../store/authStore';

// Mismos límites que el backend (app/modules/arrepentimiento/api_routes.py).
const withdrawalSchema = z.object({
  full_name: z
    .string()
    .trim()
    .min(1, 'Ingresá tu nombre y apellido')
    .max(120, 'Máximo 120 caracteres'),
  email: z.string().trim().email('Email inválido').max(255, 'Máximo 255 caracteres'),
  purchase_detail: z
    .string()
    .trim()
    .min(1, 'Contanos qué compra querés revocar')
    .max(1000, 'Máximo 1000 caracteres'),
  message: z.string().trim().max(2000, 'Máximo 2000 caracteres').optional(),
});

type WithdrawalForm = z.infer<typeof withdrawalSchema>;

const inputCls =
  'w-full rounded-lg border border-brand-border bg-white dark:bg-slate-900 text-gray-900 dark:text-slate-100 px-3 py-2.5 text-sm transition-colors focus:border-brand-indigo focus:outline-none focus:ring-1 focus:ring-brand-indigo';
const labelCls = 'mb-1 block text-sm font-medium text-gray-700 dark:text-slate-200';
const errorCls = 'mt-1 text-xs text-red-500';

function errorMessage(err: unknown): string {
  const status = (err as { response?: { status?: number } })?.response?.status;
  if (status === 429) {
    return 'Hiciste varios pedidos seguidos. Esperá unos minutos y probá de nuevo.';
  }
  if (status === 422) {
    return 'Revisá los datos: hay algún campo con un formato que no pudimos aceptar.';
  }
  return 'No pudimos registrar tu solicitud. Probá de nuevo en unos minutos.';
}

/** Botón de arrepentimiento (Res. 424/2020 de la Secretaría de Comercio
 *  Interior). Público a propósito: no pide sesión ni más datos que los
 *  necesarios para identificar la compra y responderte. */
export default function WithdrawalPage() {
  const user = useAuthStore((s) => s.user);
  const [result, setResult] = useState<{ code: string; email: string } | null>(null);
  const [copied, setCopied] = useState(false);

  const {
    register,
    handleSubmit,
    setValue,
    getValues,
    formState: { errors, isSubmitting },
    setError,
  } = useForm<WithdrawalForm>({
    resolver: zodResolver(withdrawalSchema),
    defaultValues: { full_name: '', email: '', purchase_detail: '', message: '' },
  });

  // Si ya hay sesión se adelanta el formulario, pero nada de esto es requisito.
  useEffect(() => {
    if (!user) return;
    if (!getValues('full_name')) setValue('full_name', user.full_name ?? '');
    if (!getValues('email')) setValue('email', user.email ?? '');
  }, [user, getValues, setValue]);

  async function onSubmit(data: WithdrawalForm) {
    try {
      const res = await createWithdrawalRequest({
        full_name: data.full_name,
        email: data.email,
        purchase_detail: data.purchase_detail,
        message: data.message || undefined,
      });
      setResult({ code: res.code, email: data.email });
    } catch (err: unknown) {
      setError('root', { message: errorMessage(err) });
    }
  }

  async function copyCode() {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result.code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Sin permiso de portapapeles el código sigue visible en pantalla.
    }
  }

  return (
    <LegalLayout title="Botón de arrepentimiento" updatedAt="6 de octubre de 2026">
      {result ? (
        <section role="status" className="space-y-4">
          <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-400">
            <CheckCircle2 size={20} aria-hidden="true" />
            <h2 className="!text-emerald-700 dark:!text-emerald-400">
              Recibimos tu solicitud
            </h2>
          </div>

          <div className="rounded-xl border border-brand-border bg-gray-50 dark:bg-slate-900 p-5 text-center">
            <p className="text-xs text-gray-500 dark:text-slate-400">Tu código de trámite</p>
            <p
              data-testid="withdrawal-code"
              className="mt-1 select-all text-3xl font-bold tracking-widest text-gray-800 dark:text-slate-100"
            >
              {result.code}
            </p>
            <button
              type="button"
              onClick={copyCode}
              className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-brand-border px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-800"
            >
              <Copy size={14} aria-hidden="true" />
              {copied ? 'Copiado' : 'Copiar código'}
            </button>
          </div>

          <p>
            Te mandamos una copia a <strong>{result.email}</strong>. Si no la ves, revisá la
            carpeta de spam. Guardá el código: lo vas a necesitar para consultar el trámite.
          </p>
          <ul>
            <li>Te respondemos en un máximo de 5 días hábiles.</li>
            <li>
              Si corresponde, el reembolso se hace por el mismo medio de pago con el que
              compraste (Mercado Pago).
            </li>
          </ul>
        </section>
      ) : (
        <>
          <section className="space-y-2">
            <h2>Revocá tu compra</h2>
            <p>
              Si compraste una plantilla en Can_cen y te arrepentiste, podés revocar la compra
              desde acá. La ley te da 10 días corridos desde la compra; nuestra política de
              reembolsos te da 14. Si ya pasó ese plazo igual podés mandar la solicitud, y la
              revisamos caso por caso.
            </p>
            <p>
              <strong>No hace falta tener cuenta ni iniciar sesión.</strong> Solo te pedimos lo
              necesario para identificar la compra y responderte.
            </p>
          </section>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            {errors.root && (
              <div role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-600">
                {errors.root.message}
              </div>
            )}

            <div>
              <label htmlFor="wd-full-name" className={labelCls}>
                Nombre y apellido
              </label>
              <input
                id="wd-full-name"
                {...register('full_name')}
                type="text"
                autoComplete="name"
                className={inputCls}
              />
              {errors.full_name && <p className={errorCls}>{errors.full_name.message}</p>}
            </div>

            <div>
              <label htmlFor="wd-email" className={labelCls}>
                Email
              </label>
              <input
                id="wd-email"
                {...register('email')}
                type="email"
                autoComplete="email"
                className={inputCls}
                placeholder="tu@email.com"
              />
              <p className="mt-1 text-xs text-gray-500 dark:text-slate-400">
                Ahí te mandamos el código de trámite y la respuesta.
              </p>
              {errors.email && <p className={errorCls}>{errors.email.message}</p>}
            </div>

            <div>
              <label htmlFor="wd-purchase" className={labelCls}>
                Plantilla / compra
              </label>
              <textarea
                id="wd-purchase"
                {...register('purchase_detail')}
                rows={3}
                className={inputCls}
              />
              <p className="mt-1 text-xs text-gray-500 dark:text-slate-400">
                Nombre de la plantilla, fecha y número de operación de Mercado Pago si lo tenés.
              </p>
              {errors.purchase_detail && (
                <p className={errorCls}>{errors.purchase_detail.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="wd-message" className={labelCls}>
                Mensaje <span className="font-normal text-gray-400">(opcional)</span>
              </label>
              <textarea id="wd-message" {...register('message')} rows={3} className={inputCls} />
              {errors.message && <p className={errorCls}>{errors.message.message}</p>}
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="press-effect w-full rounded-lg bg-brand-charcoal py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-charcoal-hover disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting ? 'Enviando…' : 'Solicitar la revocación'}
            </button>
          </form>
        </>
      )}
    </LegalLayout>
  );
}
