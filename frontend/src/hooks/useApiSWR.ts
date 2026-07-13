import useSWR, { type SWRConfiguration } from 'swr';

export function useApiSWR<T>(
  key: Parameters<typeof useSWR>[0],
  fetcher: (() => Promise<T>) | null,
  config?: SWRConfiguration,
) {
  return useSWR<T>(key, fetcher, {
    shouldRetryOnError: true,
    errorRetryCount: 2,
    onError: (err: Error) => {
      console.error('[API Error]', key, err);
    },
    ...config,
  });
}
