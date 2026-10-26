import { useApiSWR } from './useApiSWR';
import { fetchMarketFx, fetchInflation, fetchCryptoAssets } from '../api/endpoints';

const FX_REFRESH_MS = 5 * 60 * 1000;

/** Cotizaciones del dólar y el euro que guarda el server. El server las
 *  actualiza cada ~15 min; acá se refrescan cada 5 para ver el cambio rápido. */
export function useMarketFx() {
  return useApiSWR('finance/market/fx', fetchMarketFx, { refreshInterval: FX_REFRESH_MS });
}

/** Variación mensual del IPC (para mostrar de dónde sale el rendimiento real). */
export function useInflation(months = 12) {
  return useApiSWR(['finance/market/inflation', months], () => fetchInflation(months));
}

/** Tickers de cripto con cotización automática (cambian muy de vez en cuando). */
export function useCryptoAssets() {
  return useApiSWR('finance/market/crypto-assets', fetchCryptoAssets, {
    revalidateOnFocus: false,
    dedupingInterval: 60 * 60 * 1000,
  });
}
