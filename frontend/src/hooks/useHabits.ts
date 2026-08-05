import { mutate as globalMutate } from 'swr';
import { useGoals } from './useGoals';
import { useApiSWR } from './useApiSWR';
import { fetchHabitRecords, upsertHabitRecord, fetchMonthlySummary } from '../api/endpoints';
import type { Goal, HabitRecord } from '../types';

// Un "hábito" es simplemente una Goal con goal_type binario.
export function useHabits() {
  const swr = useGoals();
  const habits: Goal[] | undefined = swr.data?.filter((g) => g.goal_type === 'binary');
  return { ...swr, data: habits };
}

// Hábitos "métricos": se carga un valor numérico distinto cada día (minutos, páginas, etc.)
export function useMetricHabits() {
  const swr = useGoals();
  const metrics: Goal[] | undefined = swr.data?.filter((g) => g.goal_type === 'metric');
  return { ...swr, data: metrics };
}

// Registros del mes para un conjunto de hábitos métricos, en una sola llamada SWR
// (evita invocar un hook por cada goal, lo cual violaría las reglas de hooks).
export function useHabitRecordsForGoals(goalIds: string[], year: number, month: number) {
  const sortedIds = [...goalIds].sort();
  const key = sortedIds.length > 0 ? (['habit-records-multi', sortedIds.join(','), year, month] as const) : null;
  return useApiSWR(key, async () => {
    const results = await Promise.all(goalIds.map((id) => fetchHabitRecords(id, year, month)));
    const map: Record<string, HabitRecord[]> = {};
    goalIds.forEach((id, i) => {
      map[id] = results[i];
    });
    return map;
  });
}

export function useMonthlySummary(year: number, month: number) {
  return useApiSWR(['habits/summary', year, month] as const, () => fetchMonthlySummary(year, month));
}

export async function logHabit(goalId: string, recordDate: string, value: number, notes?: string | null) {
  await upsertHabitRecord(goalId, recordDate, value, notes);
  await globalMutate((key) => Array.isArray(key) && key[0] === 'habit-records-multi');
  await globalMutate((key) => Array.isArray(key) && key[0] === 'habits/summary');
}

export { addGoal as addHabit, editGoal as editHabit, removeGoal as removeHabit, checkInGoal as checkInHabit } from './useGoals';
