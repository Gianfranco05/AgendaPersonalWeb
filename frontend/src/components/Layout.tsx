import { useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, PiggyBank, StickyNote, ListTodo, Calendar, Target, Settings, Menu, X, LogOut, Dumbbell, Apple, Repeat, Sun, Moon, LayoutGrid, Timer } from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import { useTheme } from '../context/ThemeContext';

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/finances', label: 'Finanzas', icon: PiggyBank },
  { to: '/events', label: 'Eventos', icon: Calendar },
  { to: '/goals', label: 'Metas', icon: Target },
  { to: '/fitness', label: 'Fitness', icon: Dumbbell },
  { to: '/nutrition', label: 'Nutrición', icon: Apple },
  { to: '/habits', label: 'Hábitos', icon: Repeat },
  { to: '/focus', label: 'Enfoque', icon: Timer },
  { to: '/notes', label: 'Notas', icon: StickyNote },
  { to: '/tasks', label: 'Tareas', icon: ListTodo },
  { to: '/modules', label: 'Módulos', icon: LayoutGrid },
  { to: '/settings', label: 'Configuración', icon: Settings },
];

export default function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { user, logout } = useAuthStore();
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();

  async function handleLogout() {
    await logout();
    navigate('/login', { replace: true });
  }

  const initials = user?.full_name
    ? user.full_name
        .split(' ')
        .slice(0, 2)
        .map((w) => w[0])
        .join('')
        .toUpperCase()
    : 'U';

  return (
    <div className="flex h-screen bg-brand-surface text-gray-900 dark:text-slate-100">
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        className={`
          fixed inset-y-0 left-0 z-50 w-64 transform bg-brand-charcoal text-white transition-transform duration-200 ease-in-out
          lg:static lg:translate-x-0
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        <div className="flex h-16 items-center justify-between px-6">
          <h1 className="text-xl font-bold tracking-tight">Vida Personal</h1>
          <button
            onClick={() => setMobileOpen(false)}
            className="rounded-lg p-1 hover:bg-white/20 lg:hidden"
            aria-label="Cerrar menú"
          >
            <X size={20} />
          </button>
        </div>

        <nav className="mt-4 space-y-1 px-3">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) =>
                `relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${
                  isActive
                    ? 'bg-white/10 font-semibold text-white before:absolute before:left-0 before:top-1/2 before:h-5 before:w-[3px] before:-translate-y-1/2 before:rounded-full before:bg-brand-indigo'
                    : 'font-medium text-white/80 hover:bg-white/10 hover:text-white'
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="absolute bottom-0 left-0 right-0 border-t border-white/20 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 min-w-0">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/20 text-xs font-semibold">
                {initials}
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{user?.full_name ?? 'Usuario'}</p>
                <p className="truncate text-xs text-white/60">{user?.email ?? ''}</p>
              </div>
            </div>
            <div className="ml-2 flex shrink-0 items-center gap-1">
              <button
                onClick={toggle}
                className="rounded-lg p-1.5 text-white/70 hover:bg-white/20 hover:text-white"
                title={theme === 'dark' ? 'Modo claro' : 'Modo oscuro'}
                aria-label="Cambiar tema"
              >
                {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
              </button>
              <button
                onClick={handleLogout}
                className="rounded-lg p-1.5 text-white/70 hover:bg-white/20 hover:text-white"
                title="Cerrar sesión"
              >
                <LogOut size={16} />
              </button>
            </div>
          </div>
        </div>
      </aside>

      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-16 items-center gap-4 border-b border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 lg:hidden">
          <button
            onClick={() => setMobileOpen(true)}
            className="rounded-lg p-1 text-gray-600 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-700"
            aria-label="Abrir menú"
          >
            <Menu size={20} />
          </button>
          <h1 className="text-lg font-bold text-brand-charcoal dark:text-slate-100">Vida Personal</h1>
        </header>

        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          {/* key por ruta: re-monta el wrapper y dispara la animación de entrada.
              Solo opacidad: un transform aquí crearía un containing block y los
              modales `fixed` quedarían atrapados dentro del área scrolleable. */}
          <div key={location.pathname} className="animate-fade-in">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
