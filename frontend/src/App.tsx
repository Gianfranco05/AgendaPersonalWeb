import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import { ErrorBoundary } from './components/ErrorBoundary';
import DashboardPage from './pages/Dashboard/DashboardPage';
import FinancePage from './pages/Finance/FinancePage';
import NotesPage from './pages/Notes/NotesPage';
import KanbanBoard from './pages/Tasks/KanbanBoard';
import LoginPage from './features/auth/LoginPage';
import { useAuthStore } from './store/authStore';

export default function App() {
  const checkAuth = useAuthStore((s) => s.checkAuth);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/finances" element={<FinancePage />} />
              <Route path="/notes" element={<NotesPage />} />
              <Route path="/tasks" element={<KanbanBoard />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
