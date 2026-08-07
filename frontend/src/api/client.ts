import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '',
  withCredentials: true,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

// Un 401 acá es un error de credenciales real, no un access token vencido:
// reintentar el refresh no tendría sentido y enmascararía el error del form.
const NO_REFRESH_PATHS = ['/auth/api/login', '/auth/api/register', '/auth/api/refresh'];

type RetriableConfig = InternalAxiosRequestConfig & { _retried?: boolean };

// Single-flight: si varias requests fallan con 401 a la vez, todas esperan el
// mismo refresh en lugar de dispararlo N veces. Como el backend rota el token
// en cada uso, N refreshes en paralelo se pisarían entre sí y cerrarían la sesión.
let refreshPromise: Promise<void> | null = null;

function refreshSession(): Promise<void> {
  if (!refreshPromise) {
    refreshPromise = apiClient
      .post('/auth/api/refresh', {})
      .then(() => undefined)
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

async function forceLogout(): Promise<void> {
  const { useAuthStore } = await import('../store/authStore');
  useAuthStore.setState({ user: null, isAuthenticated: false, isLoading: false });
  if (!(window.location.pathname ?? '').startsWith('/login')) {
    window.location.href = '/login';
  }
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const status = error.response?.status;
    const config = error.config as RetriableConfig | undefined;
    const url: string = config?.url ?? '';

    const shouldTryRefresh =
      status === 401 &&
      config &&
      !config._retried &&
      !NO_REFRESH_PATHS.some((path) => url.includes(path));

    if (shouldTryRefresh) {
      config._retried = true;
      try {
        await refreshSession();
        return apiClient(config);
      } catch {
        // El refresh token también venció o fue revocado: sesión terminada.
        await forceLogout();
      }
    }

    return Promise.reject(error);
  },
);

export default apiClient;
