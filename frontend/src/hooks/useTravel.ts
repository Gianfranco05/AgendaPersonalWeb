import { mutate as globalMutate } from 'swr';
import { useApiSWR } from './useApiSWR';
import {
  fetchTrips,
  createTrip,
  updateTrip,
  deleteTrip,
  fetchPackingItems,
  addPackingItem,
  setPackingItemPacked,
  deletePackingItem,
  fetchTravelSummary,
} from '../api/endpoints';
import type { Trip } from '../types';

const TRIPS_KEY = 'travel/trips';
const SUMMARY_KEY = 'travel/summary';
const itemsKey = (tripId: string) => ['travel/items', tripId] as const;

export function useTrips() {
  return useApiSWR(TRIPS_KEY, fetchTrips);
}

export function useTravelSummary() {
  return useApiSWR(SUMMARY_KEY, fetchTravelSummary);
}

export function usePackingItems(tripId: string | null) {
  return useApiSWR(tripId ? itemsKey(tripId) : null, tripId ? () => fetchPackingItems(tripId) : null);
}

async function revalidateTrips() {
  await Promise.all([globalMutate(TRIPS_KEY), globalMutate(SUMMARY_KEY)]);
}

export async function addTrip(input: Partial<Trip>) {
  await createTrip(input);
  await revalidateTrips();
}

export async function editTrip(id: string, input: Partial<Trip>) {
  await updateTrip(id, input);
  await revalidateTrips();
}

export async function removeTrip(id: string) {
  await deleteTrip(id);
  await revalidateTrips();
}

export async function addItem(tripId: string, name: string) {
  await addPackingItem(tripId, name);
  await globalMutate(itemsKey(tripId));
}

export async function toggleItemPacked(tripId: string, itemId: string, packed: boolean) {
  await setPackingItemPacked(itemId, packed);
  await globalMutate(itemsKey(tripId));
}

export async function removeItem(tripId: string, itemId: string) {
  await deletePackingItem(itemId);
  await globalMutate(itemsKey(tripId));
}
