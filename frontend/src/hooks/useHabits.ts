import { useGoals } from './useGoals';
import type { Goal } from '../types';

// Un "hábito" es simplemente una Goal con goal_type binario.
export function useHabits() {
  const swr = useGoals();
  const habits: Goal[] | undefined = swr.data?.filter((g) => g.goal_type === 'binary');
  return { ...swr, data: habits };
}

export { addGoal as addHabit, editGoal as editHabit, removeGoal as removeHabit, checkInGoal as checkInHabit } from './useGoals';
