import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Settings2 } from 'lucide-react';
import {
  discardImportPreview,
  previewImport,
  updateImportMapping,
} from '../../../api/endpoints';
import { confirmImportBatch } from '../../../hooks/useFinanceImport';
import { apiErrorMessage } from '../../../utils/apiError';
import {
  buildConfirmRows,
  defaultSelection,
  formatCents,
  selectedTotals,
} from '../../../utils/financeTransfer';
import type { ImportBatch, ImportMapping, ImportPreview } from '../../../types';
import UploadStep from './UploadStep';
import MappingPanel from './MappingPanel';
import PreviewTable from './PreviewTable';
import ImportHistory from './ImportHistory';

type Step = 'upload' | 'preview' | 'done';

export default function ImportPage() {
  const [step, setStep] = useState<Step>('upload');
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [result, setResult] = useState<ImportBatch | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [showMapping, setShowMapping] = useState(false);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [categories, setCategories] = useState<Record<number, string>>({});
  const [types, setTypes] = useState<Record<number, 'income' | 'expense'>>({});
  const lastFile = useRef<File | null>(null);
  const lastOpts = useRef<{ preset: string; account_id: string }>({ preset: 'auto', account_id: '' });

  function load(next: ImportPreview) {
    setPreview(next);
    setSelected(defaultSelection(next.rows));
    setCategories({});
    setTypes({});
    setShowMapping(!next.mapping_complete);
  }

  async function handleUpload(file: File, opts: { preset: string; account_id: string }) {
    setBusy(true);
    setError('');
    lastFile.current = file;
    lastOpts.current = opts;
    try {
      load(await previewImport(file, opts));
      setStep('preview');
    } catch (err) {
      setError(apiErrorMessage(err, 'No pudimos leer el archivo.'));
    } finally {
      setBusy(false);
    }
  }

  async function handleMapping(update: { header_row?: number; mapping?: ImportMapping }) {
    if (!preview) return;
    setBusy(true);
    setError('');
    try {
      load(await updateImportMapping(preview.batch_id, update));
    } catch (err) {
      setError(apiErrorMessage(err, 'No pudimos aplicar las columnas.'));
    } finally {
      setBusy(false);
    }
  }

  const confirmRows = useMemo(
    () => (preview ? buildConfirmRows(preview.rows, selected, categories, types) : []),
    [preview, selected, categories, types],
  );
  const totals = useMemo(
    () => (preview ? selectedTotals(preview.rows, selected, types) : []),
    [preview, selected, types],
  );

  async function handleConfirm() {
    if (!preview || confirmRows.length === 0) return;
    setBusy(true);
    setError('');
    try {
      setResult(await confirmImportBatch(preview.batch_id, confirmRows));
      setPreview(null);
      setStep('done');
    } catch (err) {
      setError(apiErrorMessage(err, 'No pudimos importar los movimientos.'));
    } finally {
      setBusy(false);
    }
  }

  async function handleCancel() {
    const id = preview?.batch_id;
    setPreview(null);
    setStep('upload');
    setError('');
    if (id) await discardImportPreview(id).catch(() => undefined);
  }

  // Si se sale de la página con una previsualización abierta, se descarta (no crea nada).
  const openBatch = useRef<string | null>(null);
  useEffect(() => {
    openBatch.current = preview?.batch_id ?? null;
  }, [preview]);
  useEffect(
    () => () => {
      if (openBatch.current) void discardImportPreview(openBatch.current).catch(() => undefined);
    },
    [],
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link
          to="/finances"
          aria-label="Volver a Finanzas"
          className="rounded-lg p-1.5 text-gray-500 hover:bg-gray-100 dark:text-slate-400 dark:hover:bg-slate-700"
        >
          <ArrowLeft size={20} />
        </Link>
        <h2 className="text-2xl font-bold text-gray-800 dark:text-slate-100">Importar movimientos</h2>
      </div>

      {step === 'upload' && (
        <>
          <UploadStep busy={busy} error={error} onSubmit={handleUpload} />
          <ImportHistory />
        </>
      )}

      {step === 'preview' && preview && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm text-gray-600 dark:text-slate-300">
              <span className="font-medium">{preview.filename}</span> · {preview.counts.ok} para importar,{' '}
              {preview.counts.possible_duplicate} posibles duplicados, {preview.counts.duplicate} ya importados,{' '}
              {preview.counts.error} con error
            </p>
            <button
              type="button"
              onClick={() => setShowMapping((s) => !s)}
              className="flex items-center gap-1 rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-1.5 text-sm text-gray-600 dark:text-slate-300"
            >
              <Settings2 size={14} />
              Ajustar columnas
            </button>
          </div>

          {preview.warnings.map((w) => (
            <p key={w} className="rounded-lg bg-amber-50 dark:bg-amber-500/10 px-3 py-2 text-sm text-amber-800 dark:text-amber-200">
              {w}
            </p>
          ))}

          {showMapping && <MappingPanel key={preview.batch_id + preview.mapping_source} preview={preview} busy={busy} onApply={handleMapping} />}

          {preview.mapping_complete && (
            <PreviewTable
              rows={preview.rows}
              selected={selected}
              categories={categories}
              types={types}
              onSelectedChange={setSelected}
              onCategoryChange={(i, c) => setCategories((m) => ({ ...m, [i]: c }))}
              onTypeChange={(i, t) => setTypes((m) => ({ ...m, [i]: t }))}
            />
          )}

          {error && <p role="alert" className="rounded-lg bg-red-50 dark:bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-300">{error}</p>}

          <div className="sticky bottom-0 flex flex-wrap items-center justify-between gap-3 rounded-xl bg-white dark:bg-slate-800 p-4 shadow-md">
            <div className="text-sm text-gray-600 dark:text-slate-300" data-testid="import-summary">
              {confirmRows.length === 0
                ? 'No hay movimientos seleccionados.'
                : `Vas a importar ${confirmRows.length} ${confirmRows.length === 1 ? 'movimiento' : 'movimientos'}: ` +
                  totals
                    .map((t) => `ingresos ${formatCents(t.income, t.currency)}, egresos ${formatCents(t.expense, t.currency)}`)
                    .join(' · ')}
            </div>
            <div className="flex gap-2">
              <button type="button" onClick={handleCancel} className="rounded-lg border border-gray-200 dark:border-slate-700 px-4 py-2 text-sm text-gray-600 dark:text-slate-300">
                Cancelar
              </button>
              <button
                type="button"
                disabled={busy || confirmRows.length === 0}
                onClick={handleConfirm}
                className="rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white hover:bg-brand-charcoal-hover disabled:cursor-not-allowed disabled:opacity-50"
              >
                {busy ? 'Importando…' : `Importar ${confirmRows.length}`}
              </button>
            </div>
          </div>
        </div>
      )}

      {step === 'done' && result && (
        <div className="space-y-3 rounded-xl bg-white dark:bg-slate-800 p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">Importación lista</h3>
          <p className="text-sm text-gray-600 dark:text-slate-300">
            Se importaron {result.imported_count} movimientos de «{result.filename}». Podés deshacerlo desde el historial.
          </p>
          <div className="flex gap-2">
            <Link to="/finances" className="rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white hover:bg-brand-charcoal-hover">
              Ver transacciones
            </Link>
            <button
              type="button"
              onClick={() => {
                setStep('upload');
                setResult(null);
              }}
              className="rounded-lg border border-gray-200 dark:border-slate-700 px-4 py-2 text-sm text-gray-600 dark:text-slate-300"
            >
              Importar otro archivo
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
