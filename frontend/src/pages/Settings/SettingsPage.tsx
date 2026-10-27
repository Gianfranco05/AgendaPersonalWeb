import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Sun, Moon, Save, Check, Loader2, Calendar, RefreshCw, Unlink, Download, Trash2, AlertTriangle, HelpCircle } from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { useTheme } from '../../context/ThemeContext';
import { useSettings, syncGoogle, disconnectGoogle } from '../../hooks/useSettings';
import { exportMyData, deleteMyAccount } from '../../api/endpoints';
import SessionsSection from './SessionsSection';
import ReminderSection from './ReminderSection';
import { useOnboardingStore } from '../../store/onboardingStore';
import { toLocalDateString } from '../../utils/date';

const inputCls =
  'w-full rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-2 text-sm focus:border-brand-indigo focus:outline-none focus:ring-1 focus:ring-brand-indigo disabled:bg-gray-50 disabled:text-gray-400';

const GOOGLE_ERROR_MESSAGES: Record<string, string> = {
  google_not_configured: 'Google Calendar no está configurado en el servidor.',
  google_denied: 'Acceso a Google Calendar denegado.',
  invalid_state: 'La conexión con Google expiró, probá de nuevo.',
  no_code: 'Google no devolvió un código de autorización.',
  google_exchange_failed: 'No se pudo completar la conexión con Google.',
};

export default function SettingsPage() {
  const { user, updateProfile } = useAuthStore();
  const { theme, toggle } = useTheme();
  const openTutorial = useOnboardingStore((s) => s.openReplay);
  const [displayName, setDisplayName] = useState(user?.full_name ?? '');
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');

  const [searchParams, setSearchParams] = useSearchParams();
  const { data: settings, isLoading: settingsLoading } = useSettings();
  const [googleAction, setGoogleAction] = useState<'idle' | 'syncing' | 'disconnecting'>('idle');
  const [googleMessage, setGoogleMessage] = useState<string | null>(null);

  useEffect(() => {
    const connected = searchParams.get('google');
    const googleError = searchParams.get('google_error');
    if (connected === 'connected') {
      setGoogleMessage('Google Calendar conectado correctamente.');
    } else if (googleError) {
      setGoogleMessage(GOOGLE_ERROR_MESSAGES[googleError] ?? 'Ocurrió un error al conectar Google Calendar.');
    }
    if (connected || googleError) {
      const next = new URLSearchParams(searchParams);
      next.delete('google');
      next.delete('google_error');
      setSearchParams(next, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSyncGoogle() {
    setGoogleAction('syncing');
    setGoogleMessage(null);
    try {
      const result = await syncGoogle();
      setGoogleMessage(`${result.synced} evento(s) sincronizado(s) con Google Calendar.`);
    } catch {
      setGoogleMessage('Error al sincronizar con Google Calendar.');
    } finally {
      setGoogleAction('idle');
    }
  }

  async function handleDisconnectGoogle() {
    setGoogleAction('disconnecting');
    setGoogleMessage(null);
    try {
      await disconnectGoogle();
      setGoogleMessage('Google Calendar desconectado.');
    } catch {
      setGoogleMessage('Error al desconectar Google Calendar.');
    } finally {
      setGoogleAction('idle');
    }
  }

  const [exportState, setExportState] = useState<'idle' | 'working' | 'error'>('idle');
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deletePassword, setDeletePassword] = useState('');
  const [deleteState, setDeleteState] = useState<'idle' | 'working' | 'error'>('idle');
  const [deleteError, setDeleteError] = useState('');

  async function handleExport() {
    setExportState('working');
    try {
      const blob = await exportMyData();
      // Descarga sin navegar: el endpoint requiere la cookie de sesión, así que
      // un <a href> directo tampoco haría daño, pero esto evita perder el estado
      // de la página y funciona igual con el token Bearer del cliente mobile.
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `vida-personal-${toLocalDateString()}.json`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setExportState('idle');
    } catch {
      setExportState('error');
    }
  }

  async function handleDelete(e: React.FormEvent) {
    e.preventDefault();
    if (deleteState === 'working') return;
    setDeleteState('working');
    setDeleteError('');
    try {
      await deleteMyAccount(deletePassword);
      // La cuenta ya no existe: no tiene sentido llamar a logout (su endpoint
      // respondería 401). Se limpia el estado local y se sale a /login.
      useAuthStore.setState({ user: null, isAuthenticated: false });
      window.location.href = '/login';
    } catch (err) {
      setDeleteState('error');
      setDeleteError(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          'No se pudo eliminar la cuenta',
      );
    }
  }

  const dirty = displayName.trim() !== (user?.full_name ?? '');

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!dirty || status === 'saving') return;
    setStatus('saving');
    setErrorMsg('');
    try {
      await updateProfile(displayName.trim());
      setStatus('saved');
      setTimeout(() => setStatus('idle'), 2500);
    } catch (err) {
      setStatus('error');
      setErrorMsg(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          'No se pudieron guardar los cambios',
      );
    }
  }

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <h2 className="text-2xl font-bold text-gray-800 dark:text-slate-100">Configuración</h2>

      <form onSubmit={handleSave} className="space-y-6 rounded-xl bg-white dark:bg-slate-800 p-6 shadow-sm">
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Nombre</label>
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className={inputCls}
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Email</label>
          <input
            type="email"
            value={user?.email ?? ''}
            disabled
            className={inputCls}
          />
          <p className="mt-1 text-xs text-gray-400 dark:text-slate-500">El email no se puede modificar</p>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-slate-400">Tema</label>
          <button
            type="button"
            onClick={toggle}
            className="flex items-center gap-3 rounded-lg border border-gray-200 dark:border-slate-700 px-4 py-3 text-sm text-gray-700 dark:text-slate-200 transition-colors hover:bg-gray-50 dark:hover:bg-slate-700/50"
          >
            {theme === 'light' ? <Sun size={18} /> : <Moon size={18} />}
            <span>{theme === 'light' ? 'Claro' : 'Oscuro'}</span>
          </button>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={!dirty || status === 'saving'}
            className="flex items-center gap-2 rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-charcoal-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            {status === 'saving' ? (
              <Loader2 size={16} className="animate-spin" />
            ) : status === 'saved' ? (
              <Check size={16} />
            ) : (
              <Save size={16} />
            )}
            {status === 'saving' ? 'Guardando…' : status === 'saved' ? 'Guardado' : 'Guardar cambios'}
          </button>
          {status === 'error' && (
            <span className="text-sm text-red-500 dark:text-red-400">{errorMsg}</span>
          )}
        </div>
      </form>

      <div className="space-y-3 rounded-xl bg-white dark:bg-slate-800 p-6 shadow-sm">
        <div className="flex items-center gap-2">
          <HelpCircle size={18} className="text-brand-indigo" />
          <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-200">Ayuda</h3>
        </div>
        <p className="text-sm text-gray-500 dark:text-slate-400">
          Repasá cómo está organizada la app en cuatro pasos.
        </p>
        <button
          type="button"
          onClick={openTutorial}
          className="flex items-center gap-2 rounded-lg border border-gray-200 dark:border-slate-700 px-4 py-2 text-sm text-gray-700 dark:text-slate-200 transition-colors hover:bg-gray-50 dark:hover:bg-slate-700/50"
        >
          Ver tutorial
        </button>
      </div>

      <div className="space-y-4 rounded-xl bg-white dark:bg-slate-800 p-6 shadow-sm">
        <div className="flex items-center gap-2">
          <Calendar size={18} className="text-brand-indigo" />
          <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-200">Google Calendar</h3>
        </div>

        {googleMessage && (
          <p className="rounded-lg bg-gray-50 dark:bg-slate-700/50 px-3 py-2 text-xs text-gray-600 dark:text-slate-300">
            {googleMessage}
          </p>
        )}

        {settingsLoading ? (
          <p className="text-sm text-gray-400 dark:text-slate-500">Cargando…</p>
        ) : settings?.google_connected ? (
          <div className="space-y-3">
            <p className="text-sm text-emerald-600 dark:text-emerald-400">Conectado</p>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={handleSyncGoogle}
                disabled={googleAction !== 'idle'}
                className="flex items-center gap-2 rounded-lg border border-gray-200 dark:border-slate-700 px-4 py-2 text-sm text-gray-700 dark:text-slate-200 transition-colors hover:bg-gray-50 dark:hover:bg-slate-700/50 disabled:opacity-50"
              >
                <RefreshCw size={16} className={googleAction === 'syncing' ? 'animate-spin' : ''} />
                Sincronizar ahora
              </button>
              <button
                type="button"
                onClick={handleDisconnectGoogle}
                disabled={googleAction !== 'idle'}
                className="flex items-center gap-2 rounded-lg border border-gray-200 dark:border-slate-700 px-4 py-2 text-sm text-rose-500 transition-colors hover:bg-rose-50 disabled:opacity-50"
              >
                <Unlink size={16} />
                Desconectar
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-gray-500 dark:text-slate-400">No conectado</p>
            <a
              href="/ajustes/google/connect"
              className="inline-flex items-center gap-2 rounded-lg bg-brand-charcoal px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-charcoal-hover"
            >
              <Calendar size={16} />
              Conectar con Google
            </a>
          </div>
        )}
      </div>

      <div className="space-y-4 rounded-xl bg-white dark:bg-slate-800 p-6 shadow-sm">
        <div className="flex items-center gap-2">
          <Download size={18} className="text-brand-indigo" />
          <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-200">Tus datos</h3>
        </div>
        <p className="text-sm text-gray-500 dark:text-slate-400">
          Descargá un archivo JSON con todo lo que guardamos: transacciones, tareas,
          notas, eventos, metas, entrenamientos y comidas.
        </p>
        <button
          type="button"
          onClick={handleExport}
          disabled={exportState === 'working'}
          className="flex items-center gap-2 rounded-lg border border-gray-200 dark:border-slate-700 px-4 py-2 text-sm text-gray-700 dark:text-slate-200 transition-colors hover:bg-gray-50 dark:hover:bg-slate-700/50 disabled:opacity-50"
        >
          {exportState === 'working' ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <Download size={16} />
          )}
          {exportState === 'working' ? 'Preparando…' : 'Descargar mis datos'}
        </button>
        {exportState === 'error' && (
          <p className="text-sm text-red-500 dark:text-red-400">
            No se pudo generar la descarga. Probá de nuevo.
          </p>
        )}
      </div>

      <SessionsSection />

      <ReminderSection />

      <div className="space-y-4 rounded-xl border border-rose-200 dark:border-rose-900/50 bg-white dark:bg-slate-800 p-6 shadow-sm">
        <div className="flex items-center gap-2">
          <AlertTriangle size={18} className="text-rose-500" />
          <h3 className="text-sm font-semibold text-rose-600 dark:text-rose-400">
            Eliminar cuenta
          </h3>
        </div>
        <p className="text-sm text-gray-500 dark:text-slate-400">
          Borra tu cuenta y todos tus datos de forma permanente. No se puede
          deshacer: descargá tus datos antes si querés conservarlos.
        </p>

        {!confirmingDelete ? (
          <button
            type="button"
            onClick={() => setConfirmingDelete(true)}
            className="flex items-center gap-2 rounded-lg border border-rose-200 dark:border-rose-900/50 px-4 py-2 text-sm text-rose-500 transition-colors hover:bg-rose-50 dark:hover:bg-rose-900/20"
          >
            <Trash2 size={16} />
            Eliminar mi cuenta
          </button>
        ) : (
          <form onSubmit={handleDelete} className="space-y-3">
            <label className="block text-xs font-medium text-gray-500 dark:text-slate-400">
              Confirmá tu contraseña para continuar
            </label>
            <input
              type="password"
              value={deletePassword}
              onChange={(e) => setDeletePassword(e.target.value)}
              autoComplete="current-password"
              required
              className={inputCls}
            />
            <div className="flex items-center gap-3">
              <button
                type="submit"
                disabled={deleteState === 'working' || !deletePassword}
                className="flex items-center gap-2 rounded-lg bg-rose-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-rose-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {deleteState === 'working' ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Trash2 size={16} />
                )}
                {deleteState === 'working' ? 'Eliminando…' : 'Eliminar definitivamente'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setConfirmingDelete(false);
                  setDeletePassword('');
                  setDeleteState('idle');
                  setDeleteError('');
                }}
                className="text-sm text-gray-500 dark:text-slate-400 hover:underline"
              >
                Cancelar
              </button>
            </div>
            {deleteState === 'error' && (
              <p className="text-sm text-red-500 dark:text-red-400">{deleteError}</p>
            )}
          </form>
        )}
      </div>

      <p className="pb-2 text-center text-xs text-gray-400 dark:text-slate-500">
        <Link to="/terms" className="hover:underline">
          Términos y Condiciones
        </Link>
        {' · '}
        <Link to="/privacy" className="hover:underline">
          Política de Privacidad
        </Link>
        {' · '}
        <Link to="/arrepentimiento" className="hover:underline">
          Botón de arrepentimiento
        </Link>
      </p>
    </div>
  );
}
