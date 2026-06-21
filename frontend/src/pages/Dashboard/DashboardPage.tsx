import { ErrorBoundary } from '../../components/ErrorBoundary';
import FinanceWidget from './FinanceWidget';
import NotesWidget from './NotesWidget';
import TasksWidget from './TasksWidget';
import EventsWidget from './EventsWidget';

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-800">Dashboard</h2>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
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

        {/* Row 2: Notes full width or span 2 */}
        <div className="md:col-span-2 xl:col-span-4">
          <ErrorBoundary>
            <NotesWidget />
          </ErrorBoundary>
        </div>
      </div>
    </div>
  );
}
