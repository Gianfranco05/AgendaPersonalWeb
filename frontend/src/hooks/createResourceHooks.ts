import { mutate as globalMutate } from 'swr';
import { useApiSWR } from './useApiSWR';

/**
 * Factory para el patrón list+summary+revalidate+save+remove que se repite en
 * los hooks de recurso simple (sin sub-entidad anidada): useLibrary, useMedia,
 * useWork, useFocus. Ver useNutrition.ts / useApiSWR.ts para el patrón base de
 * SWR ya establecido en el proyecto.
 *
 * Los hooks con sub-recurso anidado (useTravel, useVehicle, useProjects,
 * useStudy) tienen una segunda key SWR dependiente del id padre y
 * revalidación cruzada — se mantienen escritos a mano.
 */
export function createResourceHooks<TItem extends { id: string }, TSummary, TParams = void>(config: {
  /** Key base de la lista (string simple, se usa como prefijo si `paramsInKey`). */
  listKey: string;
  summaryKey: string;
  fetchList: (params?: TParams) => Promise<TItem[]>;
  fetchSummary: () => Promise<TSummary>;
  /** Omitir si el recurso no soporta crear/editar vía save() genérico (ej. Focus). */
  createItem?: (data: Partial<TItem>) => Promise<unknown>;
  updateItem?: (id: string, data: Partial<TItem>) => Promise<unknown>;
  deleteItem: (id: string) => Promise<unknown>;
  /**
   * Si la lista toma params, la key se arma como [listKey, JSON.stringify(params ?? {})]
   * y la revalidación usa un matcher de array-prefix (igual que useLibrary/useMedia/useWork).
   * Si la lista no toma params (ej. useFocusSessions), se usa `listKey` tal cual.
   * Default: true.
   */
  paramsInKey?: boolean;
}) {
  const { listKey, summaryKey, fetchList, fetchSummary, createItem, updateItem, deleteItem } = config;
  const paramsInKey = config.paramsInKey ?? true;

  function useList(params?: TParams) {
    const key = paramsInKey ? ([listKey, JSON.stringify(params ?? {})] as const) : listKey;
    return useApiSWR<TItem[]>(key, () => fetchList(params));
  }

  function useSummary() {
    return useApiSWR<TSummary>(summaryKey, fetchSummary);
  }

  async function revalidate() {
    const listMutate = paramsInKey
      ? globalMutate((key) => Array.isArray(key) && key[0] === listKey)
      : globalMutate(listKey);
    await Promise.all([listMutate, globalMutate(summaryKey)]);
  }

  async function save(item: TItem | null, data: Partial<TItem>) {
    if (item) {
      await updateItem!(item.id, data);
    } else {
      await createItem!(data);
    }
    await revalidate();
  }

  async function remove(id: string) {
    await deleteItem(id);
    await revalidate();
  }

  return { useList, useSummary, revalidate, save, remove };
}
