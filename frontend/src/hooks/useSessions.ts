import { mutate as globalMutate } from 'swr';
import { useApiSWR } from './useApiSWR';
import { fetchSessions, revokeSession as apiRevokeSession } from '../api/endpoints';

const SESSIONS_KEY = 'auth/sessions';

export function useSessions() {
  return useApiSWR(SESSIONS_KEY, fetchSessions);
}

export async function revokeSession(id: string) {
  await apiRevokeSession(id);
  await globalMutate(SESSIONS_KEY);
}
