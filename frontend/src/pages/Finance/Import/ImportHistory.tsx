import { useState } from 'react';
import { Undo2 } from 'lucide-react';
import { useImports, undoImportBatch } from '../../../hooks/useFinanceImport';
import { apiErrorMessage } from '../../../utils/apiError';
import { parseServerTimestamp } from '../../../utils/date';
import type { ImportBatch } from '../../../types';

const PRESET_LABEL: Record<string, string> = {
  mercadopago_release: 'Mercado Pago · Dinero disponible',
  mercadopago_account_money: 'Mercado Pago · Dinero en cuenta',
  generic: 'Otro banco o billetera',
};

function formatDate(value: string | null): string {
  if (!value) return '';
  return parseServerTimestamp(value).toLocaleDateString('es-AR');
}

/** Texto de la confirmación de deshacer: borra todo el lote, también lo editado. */
export function undoWarning(batch: ImportBatch): string {
  const edited =
    batch.edited_count > 0
      ? `\n\n${batch.edited_count} ${batch.edited_count === 1 ? 'de esos movimientos lo editaste' : 'de esos movimientos los editaste'} después de importar: también se van a borrar con sus cambios.`
      : '';
  return `Vas a borrar los ${batch.imported_count} movimientos de «${batch.filename}».${edited}\n\n¿Querés deshacer la importación?`;
}

export default function ImportHistory() {
  const { data: batches = [], isLoading } = useImports();
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState('');

  async function handleUndo(batch: ImportBatch) {
    if (!window.confirm(undoWarning(batch))) return;
    setBusyId(batch.id);
    setError('');
    try {
      await undoImportBatch(batch.id);
    } catch (err) {
      setError(apiErrorMessage(err, 'No pudimos deshacer la importación.'));
    } finally {
      setBusyId(null);
    }
  }

  if (isLoading || batches.length === 0) return null;

  return (
    <section className="space-y-2" aria-label="Historial de importaciones">
      <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-200">Importaciones anteriores</h3>
      {error && <p role="alert" className="text-sm text-red-500">{error}</p>}
      <ul className="divide-y divide-gray-100 dark:divide-slate-700 rounded-xl bg-white dark:bg-slate-800 shadow-sm">
        {batches.map((b) => (
          <li key={b.id} className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-sm">
            <div className="min-w-0">
              <p className="truncate font-medium text-gray-800 dark:text-slate-100">{b.filename}</p>
              <p className="text-xs text-gray-500 dark:text-slate-400">
                {formatDate(b.confirmed_at ?? b.created_at)} · {PRESET_LABEL[b.preset] ?? b.preset} ·{' '}
                {b.imported_count} importados, {b.duplicate_count} repetidos, {b.error_count} con error
              </p>
            </div>
            {b.status === 'confirmed' ? (
              <button
                type="button"
                disabled={busyId === b.id}
                onClick={() => handleUndo(b)}
                className="flex items-center gap-1 rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-1.5 text-xs text-gray-600 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700/50 disabled:opacity-50"
              >
                <Undo2 size={14} />
                Deshacer
              </button>
            ) : (
              <span className="rounded-full bg-gray-100 dark:bg-slate-700 px-2 py-0.5 text-xs text-gray-500 dark:text-slate-400">
                Deshecha el {formatDate(b.undone_at)}
              </span>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
