import { useState } from 'react';
import { Pencil } from 'lucide-react';
import { saveInvestmentSettings } from '../../hooks/useInvestments';
import { apiErrorMessage } from '../../utils/apiError';
import { ageLabel, daysSince, formatMoney, parseDecimal } from '../../utils/investments';

const STALE_DAYS = 7;
const MAX_RATE = 9_999_999.9999;

interface Props {
  usdArs: number | null;
  eurArs: number | null;
  updatedAt: string | null;
  /** El euro solo se pide cuando hay activos en EUR. */
  showEur: boolean;
}

const inputCls =
  'w-full rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-sm focus:border-brand-indigo focus:outline-none focus:ring-1 focus:ring-brand-indigo';

function toText(n: number | null): string {
  return n === null ? '' : String(n).replace('.', ',');
}

/** Cotización del dólar (y del euro si hace falta) que carga el usuario. */
export default function FxRatesEditor({ usdArs, eurArs, updatedAt, showEur }: Props) {
  const [editing, setEditing] = useState(false);
  const [usd, setUsd] = useState('');
  const [eur, setEur] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const age = updatedAt ? daysSince(updatedAt) : null;
  const stale = age !== null && age > STALE_DAYS;

  function startEditing() {
    setUsd(toText(usdArs));
    setEur(toText(eurArs));
    setError(null);
    setEditing(true);
  }

  // '' borra la cotización; cualquier otra cosa tiene que ser un número válido.
  function parseRate(text: string): { ok: true; value: number | null } | { ok: false } {
    if (!text.trim()) return { ok: true, value: null };
    const n = parseDecimal(text);
    if (n === null || n <= 0 || n > MAX_RATE) return { ok: false };
    return { ok: true, value: n };
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    const u = parseRate(usd);
    const eu = showEur ? parseRate(eur) : ({ ok: true, value: eurArs } as const);
    if (!u.ok || !eu.ok) {
      setError('Ingresá una cotización mayor a 0 (por ejemplo 1450,50).');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await saveInvestmentSettings({
        fx_usd_ars: u.value,
        ...(showEur && { fx_eur_ars: eu.value }),
      });
      setEditing(false);
    } catch (err) {
      setError(apiErrorMessage(err, 'No se pudo guardar la cotización'));
    } finally {
      setSaving(false);
    }
  }

  if (editing) {
    return (
      <form onSubmit={handleSave} className="space-y-3" data-testid="fx-form">
        <div className={`grid gap-3 ${showEur ? 'grid-cols-2' : 'grid-cols-1'}`}>
          <div>
            <label htmlFor="fx-usd" className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">
              Dólar (ARS por US$ 1)
            </label>
            <input
              id="fx-usd"
              value={usd}
              onChange={(e) => setUsd(e.target.value)}
              inputMode="decimal"
              className={inputCls}
              placeholder="1450,50"
              autoFocus
            />
          </div>
          {showEur && (
            <div>
              <label htmlFor="fx-eur" className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">
                Euro (ARS por € 1)
              </label>
              <input
                id="fx-eur"
                value={eur}
                onChange={(e) => setEur(e.target.value)}
                inputMode="decimal"
                className={inputCls}
                placeholder="1600,00"
              />
            </div>
          )}
        </div>
        <p className="text-xs text-gray-400 dark:text-slate-500">
          Dejalo vacío para borrarla. USDT se toma 1 a 1 con el dólar.
        </p>
        {error && <p role="alert" className="text-xs text-red-500">{error}</p>}
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={() => setEditing(false)}
            className="rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700/50"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={saving}
            className="rounded-lg bg-brand-charcoal px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-charcoal-hover disabled:opacity-50"
          >
            {saving ? 'Guardando…' : 'Guardar'}
          </button>
        </div>
      </form>
    );
  }

  return (
    <div className="flex items-start justify-between gap-3">
      <div className="space-y-0.5 text-sm text-gray-700 dark:text-slate-200">
        <p>
          Dólar:{' '}
          {usdArs === null ? (
            <span className="text-gray-400 dark:text-slate-500">sin cargar</span>
          ) : (
            <span className="font-semibold">{formatMoney(usdArs)}</span>
          )}
          {showEur && (
            <>
              {' · Euro: '}
              {eurArs === null ? (
                <span className="text-gray-400 dark:text-slate-500">sin cargar</span>
              ) : (
                <span className="font-semibold">{formatMoney(eurArs)}</span>
              )}
            </>
          )}
        </p>
        {age !== null && (
          <p className={`text-xs ${stale ? 'text-amber-600 dark:text-amber-400' : 'text-gray-400 dark:text-slate-500'}`}>
            Actualizada {ageLabel(age)}
            {stale ? ' · conviene actualizarla' : ''}
          </p>
        )}
      </div>
      <button
        type="button"
        onClick={startEditing}
        aria-label="Editar cotización"
        className="flex shrink-0 items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-brand-indigo hover:bg-gray-100 dark:hover:bg-slate-700"
      >
        <Pencil size={12} />
        {usdArs === null ? 'Cargar' : 'Editar'}
      </button>
    </div>
  );
}
