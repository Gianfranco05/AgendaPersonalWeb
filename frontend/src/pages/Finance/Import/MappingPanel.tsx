import { useState } from 'react';
import type { ImportMapping, ImportPreview } from '../../../types';

interface Props {
  preview: ImportPreview;
  busy: boolean;
  onApply: (update: { header_row?: number; mapping?: ImportMapping }) => void;
}

const selectCls =
  'w-full rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1.5 text-sm';
const labelCls = 'mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400';

function ColumnSelect({
  id,
  label,
  value,
  headers,
  onChange,
  optional = true,
}: {
  id: string;
  label: string;
  value: number | null;
  headers: string[];
  onChange: (v: number | null) => void;
  optional?: boolean;
}) {
  return (
    <div>
      <label htmlFor={id} className={labelCls}>{label}</label>
      <select
        id={id}
        className={selectCls}
        value={value === null ? '' : String(value)}
        onChange={(e) => onChange(e.target.value === '' ? null : Number(e.target.value))}
      >
        <option value="">{optional ? '— ninguna —' : 'Elegí una columna'}</option>
        {headers.map((h, i) => (
          <option key={i} value={i}>{`${i + 1}. ${h || '(sin nombre)'}`}</option>
        ))}
      </select>
    </div>
  );
}

/** Editor de columnas: fila de encabezado, qué columna es cada campo, formato de
 *  fecha, separador decimal, signo y moneda por defecto. */
export default function MappingPanel({ preview, busy, onApply }: Props) {
  const [mapping, setMapping] = useState<ImportMapping>(preview.mapping);
  const [headerRow, setHeaderRow] = useState(preview.header_row);
  const headers = preview.headers;

  const set = <K extends keyof ImportMapping>(key: K, value: ImportMapping[K]) =>
    setMapping((m) => ({ ...m, [key]: value }));

  return (
    <div className="space-y-4 rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <div>
          <label htmlFor="map-header-row" className={labelCls}>Fila de encabezado</label>
          <input
            id="map-header-row"
            type="number"
            min={1}
            className={selectCls}
            value={headerRow + 1}
            onChange={(e) => setHeaderRow(Math.max(0, Number(e.target.value) - 1))}
          />
        </div>
        <ColumnSelect id="map-date" label="Columna de fecha" value={mapping.date} headers={headers} optional={false} onChange={(v) => set('date', v)} />
        <ColumnSelect
          id="map-desc"
          label="Columna de descripción"
          value={mapping.description[0] ?? null}
          headers={headers}
          onChange={(v) => set('description', v === null ? [] : [v])}
        />
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <div>
          <label htmlFor="map-mode" className={labelCls}>Cómo viene el monto</label>
          <select
            id="map-mode"
            className={selectCls}
            value={mapping.amount_mode}
            onChange={(e) => set('amount_mode', e.target.value as ImportMapping['amount_mode'])}
          >
            <option value="signed">Una columna con signo (egresos negativos)</option>
            <option value="debit_credit">Columnas de débito y crédito</option>
          </select>
        </div>
        {mapping.amount_mode === 'signed' ? (
          <ColumnSelect id="map-amount" label="Columna de monto" value={mapping.amount} headers={headers} optional={false} onChange={(v) => set('amount', v)} />
        ) : (
          <>
            <ColumnSelect id="map-debit" label="Columna de débito" value={mapping.debit} headers={headers} onChange={(v) => set('debit', v)} />
            <ColumnSelect id="map-credit" label="Columna de crédito" value={mapping.credit} headers={headers} onChange={(v) => set('credit', v)} />
          </>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-4">
        <div>
          <label htmlFor="map-datefmt" className={labelCls}>Formato de fecha</label>
          <select id="map-datefmt" className={selectCls} value={mapping.date_format} onChange={(e) => set('date_format', e.target.value as ImportMapping['date_format'])}>
            <option value="auto">Detectar</option>
            <option value="dd/mm/yyyy">día/mes/año</option>
            <option value="mm/dd/yyyy">mes/día/año</option>
            <option value="yyyy-mm-dd">año-mes-día</option>
          </select>
        </div>
        <div>
          <label htmlFor="map-decimal" className={labelCls}>Separador decimal</label>
          <select id="map-decimal" className={selectCls} value={mapping.decimal_separator} onChange={(e) => set('decimal_separator', e.target.value as ImportMapping['decimal_separator'])}>
            <option value="auto">Detectar</option>
            <option value=",">Coma (1.234,56)</option>
            <option value=".">Punto (1,234.56)</option>
          </select>
        </div>
        <div>
          <label htmlFor="map-currency" className={labelCls}>Moneda por defecto</label>
          <select id="map-currency" className={selectCls} value={mapping.default_currency} onChange={(e) => set('default_currency', e.target.value)}>
            {['ARS', 'USD', 'EUR', 'BRL', 'UYU', 'CLP'].map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <label className="flex items-end gap-2 pb-2 text-sm text-gray-700 dark:text-slate-200">
          <input type="checkbox" checked={mapping.invert_sign} onChange={(e) => set('invert_sign', e.target.checked)} />
          Invertir signo
        </label>
      </div>

      <div className="flex items-center justify-between gap-2">
        <p className="text-xs text-gray-400 dark:text-slate-500">
          Cuando confirmes, la app recuerda estas columnas para tus próximos archivos con el mismo formato.
        </p>
        <button
          type="button"
          disabled={busy}
          onClick={() => onApply({ header_row: headerRow, mapping })}
          className="shrink-0 rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white hover:bg-brand-charcoal-hover disabled:opacity-50"
        >
          Aplicar columnas
        </button>
      </div>
    </div>
  );
}
