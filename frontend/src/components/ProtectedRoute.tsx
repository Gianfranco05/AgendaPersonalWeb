import { Navigate, Outlet } from 'react-router-dom';
import { CURRENT_TERMS_VERSION, useAuthStore } from '../store/authStore';

interface ProtectedRouteProps {
  // /accept-terms también requiere sesión iniciada, pero no puede pasar por
  // su propio gate — eso generaría un loop de redirección.
  skipTermsGate?: boolean;
}

export default function ProtectedRoute({ skipTermsGate = false }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, user } = useAuthStore();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-brand-surface">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-indigo border-t-transparent" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (!skipTermsGate && user && user.terms_accepted_version !== CURRENT_TERMS_VERSION) {
    return <Navigate to="/accept-terms" replace />;
  }

  return <Outlet />;
}
