import { mutate as globalMutate } from 'swr';
import { useApiSWR } from './useApiSWR';
import {
  fetchGoals,
  createGoal,
  updateGoal,
  deleteGoal,
  updateGoalProgress,
} from '../api/endpoints';
import type { Goal } from '../types';

const GOALS_KEY = 'goals';

export function useGoals() {
  return useApiSWR(GOALS_KEY, fetchGoals);
}

export async function addGoal(data: Omit<Goal, 'id'>) {
  await createGoal(data);
  await globalMutate(GOALS_KEY);
}

export async function editGoal(id: string, data: Partial<Goal>) {
  await updateGoal(id, data);
  await globalMutate(GOALS_KEY);
}

export async function removeGoal(id: string) {
  await deleteGoal(id);
  await globalMutate(GOALS_KEY);
}

export async function checkInGoal(id: string, current: number) {
  await updateGoalProgress(id, current);
  await globalMutate(GOALS_KEY);
}
