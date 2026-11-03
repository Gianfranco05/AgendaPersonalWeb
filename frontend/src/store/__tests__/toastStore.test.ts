import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { useToastStore, showToast } from '../toastStore';

describe('toastStore', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useToastStore.setState({ toasts: [] });
  });
  afterEach(() => vi.useRealTimers());

  it('agrega un aviso y lo saca solo después de unos segundos', () => {
    showToast('Ese elemento ya no existe');
    expect(useToastStore.getState().toasts.map((t) => t.message)).toEqual(['Ese elemento ya no existe']);
    vi.advanceTimersByTime(5000);
    expect(useToastStore.getState().toasts).toHaveLength(0);
  });

  it('dismiss saca solo el aviso indicado', () => {
    showToast('uno');
    showToast('dos');
    const [first] = useToastStore.getState().toasts;
    useToastStore.getState().dismiss(first.id);
    expect(useToastStore.getState().toasts.map((t) => t.message)).toEqual(['dos']);
  });
});
