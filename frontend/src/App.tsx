import { useEffect, lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import { ErrorBoundary } from './components/ErrorBoundary';
import { ThemeProvider } from './context/ThemeContext';
import { LoadingSkeleton } from './components/LoadingSkeleton';
import DashboardPage from './pages/Dashboard/DashboardPage';
import GoalsPage from './pages/Goals/GoalsPage';
import SettingsPage from './pages/Settings/SettingsPage';
import RegisterPage from './pages/Auth/RegisterPage';
import LoginPage from './features/auth/LoginPage';
import { useAuthStore } from './store/authStore';

const FinancePage = lazy(() => import('./pages/Finance/FinancePage'));
const NotesPage = lazy(() => import('./pages/Notes/NotesPage'));
const KanbanBoard = lazy(() => import('./pages/Tasks/KanbanBoard'));
const EventsPage = lazy(() => import('./pages/Events/EventsPage'));
const FitnessPage = lazy(() => import('./pages/Fitness/FitnessPage'));
const NutritionPage = lazy(() => import('./pages/Nutrition/NutritionPage'));
const HabitsPage = lazy(() => import('./pages/Habits/HabitsPage'));

export default function App() {
  const checkAuth = useAuthStore((s) => s.checkAuth);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return (
    <ErrorBoundary>
      <ThemeProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route element={<ProtectedRoute />}>
              <Route element={<Layout />}>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/finances" element={<Suspense fallback={<LoadingSkeleton type="page" />}><FinancePage /></Suspense>} />
                <Route path="/events" element={<Suspense fallback={<LoadingSkeleton type="page" />}><EventsPage /></Suspense>} />
                <Route path="/goals" element={<GoalsPage />} />
                <Route path="/fitness" element={<Suspense fallback={<LoadingSkeleton type="page" />}><FitnessPage /></Suspense>} />
                <Route path="/nutrition" element={<Suspense fallback={<LoadingSkeleton type="page" />}><NutritionPage /></Suspense>} />
                <Route path="/habits" element={<Suspense fallback={<LoadingSkeleton type="page" />}><HabitsPage /></Suspense>} />
                <Route path="/notes" element={<Suspense fallback={<LoadingSkeleton type="page" />}><NotesPage /></Suspense>} />
                <Route path="/tasks" element={<Suspense fallback={<LoadingSkeleton type="page" />}><KanbanBoard /></Suspense>} />
                <Route path="/settings" element={<SettingsPage />} />
              </Route>
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </ThemeProvider>
    </ErrorBoundary>
  );
}
