import { create } from 'zustand';
import type { AuthUser } from '../types/auth';
import * as authApi from '../api/authApi';

// Tiene que coincidir con settings.CURRENT_TERMS_VERSION en el backend
// (backend/app/config.py). Subir este valor "des-acepta" a todos los
// usuarios existentes sin tocar sus filas: el gate compara esto contra
// `user.terms_accepted_version` y decide si mostrar /accept-terms de nuevo.
export const CURRENT_TERMS_VERSION = '1.0';

interface AuthState {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
  updateProfile: (fullName: string) => Promise<void>;
  acceptTerms: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,

  login: async (email, password) => {
    const user = await authApi.login(email, password);
    set({ user, isAuthenticated: true });
  },

  logout: async () => {
    await authApi.logout();
    set({ user: null, isAuthenticated: false });
  },

  checkAuth: async () => {
    try {
      const user = await authApi.getMe();
      set({ user, isAuthenticated: true, isLoading: false });
    } catch {
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },

  updateProfile: async (fullName) => {
    const user = await authApi.updateProfile(fullName);
    set({ user });
  },

  acceptTerms: async () => {
    const user = await authApi.acceptTerms(CURRENT_TERMS_VERSION);
    set({ user });
  },
}));
