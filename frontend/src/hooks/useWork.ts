import { createResourceHooks } from './createResourceHooks';
import {
  fetchOpportunities,
  createOpportunity,
  updateOpportunity,
  deleteOpportunity,
  fetchWorkSummary,
} from '../api/endpoints';
import type { WorkOpportunity } from '../types';

const work = createResourceHooks<
  WorkOpportunity,
  Awaited<ReturnType<typeof fetchWorkSummary>>,
  Parameters<typeof fetchOpportunities>[0]
>({
  listKey: 'work/opportunities',
  summaryKey: 'work/summary',
  fetchList: fetchOpportunities,
  fetchSummary: fetchWorkSummary,
  createItem: createOpportunity,
  updateItem: updateOpportunity,
  deleteItem: deleteOpportunity,
});

export const useOpportunities = work.useList;
export const useWorkSummary = work.useSummary;
export const saveOpportunity = work.save;
export const removeOpportunity = work.remove;
