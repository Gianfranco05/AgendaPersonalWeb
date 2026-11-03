import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { SWRConfig } from 'swr';
import type { ReactNode } from 'react';
import { useSearch, SEARCH_DEBOUNCE_MS } from '../useSearch';

vi.mock('../../api/endpoints', () => ({ searchAll: vi.fn() }));
import { searchAll } from '../../api/endpoints';

const wrapper = ({ children }: { children: ReactNode }) => (
  <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>{children}</SWRConfig>
);

const response = (query: string) => ({ query, groups: [] });

beforeEach(() => {
  vi.useFakeTimers();
  vi.mocked(searchAll).mockReset();
  vi.mocked(searchAll).mockImplementation(async (q: string) => response(q));
});
afterEach(() => vi.useRealTimers());

async function flush() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(SEARCH_DEBOUNCE_MS + 10);
  });
}

describe('useSearch', () => {
  it('con menos de 2 caracteres no llama al server', async () => {
    const { result } = renderHook(() => useSearch('a'), { wrapper });
    await flush();
    expect(searchAll).not.toHaveBeenCalled();
    expect(result.current.enabled).toBe(false);
    expect(result.current.data).toBeUndefined();
  });

  it('el debounce manda una sola request aunque se tipee rápido', async () => {
    const { rerender } = renderHook(({ q }: { q: string }) => useSearch(q), {
      wrapper,
      initialProps: { q: 'c' },
    });
    for (const q of ['ca', 'caf', 'cafe', 'cafe ']) {
      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });
      rerender({ q });
    }
    expect(searchAll).not.toHaveBeenCalled();
    await flush();
    expect(searchAll).toHaveBeenCalledTimes(1);
    expect(searchAll).toHaveBeenCalledWith('cafe', { types: undefined, limit: undefined });
  });

  it('pide solo un tipo con su límite cuando se le indica ("Ver más")', async () => {
    renderHook(() => useSearch('cafe', { types: ['notes'], limit: 20 }), { wrapper });
    await flush();
    expect(searchAll).toHaveBeenCalledWith('cafe', { types: ['notes'], limit: 20 });
  });

  it('devuelve los datos y mantiene los anteriores mientras llega la búsqueda nueva', async () => {
    const { result, rerender } = renderHook(({ q }: { q: string }) => useSearch(q), {
      wrapper,
      initialProps: { q: 'cafe' },
    });
    await flush();
    expect(result.current.data?.query).toBe('cafe');

    let release: (v: ReturnType<typeof response>) => void = () => {};
    vi.mocked(searchAll).mockImplementationOnce(() => new Promise((res) => { release = res; }));
    rerender({ q: 'cafeteria' });
    await flush();
    expect(result.current.data?.query).toBe('cafe');
    expect(result.current.isLoading).toBe(true);

    await act(async () => release(response('cafeteria')));
    expect(result.current.data?.query).toBe('cafeteria');
  });

  it('al borrar hasta menos de 2 caracteres deja de buscar y no devuelve resultados viejos', async () => {
    const { result, rerender } = renderHook(({ q }: { q: string }) => useSearch(q), {
      wrapper,
      initialProps: { q: 'cafe' },
    });
    await flush();
    rerender({ q: 'c' });
    await flush();
    expect(result.current.enabled).toBe(false);
    expect(result.current.data).toBeUndefined();
  });
});
