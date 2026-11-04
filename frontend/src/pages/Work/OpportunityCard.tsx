import { Pencil, Trash2 } from 'lucide-react';
import type { WorkOpportunity } from '../../types';

interface Props {
  opportunity: WorkOpportunity;
  onEdit: (opportunity: WorkOpportunity) => void;
  onDelete: (opportunity: WorkOpportunity) => void;
}

function formatMoney(value: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS', maximumFractionDigits: 0 }).format(
    value,
  );
}

export default function OpportunityCard({ opportunity, onEdit, onDelete }: Props) {
  return (
    <div className="rounded-xl bg-white dark:bg-slate-800 p-4 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h4 className="truncate text-sm font-medium text-gray-800 dark:text-slate-100">{opportunity.role}</h4>
          <p className="truncate text-xs text-gray-500 dark:text-slate-400">{opportunity.company}</p>
        </div>
        <div className="flex shrink-0 gap-1">
          <button
            onClick={() => onEdit(opportunity)}
            className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 transition-colors hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-brand-work"
            title="Editar"
          >
            <Pencil size={13} />
          </button>
          <button
            onClick={() => onDelete(opportunity)}
            className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 transition-colors hover:bg-rose-50 hover:text-rose-500"
            title="Eliminar"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>
      {opportunity.salary != null && (
        <p className="mt-2 text-xs font-medium text-gray-500 dark:text-slate-400">{formatMoney(opportunity.salary)}</p>
      )}
    </div>
  );
}
