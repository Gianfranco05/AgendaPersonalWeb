import { useEffect, useState } from 'react';
import { useApiSWR } from './useApiSWR';
import { searchAll } from '../api/endpoints';
import { isSearchable, normalizeQuery } from '../utils/search';
import type { SearchResponse, SearchType } from '../types';

export const SEARCH_DEBOUNCE_MS = 250;

interface Options {
  types?: SearchType[];
  limit?: number;
}

/**
 * Búsqueda en vivo: espera 250 ms sin tipear, no llama con menos de 2
 * caracteres y conserva la respuesta anterior mientras llega la nueva para
 * que la lista no parpadee. Los errores no se reintentan: un 429 (límite de
 * búsquedas) reintentado solo empeoraría las cosas.
 */
export function useSearch(rawQuery: string, { types, limit }: Options = {}) {
  const normalized = normalizeQuery(rawQuery);
  const [debounced, setDebounced] = useState(normalized);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(normalized), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [normalized]);

  const enabled = isSearchable(debounced);
  const { data, error, isLoading, isValidating } = useApiSWR<SearchResponse>(
    enabled ? ['search', debounced, types?.join(',') ?? '', limit ?? 0] : null,
    enabled ? () => searchAll(debounced, { types, limit }) : null,
    { keepPreviousData: true, shouldRetryOnError: false, revalidateOnFocus: false },
  );

  return {
    data: enabled ? data : undefined,
    error: enabled ? error : undefined,
    isLoading: enabled && (isLoading || isValidating),
    enabled,
    /** La búsqueda que se está mostrando (ya con debounce). */
    query: debounced,
  };
}
