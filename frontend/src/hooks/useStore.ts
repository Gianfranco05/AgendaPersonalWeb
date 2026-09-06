import { mutate as globalMutate } from 'swr';
import { useApiSWR } from './useApiSWR';
import { fetchStore, createCheckout } from '../api/endpoints';

const STORE_KEY = 'billing/store';
const MODULES_KEY = 'modules';

export function useStore() {
  return useApiSWR(STORE_KEY, fetchStore);
}

/**
 * Inicia el checkout de Stripe para una plantilla y redirige a la página de
 * pago hosteada por Stripe. Vuelve a esta misma pestaña: no hay deep link,
 * eso es solo para la app mobile.
 */
export async function startCheckout(moduleKey: string): Promise<void> {
  const { url } = await createCheckout(moduleKey);
  window.location.href = url;
}

/** Tras volver de un checkout exitoso, tienda y selector de módulos quedan desincronizados sin esto. */
export async function revalidateAfterPurchase() {
  await Promise.all([globalMutate(STORE_KEY), globalMutate(MODULES_KEY)]);
}
