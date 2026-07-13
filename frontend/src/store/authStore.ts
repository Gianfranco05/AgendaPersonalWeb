import { create } from 'zustand';
import type { AuthUser } from '../types/auth';
import * as authApi from '../api/authApi';

interface AuthState {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
  updateProfile: (fullName: string) => Promise<void>;
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
}));
