import { create } from 'zustand';

export interface Toast {
  id: number;
  message: string;
}

interface ToastState {
  toasts: Toast[];
  dismiss: (id: number) => void;
}

const TOAST_DURATION_MS = 4000;
let nextId = 1;

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  dismiss: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));

/** Aviso corto que se cierra solo. Se puede llamar desde cualquier lado. */
export function showToast(message: string): void {
  const id = nextId++;
  useToastStore.setState((s) => ({ toasts: [...s.toasts, { id, message }] }));
  setTimeout(() => useToastStore.getState().dismiss(id), TOAST_DURATION_MS);
}
