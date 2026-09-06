import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { X } from 'lucide-react';
import { saveOpportunity } from '../../hooks/useWork';
import type { OpportunityStatus, WorkOpportunity } from '../../types';

const schema = z.object({
  company: z.string().min(1, 'La empresa es requerida'),
  role: z.string().min(1, 'El puesto es requerido'),
  status: z.enum(['aplicado', 'entrevista', 'oferta', 'rechazado', 'aceptado']),
  salary: z
    .union([z.number(), z.nan()])
    .optional()
    .refine((v) => v === undefined || Number.isNaN(v) || v >= 0, 'El salario debe ser 0 o mayor'),
  applied_date: z.string(),
});

type FormData = z.infer<typeof schema>;

interface Props {
  opportunity: WorkOpportunity | null;
  onClose: () => void;
  onSaved: () => void;
}

const inputCls =
  'w-full rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-2 text-sm focus:border-brand-work focus:outline-none focus:ring-1 focus:ring-brand-work';
const errorCls = 'mt-1 text-xs text-red-500';

const STATUS_LABELS: Record<OpportunityStatus, string> = {
  aplicado: 'Aplicado',
  entrevista: 'Entrevista',
  oferta: 'Oferta',
  rechazado: 'Rechazado',
  aceptado: 'Aceptado',
};

export default function OpportunityForm({ opportunity, onClose, onSaved }: Props) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { company: '', role: '', status: 'aplicado', salary: undefined, applied_date: '' },
  });

  useEffect(() => {
    if (opportunity) {
      reset({
        company: opportunity.company,
        role: opportunity.role,
        status: opportunity.status,
        salary: opportunity.salary ?? undefined,
        applied_date: opportunity.applied_date ?? '',
      });
    }
  }, [opportunity, reset]);

  async function onSubmit(data: FormData) {
    const salary = data.salary === undefined || Number.isNaN(data.salary) ? null : data.salary;
    await saveOpportunity(opportunity, { ...data, salary, applied_date: data.applied_date || null });
    onSaved();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 px-4 py-8 sm:py-12">
      <div className="w-full max-w-lg rounded-2xl bg-white dark:bg-slate-800 shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-100 dark:border-slate-800 px-6 py-4">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">
            {opportunity ? 'Editar oportunidad' : 'Nueva oportunidad'}
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-gray-400 dark:text-slate-500 hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-gray-600 dark:hover:text-slate-200"
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 px-6 py-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Empresa</label>
              <input {...register('company')} type="text" className={inputCls} placeholder="Acme" />
              {errors.company && <p className={errorCls}>{errors.company.message}</p>}
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Puesto</label>
              <input {...register('role')} type="text" className={inputCls} placeholder="Backend Developer" />
              {errors.role && <p className={errorCls}>{errors.role.message}</p>}
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Estado</label>
            <select {...register('status')} className={inputCls}>
              {Object.entries(STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">
                Salario (opcional)
              </label>
              <input
                {...register('salary', { valueAsNumber: true })}
                type="number"
                min={0}
                className={inputCls}
                placeholder="1500000"
              />
              {errors.salary && <p className={errorCls}>{errors.salary.message}</p>}
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">
                Fecha de aplicación (opcional)
              </label>
              <input {...register('applied_date')} type="date" className={inputCls} />
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-gray-200 dark:border-slate-700 px-4 py-2 text-sm font-medium text-gray-600 dark:text-slate-300 transition-colors hover:bg-gray-50 dark:hover:bg-slate-700/50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded-lg bg-brand-work px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90 disabled:opacity-50"
            >
              {isSubmitting ? 'Guardando…' : opportunity ? 'Actualizar' : 'Crear'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
