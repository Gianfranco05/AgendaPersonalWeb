import { useState } from 'react';
import { Trash2 } from 'lucide-react';
import { useVehicleRecords, addRecord, removeRecord } from '../../hooks/useVehicle';
import type { MaintenanceRecordType } from '../../types';
import { toLocalDateString } from '../../utils/date';

interface Props {
  vehicleId: string;
}

const TYPE_LABELS: Record<MaintenanceRecordType, string> = {
  combustible: 'Combustible',
  revision: 'Revisión',
  itv: 'ITV',
  gasto: 'Gasto',
};

const TYPE_ICONS: Record<MaintenanceRecordType, string> = {
  combustible: '⛽',
  revision: '🔧',
  itv: '📋',
  gasto: '💸',
};

function today(): string {
  return toLocalDateString();
}

export default function MaintenanceRecords({ vehicleId }: Props) {
  const { data: records, isLoading } = useVehicleRecords(vehicleId);
  const [recordType, setRecordType] = useState<MaintenanceRecordType>('combustible');
  const [date, setDate] = useState(today());
  const [cost, setCost] = useState('');
  const [odometer, setOdometer] = useState('');
  const [saving, setSaving] = useState(false);

  const canSubmit = date.trim().length > 0;

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setSaving(true);
    try {
      await addRecord({
        vehicle_id: vehicleId,
        record_type: recordType,
        record_date: date,
        cost: cost.trim() ? Number(cost) : null,
        odometer_km: odometer.trim() ? Number(odometer) : null,
      });
      setCost('');
      setOdometer('');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('¿Borrar este registro?')) return;
    await removeRecord(id, vehicleId);
  }

  return (
    <div className="mt-3 rounded-lg bg-gray-50 dark:bg-slate-900/40 p-4">
      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-slate-400">
        Historial de mantenimiento
      </h4>

      {isLoading ? (
        <p className="text-xs text-gray-500 dark:text-slate-400">Cargando…</p>
      ) : (records ?? []).length === 0 ? (
        <p className="mb-2 text-xs text-gray-500 dark:text-slate-400">Todavía no hay registros.</p>
      ) : (
        <ul className="mb-3 space-y-1.5">
          {(records ?? []).map((r) => (
            <li key={r.id} id={`item-${r.id}`} className="flex items-center justify-between gap-2 rounded py-0.5">
              <div className="flex min-w-0 flex-1 items-center gap-2">
                <span className="text-base">{TYPE_ICONS[r.record_type]}</span>
                <div className="min-w-0">
                  <p className="truncate text-sm text-gray-700 dark:text-slate-200">
                    {TYPE_LABELS[r.record_type]}
                  </p>
                  <p className="text-[11px] text-gray-500 dark:text-slate-400">{r.record_date}</p>
                </div>
              </div>
              {r.cost != null ? (
                <span className="shrink-0 text-sm font-semibold text-gray-800 dark:text-slate-100">
                  ${r.cost.toLocaleString('es-AR')}
                </span>
              ) : null}
              <button
                onClick={() => handleDelete(r.id)}
                className="shrink-0 rounded-lg p-1 text-gray-400 dark:text-slate-500 transition-colors hover:bg-rose-50 hover:text-rose-500"
                title="Borrar registro"
              >
                <Trash2 size={14} />
              </button>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={handleAdd} className="space-y-2">
        <div className="flex flex-wrap gap-2">
          {(Object.keys(TYPE_LABELS) as MaintenanceRecordType[]).map((opt) => (
            <button
              type="button"
              key={opt}
              onClick={() => setRecordType(opt)}
              className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                recordType === opt
                  ? 'bg-brand-vehicle text-white'
                  : 'bg-white dark:bg-slate-800 text-gray-600 dark:text-slate-300 border border-gray-200 dark:border-slate-700'
              }`}
            >
              {TYPE_ICONS[opt]} {TYPE_LABELS[opt]}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="h-9 rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 text-sm text-gray-700 dark:text-slate-200 focus:border-brand-vehicle focus:outline-none focus:ring-1 focus:ring-brand-vehicle"
          />
          <input
            type="number"
            min="0"
            step="0.01"
            value={cost}
            onChange={(e) => setCost(e.target.value)}
            placeholder="Costo"
            className="h-9 w-24 rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 text-sm text-gray-700 dark:text-slate-200 focus:border-brand-vehicle focus:outline-none focus:ring-1 focus:ring-brand-vehicle"
          />
          <input
            type="number"
            min="0"
            value={odometer}
            onChange={(e) => setOdometer(e.target.value)}
            placeholder="Km"
            className="h-9 w-24 rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 text-sm text-gray-700 dark:text-slate-200 focus:border-brand-vehicle focus:outline-none focus:ring-1 focus:ring-brand-vehicle"
          />
          <button
            type="submit"
            disabled={saving || !canSubmit}
            className="h-9 rounded-lg bg-brand-vehicle px-3 text-sm font-medium text-white transition-colors hover:opacity-90 disabled:opacity-50"
          >
            Agregar
          </button>
        </div>
      </form>
    </div>
  );
}
