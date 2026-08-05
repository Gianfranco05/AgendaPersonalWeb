import { useGoals, checkInGoal } from './useGoals';
import type { Goal } from '../types';

// Una "meta de ahorro" es una Goal con goal_type 'savings'.
export function useSavingsGoals() {
  const swr = useGoals();
  const goals: Goal[] | undefined = swr.data?.filter((g) => g.goal_type === 'savings');
  return { ...swr, data: goals };
}

export async function depositToSavings(id: string, amount: number) {
  await checkInGoal(id, amount);
}

export { addGoal as addSavingsGoal, editGoal as editSavingsGoal, removeGoal as removeSavingsGoal } from './useGoals';
