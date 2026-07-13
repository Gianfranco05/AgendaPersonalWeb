import { mutate as globalMutate } from 'swr';
import { useApiSWR } from './useApiSWR';
import {
  fetchNutritionSummary,
  fetchMeals,
  createMeal,
  updateMeal,
  deleteMeal,
} from '../api/endpoints';
import type { Meal } from '../types';

const SUMMARY_KEY = 'nutrition/summary';

function mealsKey(params: Parameters<typeof fetchMeals>[0]) {
  return ['nutrition/meals', JSON.stringify(params ?? {})] as const;
}

export function useNutritionSummary() {
  return useApiSWR(SUMMARY_KEY, fetchNutritionSummary);
}

export function useMeals(params?: Parameters<typeof fetchMeals>[0]) {
  return useApiSWR(mealsKey(params), () => fetchMeals(params));
}

async function invalidateNutrition(params?: Parameters<typeof fetchMeals>[0]) {
  await Promise.all([
    globalMutate(SUMMARY_KEY),
    globalMutate(mealsKey(params)),
  ]);
}

export async function saveMeal(
  meal: Meal | null,
  data: Omit<Meal, 'id'>,
  params?: Parameters<typeof fetchMeals>[0],
) {
  if (meal) {
    await updateMeal(meal.id, data);
  } else {
    await createMeal(data);
  }
  await invalidateNutrition(params);
}

export async function removeMeal(id: string, params?: Parameters<typeof fetchMeals>[0]) {
  await deleteMeal(id);
  await invalidateNutrition(params);
}
