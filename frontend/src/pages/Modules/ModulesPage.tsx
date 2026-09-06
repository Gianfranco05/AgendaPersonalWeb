import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  CheckCircle2,
  ListTodo,
  StickyNote,
  PiggyBank,
  Dumbbell,
  Calendar,
  GraduationCap,
  BookOpen,
  Film,
  Briefcase,
  Plane,
  Car,
  KanbanSquare,
  Lock,
  ShoppingBag,
  Package,
} from 'lucide-react';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import { useModules, toggleModuleVisibility } from '../../hooks/useModules';
import type { ModuleInfo } from '../../types';

const ICONS: Record<string, typeof Package> = {
  habits: CheckCircle2,
  tasks: ListTodo,
  notes: StickyNote,
  finance: PiggyBank,
  fitness_nutrition: Dumbbell,
  calendar: Calendar,
  study: GraduationCap,
  library: BookOpen,
  media: Film,
  work: Briefcase,
  travel: Plane,
  vehicle: Car,
  projects: KanbanSquare,
};

// Ruta de cada plantilla comprada. Estas páginas se agregan en un batch
// posterior de este mismo proyecto: el link queda armado igual, aunque hoy
// no exista la ruta (React Router simplemente no matchea y no rompe nada).
const MODULE_ROUTES: Record<string, string> = {
  study: '/study',
  library: '/library',
  media: '/media',
  work: '/work',
  travel: '/travel',
  vehicle: '/vehicle',
  projects: '/projects',
};

function ModuleIcon({ moduleKey, className }: { moduleKey: string; className?: string }) {
  const Icon = ICONS[moduleKey] ?? Package;
  return <Icon className={className} />;
}

function Toggle({
  checked,
  disabled,
  onChange,
}: {
  checked: boolean;
  disabled?: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
        checked ? 'bg-brand-indigo' : 'bg-gray-300 dark:bg-slate-600'
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
          checked ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  );
}

function BaseModuleTile({ module }: { module: ModuleInfo }) {
  return (
    <div className="flex items-center gap-3 rounded-xl bg-white dark:bg-slate-800 p-4 shadow-sm">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-indigo/10 text-brand-indigo">
        <ModuleIcon moduleKey={module.key} className="h-5 w-5" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-gray-800 dark:text-slate-100">{module.label}</p>
        <p className="truncate text-xs text-gray-500 dark:text-slate-400">{module.description}</p>
      </div>
      <span className="shrink-0 rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-medium text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300">
        Incluida
      </span>
    </div>
  );
}

function OwnedModuleTile({
  module,
  busy,
  onToggle,
}: {
  module: ModuleInfo;
  busy: boolean;
  onToggle: (enabled: boolean) => void;
}) {
  const route = MODULE_ROUTES[module.key];
  const content = (
    <>
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-indigo/10 text-brand-indigo">
        <ModuleIcon moduleKey={module.key} className="h-5 w-5" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-gray-800 dark:text-slate-100">{module.label}</p>
        <p className="truncate text-xs text-gray-500 dark:text-slate-400">{module.description}</p>
      </div>
    </>
  );

  return (
    <div className="flex items-center gap-3 rounded-xl bg-white dark:bg-slate-800 p-4 shadow-sm">
      {route ? (
        <Link to={route} className="flex min-w-0 flex-1 items-center gap-3">
          {content}
        </Link>
      ) : (
        <div className="flex min-w-0 flex-1 items-center gap-3">{content}</div>
      )}
      <Toggle checked={module.enabled} disabled={busy} onChange={onToggle} />
    </div>
  );
}

function LockedModuleTile({ module }: { module: ModuleInfo }) {
  return (
    <Link
      to="/store"
      className="flex items-center gap-3 rounded-xl border border-dashed border-gray-300 dark:border-slate-600 bg-white/60 dark:bg-slate-800/60 p-4 transition-colors hover:border-brand-indigo"
    >
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-gray-100 dark:bg-slate-700 text-gray-400 dark:text-slate-500">
        <ModuleIcon moduleKey={module.key} className="h-5 w-5" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-gray-600 dark:text-slate-300">{module.label}</p>
        <p className="truncate text-xs text-gray-400 dark:text-slate-500">{module.description}</p>
      </div>
      <span className="flex shrink-0 items-center gap-1 text-xs font-medium text-gray-400 dark:text-slate-500">
        <Lock className="h-3.5 w-3.5" />
        Ver en la tienda
      </span>
    </Link>
  );
}

export default function ModulesPage() {
  const { data: modules, isLoading } = useModules();
  const [busyKey, setBusyKey] = useState<string | null>(null);

  async function handleToggle(module: ModuleInfo, enabled: boolean) {
    setBusyKey(module.key);
    try {
      await toggleModuleVisibility(module.key, enabled);
    } finally {
      setBusyKey(null);
    }
  }

  const baseModules = modules?.filter((m) => m.is_base) ?? [];
  const ownedPaidModules = modules?.filter((m) => !m.is_base && m.owned) ?? [];
  const lockedModules = modules?.filter((m) => !m.is_base && !m.owned) ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-800 dark:text-slate-100">Módulos</h2>
          <p className="text-sm text-gray-500 dark:text-slate-400">
            Personalizá qué plantillas aparecen en tu menú.
          </p>
        </div>
        <Link
          to="/store"
          className="flex items-center gap-2 rounded-lg bg-brand-indigo px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-indigo-hover"
        >
          <ShoppingBag size={16} />
          Ir a la tienda
        </Link>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          <LoadingSkeleton type="card" />
          <LoadingSkeleton type="card" />
        </div>
      ) : (
        <>
          <section className="space-y-3">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-slate-400">
              Incluidas
            </h3>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {baseModules.map((m) => (
                <BaseModuleTile key={m.key} module={m} />
              ))}
            </div>
          </section>

          {ownedPaidModules.length > 0 && (
            <section className="space-y-3">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-slate-400">
                Tus plantillas
              </h3>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {ownedPaidModules.map((m) => (
                  <OwnedModuleTile
                    key={m.key}
                    module={m}
                    busy={busyKey === m.key}
                    onToggle={(enabled) => handleToggle(m, enabled)}
                  />
                ))}
              </div>
            </section>
          )}

          {lockedModules.length > 0 && (
            <section className="space-y-3">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-slate-400">
                Más plantillas
              </h3>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {lockedModules.map((m) => (
                  <LockedModuleTile key={m.key} module={m} />
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
