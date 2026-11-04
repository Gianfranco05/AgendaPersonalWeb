import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useOpenParam, type OpenRequest } from '../useOpenParam';
import { useToastStore } from '../../store/toastStore';

function wrapperFor(initial: string) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <MemoryRouter initialEntries={[initial]}>{children}</MemoryRouter>;
  };
}

function useHarness(options: Parameters<typeof useOpenParam>[0]) {
  useOpenParam(options);
  return useLocation();
}

beforeEach(() => {
  useToastStore.setState({ toasts: [] });
});

describe('useOpenParam', () => {
  it('llama al handler con el pedido y limpia open/entity/parent de la URL', async () => {
    const onOpen = vi.fn<(req: OpenRequest) => boolean>(() => true);
    const { result } = renderHook(() => useHarness({ ready: true, onOpen }), {
      wrapper: wrapperFor('/study?open=e1&entity=exam&parent=s1&otro=1'),
    });

    await waitFor(() => expect(onOpen).toHaveBeenCalledTimes(1));
    expect(onOpen).toHaveBeenCalledWith({ id: 'e1', entity: 'exam', parent: 's1', tab: null });
    await waitFor(() => expect(result.current.search).toBe('?otro=1'));
    expect(useToastStore.getState().toasts).toHaveLength(0);
  });

  it('espera a que la página tenga datos antes de llamar al handler', async () => {
    const onOpen = vi.fn(() => true);
    const { rerender, result } = renderHook(
      ({ ready }: { ready: boolean }) => useHarness({ ready, onOpen }),
      { wrapper: wrapperFor('/notes?open=n1'), initialProps: { ready: false } },
    );
    expect(onOpen).not.toHaveBeenCalled();
    expect(result.current.search).toBe('?open=n1');

    rerender({ ready: true });
    await waitFor(() => expect(onOpen).toHaveBeenCalledWith({ id: 'n1', entity: null, parent: null, tab: null }));
    await waitFor(() => expect(result.current.search).toBe(''));
  });

  it('si el elemento ya no existe avisa con un toast y limpia la URL', async () => {
    const onOpen = vi.fn(() => false);
    const { result } = renderHook(() => useHarness({ ready: true, onOpen }), {
      wrapper: wrapperFor('/tasks?open=borrada'),
    });
    await waitFor(() => expect(useToastStore.getState().toasts).toHaveLength(1));
    expect(useToastStore.getState().toasts[0].message).toBe('Ese elemento ya no existe');
    expect(result.current.search).toBe('');
  });

  it('pasa la pestaña (tab) y la limpia junto con el resto', async () => {
    const onOpen = vi.fn(() => true);
    const { result } = renderHook(() => useHarness({ ready: true, onOpen }), {
      wrapper: wrapperFor('/finances?tab=inversiones&open=i1'),
    });
    await waitFor(() =>
      expect(onOpen).toHaveBeenCalledWith({ id: 'i1', entity: null, parent: null, tab: 'inversiones' }),
    );
    await waitFor(() => expect(result.current.search).toBe(''));
  });

  it('no reabre el mismo pedido al volver a renderizar', async () => {
    const onOpen = vi.fn(() => true);
    const { rerender } = renderHook(() => useHarness({ ready: true, onOpen }), {
      wrapper: wrapperFor('/habits?open=h1'),
    });
    await waitFor(() => expect(onOpen).toHaveBeenCalledTimes(1));
    rerender();
    rerender();
    expect(onOpen).toHaveBeenCalledTimes(1);
  });

  it('sin parámetro open no hace nada', () => {
    const onOpen = vi.fn(() => true);
    renderHook(() => useHarness({ ready: true, onOpen }), { wrapper: wrapperFor('/habits') });
    expect(onOpen).not.toHaveBeenCalled();
  });

  it('con el handler en "wait" no limpia ni avisa y reintenta en el próximo render', async () => {
    let answer: boolean | 'wait' = 'wait';
    const onOpen = vi.fn(() => answer);
    const { rerender, result } = renderHook(() => useHarness({ ready: true, onOpen }), {
      wrapper: wrapperFor('/goals?open=g1'),
    });
    await waitFor(() => expect(onOpen).toHaveBeenCalled());
    expect(result.current.search).toBe('?open=g1');
    expect(useToastStore.getState().toasts).toHaveLength(0);

    answer = true;
    act(() => rerender());
    await waitFor(() => expect(result.current.search).toBe(''));
  });
});
