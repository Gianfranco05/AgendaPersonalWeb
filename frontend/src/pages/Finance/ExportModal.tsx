import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { X, Download } from 'lucide-react';
import { useCategories, useBankAccounts } from '../../hooks/useFinance';
import { downloadFinanceExport } from '../../api/endpoints';
import { apiErrorMessage } from '../../utils/apiError';
import { toLocalDateString } from '../../utils/date';
import { saveBlob } from '../../utils/financeTransfer';
import type { FinanceExportParams } from '../../types';

const schema = z
  .object({
    date_from: z.string().min(1, 'Elegí la fecha de inicio'),
    date_to: z.string().min(1, 'Elegí la fecha de fin'),
    type: z.enum(['', 'income', 'expense']),
    category_id: z.string(),
    account_id: z.string(),
    format: z.enum(['xlsx', 'pdf']),
    include_investments: z.boolean(),
  })
  .refine((v) => !v.date_from || !v.date_to || v.date_to >= v.date_from, {
    path: ['date_to'],
    message: 'La fecha de fin no puede ser anterior a la de inicio',
  });

type FormData = z.infer<typeof schema>;

/** Filtros activos de la tabla de transacciones, para prellenar el modal. */
export interface ExportDefaults {
  date_from?: string;
  date_to?: string;
  type?: string;
  category?: string;
}

interface Props {
  defaults?: ExportDefaults;
  onClose: () => void;
}

const inputCls =
  'w-full rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:border-brand-indigo focus:outline-none focus:ring-1 focus:ring-brand-indigo';
const labelCls = 'mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400';
const errorCls = 'mt-1 text-xs text-red-500';

function monthStart(): string {
  const d = new Date();
  return toLocalDateString(new Date(d.getFullYear(), d.getMonth(), 1));
}

export function buildExportParams(v: FormData): FinanceExportParams {
  return {
    format: v.format,
    date_from: v.date_from,
    date_to: v.date_to,
    ...(v.type && { type: v.type }),
    ...(v.category_id && { category_id: v.category_id }),
    ...(v.account_id && { account_id: v.account_id }),
    ...(v.include_investments && { include_investments: true }),
  };
}

export default function ExportModal({ defaults, onClose }: Props) {
  const { data: categories = [] } = useCategories();
  const { data: accounts = [] } = useBankAccounts();
  const [error, setError] = useState('');

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      date_from: defaults?.date_from || monthStart(),
      date_to: defaults?.date_to || toLocalDateString(),
      type: defaults?.type === 'income' || defaults?.type === 'expense' ? defaults.type : '',
      category_id: defaults?.category ?? '',
      account_id: '',
      format: 'xlsx',
      include_investments: false,
    },
  });
  const format = watch('format');

  async function onSubmit(values: FormData) {
    setError('');
    try {
      const { blob, filename } = await downloadFinanceExport(buildExportParams(values));
      saveBlob(blob, filename);
      onClose();
    } catch (err) {
      setError(await exportErrorMessage(err));
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 px-4 py-8 sm:py-12">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="export-title"
        className="w-full max-w-lg rounded-xl bg-white dark:bg-slate-800 shadow-xl"
      >
        <div className="flex items-center justify-between border-b border-gray-100 dark:border-slate-800 px-6 py-4">
          <h3 id="export-title" className="text-lg font-semibold text-gray-800 dark:text-slate-100">
            Exportar finanzas
          </h3>
          <button
            type="button"
            aria-label="Cerrar"
            onClick={onClose}
            className="rounded-lg p-1 text-gray-400 dark:text-slate-500 hover:bg-gray-100 dark:hover:bg-slate-700"
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 px-6 py-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="exp-from" className={labelCls}>Desde</label>
              <input id="exp-from" type="date" className={inputCls} {...register('date_from')} />
              {errors.date_from && <p className={errorCls}>{errors.date_from.message}</p>}
            </div>
            <div>
              <label htmlFor="exp-to" className={labelCls}>Hasta</label>
              <input id="exp-to" type="date" className={inputCls} {...register('date_to')} />
              {errors.date_to && <p className={errorCls}>{errors.date_to.message}</p>}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="exp-type" className={labelCls}>Tipo</label>
              <select id="exp-type" className={inputCls} {...register('type')}>
                <option value="">Ingresos y egresos</option>
                <option value="income">Solo ingresos</option>
                <option value="expense">Solo egresos</option>
              </select>
            </div>
            <div>
              <label htmlFor="exp-cat" className={labelCls}>Categoría</label>
              <select id="exp-cat" className={inputCls} {...register('category_id')}>
                <option value="">Todas</option>
                <option value="none">Sin categoría</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="exp-acc" className={labelCls}>Cuenta</label>
            <select id="exp-acc" className={inputCls} {...register('account_id')}>
              <option value="">Todas</option>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-400 dark:text-slate-500">
              Se filtra según banco, tipo y últimos 4 dígitos de la cuenta.
            </p>
          </div>

          <fieldset>
            <legend className={labelCls}>Formato</legend>
            <div className="flex rounded-lg border border-gray-200 dark:border-slate-700 p-0.5">
              {([['xlsx', 'Excel (.xlsx)'], ['pdf', 'PDF']] as const).map(([value, label]) => (
                <label
                  key={value}
                  className={`flex-1 cursor-pointer rounded-md px-4 py-2 text-center text-sm font-medium transition-colors ${
                    format === value
                      ? 'bg-brand-charcoal text-white'
                      : 'text-gray-500 dark:text-slate-400'
                  }`}
                >
                  <input type="radio" value={value} className="sr-only" {...register('format')} />
                  {label}
                </label>
              ))}
            </div>
          </fieldset>

          <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-slate-200">
            <input type="checkbox" {...register('include_investments')} />
            Incluir inversiones, patrimonio y movimientos recurrentes
          </label>

          <p className="text-xs text-gray-400 dark:text-slate-500">
            Máximo 20.000 movimientos en Excel y 5.000 en PDF. Si te pasás, achicá el rango de fechas.
          </p>

          {error && (
            <p role="alert" className="rounded-lg bg-red-50 dark:bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-300">
              {error}
            </p>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-gray-200 dark:border-slate-700 px-4 py-2 text-sm text-gray-600 dark:text-slate-300"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex items-center gap-2 rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white hover:bg-brand-charcoal-hover disabled:opacity-60"
            >
              <Download size={16} />
              {isSubmitting ? 'Generando…' : 'Descargar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/** El error de una descarga llega como Blob (responseType: 'blob'): se lee el JSON de adentro. */
async function exportErrorMessage(err: unknown): Promise<string> {
  const data = (err as { response?: { data?: unknown } })?.response?.data;
  if (data instanceof Blob) {
    try {
      const parsed = JSON.parse(await data.text()) as { detail?: unknown };
      if (typeof parsed.detail === 'string') return parsed.detail;
    } catch {
      /* cuerpo que no es JSON */
    }
    return 'No pudimos generar el reporte. Probá de nuevo.';
  }
  return apiErrorMessage(err, 'No pudimos generar el reporte. Probá de nuevo.');
}
