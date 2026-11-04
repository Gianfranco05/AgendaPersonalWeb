import { create } from 'zustand';

export type OnboardingMode = 'welcome' | 'replay';

interface OnboardingState {
  // null = cerrado. 'replay' lo abre "Ver tutorial" en Configuración y no escribe nada.
  mode: OnboardingMode | null;
  // Usuario para el que ya se cerró el tutorial de bienvenida en esta pestaña:
  // evita reabrirlo mientras el PUT a /settings está en vuelo o si falló.
  dismissedFor: string | null;
  openWelcome: () => void;
  openReplay: () => void;
  close: (userId?: string | null) => void;
}

export const useOnboardingStore = create<OnboardingState>((set) => ({
  mode: null,
  dismissedFor: null,
  openWelcome: () => set({ mode: 'welcome' }),
  openReplay: () => set({ mode: 'replay' }),
  close: (userId) =>
    set((s) => ({ mode: null, dismissedFor: userId !== undefined ? userId : s.dismissedFor })),
}));
