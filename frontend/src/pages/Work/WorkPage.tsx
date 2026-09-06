import { useState } from 'react';
import { Plus, Briefcase, Users, Award } from 'lucide-react';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import ModuleLockedNotice, { isPaymentRequiredError } from '../../components/ModuleLockedNotice';
import { useOpportunities, useWorkSummary, removeOpportunity } from '../../hooks/useWork';
import type { OpportunityStatus, WorkOpportunity } from '../../types';
import OpportunityForm from './OpportunityForm';
import OpportunityCard from './OpportunityCard';

const COLUMNS: { key: OpportunityStatus; label: string }[] = [
  { key: 'aplicado', label: 'Aplicado' },
  { key: 'entrevista', label: 'Entrevista' },
  { key: 'oferta', label: 'Oferta' },
  { key: 'aceptado', label: 'Aceptado' },
  { key: 'rechazado', label: 'Rechazado' },
];

export default function WorkPage() {
  const [modal, setModal] = useState<{ open: boolean; opportunity: WorkOpportunity | null }>({
    open: false,
    opportunity: null,
  });

  const { data: opportunities, isLoading: oppsLoading, error: oppsError } = useOpportunities();
  const { data: summary, isLoading: summaryLoading } = useWorkSummary();

  if (isPaymentRequiredError(oppsError)) {
    return <ModuleLockedNotice moduleName="Trabajo y Carrera" />;
  }

  async function handleDelete(opportunity: WorkOpportunity) {
    if (!confirm(`¿Borrar "${opportunity.company} — ${opportunity.role}"?`)) return;
    await removeOpportunity(opportunity.id);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-800 dark:text-slate-100">Trabajo y Carrera</h2>
        <button
          onClick={() => setModal({ open: true, opportunity: null })}
          className="flex items-center gap-2 rounded-lg bg-brand-work px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90"
        >
          <Plus size={16} />
          Nueva oportunidad
        </button>
      </div>

      {summaryLoading && !summary ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <LoadingSkeleton type="card" />
          <LoadingSkeleton type="card" />
          <LoadingSkeleton type="card" />
        </div>
      ) : summary ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
              <Briefcase size={16} className="text-brand-work" />
              Activas
            </div>
            <p className="mt-1 text-2xl font-bold text-brand-work">{summary.active}</p>
          </div>
          <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
              <Users size={16} className="text-indigo-500" />
              Entrevista
            </div>
            <p className="mt-1 text-2xl font-bold text-indigo-500">{summary.entrevista}</p>
          </div>
          <div className="rounded-xl bg-white dark:bg-slate-800 p-5 shadow-sm">
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
              <Award size={16} className="text-emerald-500" />
              Aceptadas
            </div>
            <p className="mt-1 text-2xl font-bold text-emerald-500">{summary.aceptado}</p>
          </div>
        </div>
      ) : null}

      {oppsLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {[1, 2, 3, 4, 5].map((i) => (
            <LoadingSkeleton key={i} type="widget" />
          ))}
        </div>
      ) : (opportunities ?? []).length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl bg-white dark:bg-slate-800 p-12 shadow-sm">
          <Briefcase size={48} className="text-gray-300 dark:text-slate-600" />
          <p className="text-sm text-gray-500 dark:text-slate-400">Todavía no cargaste ninguna oportunidad</p>
          <button
            onClick={() => setModal({ open: true, opportunity: null })}
            className="flex items-center gap-2 rounded-lg bg-brand-work px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90"
          >
            <Plus size={16} />
            Agregar oportunidad
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {COLUMNS.map((column) => {
            const items = (opportunities ?? []).filter((o) => o.status === column.key);
            return (
              <div key={column.key} className="space-y-3">
                <h3 className="flex items-center justify-between text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-slate-400">
                  {column.label}
                  <span className="rounded-full bg-gray-100 px-1.5 py-0.5 text-[10px] dark:bg-slate-700">
                    {items.length}
                  </span>
                </h3>
                <div className="space-y-3">
                  {items.map((o) => (
                    <OpportunityCard
                      key={o.id}
                      opportunity={o}
                      onEdit={(op) => setModal({ open: true, opportunity: op })}
                      onDelete={handleDelete}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {modal.open && (
        <OpportunityForm
          opportunity={modal.opportunity}
          onClose={() => setModal({ open: false, opportunity: null })}
          onSaved={() => setModal({ open: false, opportunity: null })}
        />
      )}
    </div>
  );
}
