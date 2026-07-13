import { mutate as globalMutate } from 'swr';
import { useApiSWR } from './useApiSWR';
import { fetchEvents, createEvent, updateEvent, deleteEvent } from '../api/endpoints';
import type { CalendarEvent } from '../types';

const EVENTS_KEY = 'events';

export function useEvents() {
  return useApiSWR(EVENTS_KEY, fetchEvents);
}

export async function addEvent(data: Omit<CalendarEvent, 'id'>) {
  await createEvent(data);
  await globalMutate(EVENTS_KEY);
}

export async function editEvent(id: string, data: Partial<CalendarEvent>) {
  await updateEvent(id, data);
  await globalMutate(EVENTS_KEY);
}

export async function removeEvent(id: string) {
  await deleteEvent(id);
  await globalMutate(EVENTS_KEY);
}
