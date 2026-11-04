import { mutate as globalMutate } from 'swr';
import { useApiSWR } from './useApiSWR';
import { fetchModules, toggleModule } from '../api/endpoints';

const MODULES_KEY = 'modules';

export function useModules() {
  return useApiSWR(MODULES_KEY, fetchModules);
}

export async function toggleModuleVisibility(key: string, enabled: boolean) {
  await toggleModule(key, enabled);
  await globalMutate(MODULES_KEY);
}
