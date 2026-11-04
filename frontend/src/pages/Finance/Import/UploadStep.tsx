import { useRef, useState } from 'react';
import { Upload, FileSpreadsheet } from 'lucide-react';
import { useImportPresets } from '../../../hooks/useFinanceImport';
import { useBankAccounts } from '../../../hooks/useFinance';

export const MAX_IMPORT_BYTES = 2 * 1024 * 1024;

/** Valida en el cliente lo mismo que el server (que igual lo vuelve a validar). */
export function validateImportFile(file: { name: string; size: number }): string | null {
  if (!/\.(csv|xlsx)$/i.test(file.name)) {
    return 'Subí un archivo .csv o .xlsx. Si es un .xls viejo, abrilo en Excel y guardalo como .xlsx.';
  }
  if (file.size > MAX_IMPORT_BYTES) return 'El archivo pesa más de 2 MB. Dividilo por fechas.';
  if (file.size === 0) return 'El archivo está vacío.';
  return null;
}

interface Props {
  busy: boolean;
  error: string;
  onSubmit: (file: File, opts: { preset: string; account_id: string }) => void;
}

const inputCls =
  'w-full rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:border-brand-indigo focus:outline-none focus:ring-1 focus:ring-brand-indigo';
const labelCls = 'mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400';

export default function UploadStep({ busy, error, onSubmit }: Props) {
  const { data: presets = [] } = useImportPresets();
  const { data: accounts = [] } = useBankAccounts();
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState('');
  const [preset, setPreset] = useState('auto');
  const [accountId, setAccountId] = useState('');
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function choose(next: File | undefined | null) {
    if (!next) return;
    const problem = validateImportFile(next);
    setFileError(problem ?? '');
    setFile(problem ? null : next);
  }

  return (
    <div className="space-y-4 rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          choose(e.dataTransfer.files[0]);
        }}
        className={`flex flex-col items-center gap-2 rounded-xl border-2 border-dashed px-4 py-10 text-center transition-colors ${
          dragging
            ? 'border-brand-indigo bg-brand-indigo/5'
            : 'border-gray-200 dark:border-slate-700'
        }`}
      >
        {file ? <FileSpreadsheet size={28} className="text-brand-indigo" /> : <Upload size={28} className="text-gray-400" />}
        <p className="text-sm text-gray-700 dark:text-slate-200">
          {file ? file.name : 'Arrastrá acá tu archivo .csv o .xlsx'}
        </p>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-1.5 text-sm text-gray-600 dark:text-slate-300"
        >
          {file ? 'Elegir otro archivo' : 'Elegir archivo'}
        </button>
        <input
          ref={inputRef}
          data-testid="import-file-input"
          type="file"
          accept=".csv,.xlsx"
          className="sr-only"
          onChange={(e) => choose(e.target.files?.[0])}
        />
        <p className="text-xs text-gray-400 dark:text-slate-500">Hasta 2 MB y 5.000 movimientos por archivo.</p>
      </div>
      {fileError && <p role="alert" className="text-sm text-red-500">{fileError}</p>}

      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label htmlFor="imp-preset" className={labelCls}>Origen del archivo</label>
          <select id="imp-preset" className={inputCls} value={preset} onChange={(e) => setPreset(e.target.value)}>
            <option value="auto">Detectar automáticamente</option>
            {presets.map((p) => (
              <option key={p.key} value={p.key}>{p.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="imp-account" className={labelCls}>Cuenta destino (opcional)</label>
          <select id="imp-account" className={inputCls} value={accountId} onChange={(e) => setAccountId(e.target.value)}>
            <option value="">Sin cuenta</option>
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
        </div>
      </div>

      <details className="rounded-lg bg-gray-50 dark:bg-slate-900/40 px-4 py-3 text-sm text-gray-600 dark:text-slate-300">
        <summary className="cursor-pointer font-medium">Cómo descargar el reporte de Mercado Pago</summary>
        <ol className="mt-2 list-decimal space-y-1 pl-5">
          <li>Entrá a Mercado Pago, sección «Informes y facturación».</li>
          <li>Elegí «Ir a reportes de pagos y extractos de cuenta».</li>
          <li>Generá el reporte de «Dinero disponible» o de «Dinero en cuenta» en formato .csv o .xlsx.</li>
          <li>Subilo acá. Si tu banco usa otro formato, elegí «Otro banco o billetera» y marcá las columnas una sola vez: la app las recuerda.</li>
        </ol>
      </details>

      {error && <p role="alert" className="rounded-lg bg-red-50 dark:bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-300">{error}</p>}

      <div className="flex justify-end">
        <button
          type="button"
          disabled={!file || busy}
          onClick={() => file && onSubmit(file, { preset, account_id: accountId })}
          className="rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white hover:bg-brand-charcoal-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? 'Leyendo archivo…' : 'Previsualizar'}
        </button>
      </div>
    </div>
  );
}
