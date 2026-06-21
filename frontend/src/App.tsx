import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import { ErrorBoundary } from './components/ErrorBoundary';
import DashboardPage from './pages/Dashboard/DashboardPage';
import FinancePage from './pages/Finance/FinancePage';
import NotesPage from './pages/Notes/NotesPage';
import KanbanBoard from './pages/Tasks/KanbanBoard';

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/finances" element={<FinancePage />} />
            <Route path="/notes" element={<NotesPage />} />
            <Route path="/tasks" element={<KanbanBoard />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
