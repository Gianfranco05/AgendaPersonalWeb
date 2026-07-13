import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '',
  withCredentials: true,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error.response?.status;
    const url: string = error.config?.url ?? '';

    // Session expired on a protected call: clear auth state and go to login.
    // Auth endpoints are excluded so login errors surface in their own forms.
    if (status === 401 && !url.includes('/auth/')) {
      const { useAuthStore } = await import('../store/authStore');
      useAuthStore.setState({ user: null, isAuthenticated: false, isLoading: false });
      if (!(window.location.pathname ?? '').startsWith('/login')) {
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  },
);

export default apiClient;
