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
import GoogleCallbackPage from './pages/Auth/GoogleCallbackPage';
import LoginPage from './features/auth/LoginPage';
import { useAuthStore } from './store/authStore';

const FinancePage = lazy(() => import('./pages/Finance/FinancePage'));
const NotesPage = lazy(() => import('./pages/Notes/NotesPage'));
const KanbanBoard = lazy(() => import('./pages/Tasks/KanbanBoard'));
const EventsPage = lazy(() => import('./pages/Events/EventsPage'));
const FitnessPage = lazy(() => import('./pages/Fitness/FitnessPage'));
const NutritionPage = lazy(() => import('./pages/Nutrition/NutritionPage'));
const HabitsPage = lazy(() => import('./pages/Habits/HabitsPage'));
const TermsPage = lazy(() => import('./pages/Legal/TermsPage'));
const PrivacyPage = lazy(() => import('./pages/Legal/PrivacyPage'));
const ModulesPage = lazy(() => import('./pages/Modules/ModulesPage'));
const StorePage = lazy(() => import('./pages/Store/StorePage'));
const AcceptTermsPage = lazy(() => import('./pages/Legal/AcceptTermsPage'));

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
            <Route path="/auth/google/callback" element={<GoogleCallbackPage />} />
            {/* Públicas: tienen que ser accesibles antes de registrarse, ya que
                el registro remite a ellas. */}
            <Route path="/terms" element={<Suspense fallback={<LoadingSkeleton type="page" />}><TermsPage /></Suspense>} />
            <Route path="/privacy" element={<Suspense fallback={<LoadingSkeleton type="page" />}><PrivacyPage /></Suspense>} />
            {/* Requiere sesión iniciada, pero sin pasar por el gate de términos
                (evita el loop de redirección contra sí misma). */}
            <Route element={<ProtectedRoute skipTermsGate />}>
              <Route
                path="/accept-terms"
                element={<Suspense fallback={<LoadingSkeleton type="page" />}><AcceptTermsPage /></Suspense>}
              />
            </Route>
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
                <Route path="/modules" element={<Suspense fallback={<LoadingSkeleton type="page" />}><ModulesPage /></Suspense>} />
                <Route path="/store" element={<Suspense fallback={<LoadingSkeleton type="page" />}><StorePage /></Suspense>} />
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
