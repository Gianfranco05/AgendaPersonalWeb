import useSWR, { mutate as globalMutate } from 'swr';
import { fetchEvents, createEvent } from '../api/endpoints';
import type { CalendarEvent } from '../types';

const EVENTS_KEY = 'events';

export function useEvents() {
  return useSWR(EVENTS_KEY, fetchEvents);
}

export async function addEvent(data: Omit<CalendarEvent, 'id'>) {
  await createEvent(data);
  await globalMutate(EVENTS_KEY);
}
