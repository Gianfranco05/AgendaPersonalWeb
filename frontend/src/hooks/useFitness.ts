import { mutate as globalMutate } from 'swr';
import { useApiSWR } from './useApiSWR';
import {
  fetchFitnessSummary,
  fetchWorkoutSessions,
  createWorkoutSession,
  updateWorkoutSession,
  deleteWorkoutSession,
} from '../api/endpoints';
import type { WorkoutSession } from '../types';

const SUMMARY_KEY = 'fitness/summary';
const SESSIONS_KEY = 'fitness/sessions';

export function useFitnessSummary() {
  return useApiSWR(SUMMARY_KEY, fetchFitnessSummary);
}

export function useWorkoutSessions() {
  return useApiSWR(SESSIONS_KEY, fetchWorkoutSessions);
}

async function invalidateFitness() {
  await Promise.all([
    globalMutate(SUMMARY_KEY),
    globalMutate(SESSIONS_KEY),
  ]);
}

export async function saveWorkoutSession(
  session: WorkoutSession | null,
  data: Omit<WorkoutSession, 'id'>,
) {
  if (session) {
    await updateWorkoutSession(session.id, data);
  } else {
    await createWorkoutSession(data);
  }
  await invalidateFitness();
}

export async function removeWorkoutSession(id: string) {
  await deleteWorkoutSession(id);
  await invalidateFitness();
}
