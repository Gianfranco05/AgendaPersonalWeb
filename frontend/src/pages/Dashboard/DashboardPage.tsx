import { ErrorBoundary } from '../../components/ErrorBoundary';
import FinanceWidget from './FinanceWidget';
import NotesWidget from './NotesWidget';
import TasksWidget from './TasksWidget';
import EventsWidget from './EventsWidget';
import InfraWidget from './InfraWidget';
import HabitsWidget from './HabitsWidget';

// El widget apaga la Dream Machine de la casa del dueño: solo tiene sentido en
// una instancia propia con infra_config.yaml. En el SaaS se le mostraba a todos
// los usuarios un botón rojo de "Apagar Dream Machine" que no les corresponde.
const SHOW_INFRA = import.meta.env.VITE_INFRA_WIDGET_ENABLED === 'true';

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-800 dark:text-slate-100">Dashboard</h2>

      <div className="stagger-children grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
        {/* Row 1: Finance (span 2) + Events (span 1) + Tasks (span 1) */}
        <div className="md:col-span-2 xl:col-span-2">
          <ErrorBoundary>
            <FinanceWidget />
          </ErrorBoundary>
        </div>
        <div className="md:col-span-1">
          <ErrorBoundary>
            <EventsWidget />
          </ErrorBoundary>
        </div>
        <div className="md:col-span-1">
          <ErrorBoundary>
            <TasksWidget />
          </ErrorBoundary>
        </div>

        {/* Row 2: Infra + Habits + Notes */}
        {SHOW_INFRA && (
          <div className="md:col-span-1">
            <ErrorBoundary>
              <InfraWidget />
            </ErrorBoundary>
          </div>
        )}
        <div className={SHOW_INFRA ? 'md:col-span-1' : 'md:col-span-1 xl:col-span-2'}>
          <ErrorBoundary>
            <HabitsWidget />
          </ErrorBoundary>
        </div>
        <div className="md:col-span-2 xl:col-span-2">
          <ErrorBoundary>
            <NotesWidget />
          </ErrorBoundary>
        </div>
      </div>
    </div>
  );
}
