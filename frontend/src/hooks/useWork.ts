import { mutate as globalMutate } from 'swr';
import { useApiSWR } from './useApiSWR';
import {
  fetchOpportunities,
  createOpportunity,
  updateOpportunity,
  deleteOpportunity,
  fetchWorkSummary,
} from '../api/endpoints';
import type { WorkOpportunity } from '../types';

const OPPORTUNITIES_KEY = 'work/opportunities';
const SUMMARY_KEY = 'work/summary';

export function useOpportunities(params?: Parameters<typeof fetchOpportunities>[0]) {
  return useApiSWR([OPPORTUNITIES_KEY, JSON.stringify(params ?? {})], () => fetchOpportunities(params));
}

export function useWorkSummary() {
  return useApiSWR(SUMMARY_KEY, fetchWorkSummary);
}

async function revalidate() {
  await Promise.all([
    globalMutate((key) => Array.isArray(key) && key[0] === OPPORTUNITIES_KEY),
    globalMutate(SUMMARY_KEY),
  ]);
}

export async function saveOpportunity(opportunity: WorkOpportunity | null, data: Partial<WorkOpportunity>) {
  if (opportunity) {
    await updateOpportunity(opportunity.id, data);
  } else {
    await createOpportunity(data);
  }
  await revalidate();
}

export async function removeOpportunity(id: string) {
  await deleteOpportunity(id);
  await revalidate();
}
