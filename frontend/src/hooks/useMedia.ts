import { mutate as globalMutate } from 'swr';
import { useApiSWR } from './useApiSWR';
import {
  fetchMediaItems,
  createMediaItem,
  updateMediaItem,
  deleteMediaItem,
  fetchMediaSummary,
} from '../api/endpoints';
import type { MediaItem } from '../types';

const ITEMS_KEY = 'media/items';
const SUMMARY_KEY = 'media/summary';

export function useMediaItems(params?: Parameters<typeof fetchMediaItems>[0]) {
  return useApiSWR([ITEMS_KEY, JSON.stringify(params ?? {})], () => fetchMediaItems(params));
}

export function useMediaSummary() {
  return useApiSWR(SUMMARY_KEY, fetchMediaSummary);
}

async function revalidate() {
  await Promise.all([
    globalMutate((key) => Array.isArray(key) && key[0] === ITEMS_KEY),
    globalMutate(SUMMARY_KEY),
  ]);
}

export async function saveMediaItem(item: MediaItem | null, data: Partial<MediaItem>) {
  if (item) {
    await updateMediaItem(item.id, data);
  } else {
    await createMediaItem(data);
  }
  await revalidate();
}

export async function removeMediaItem(id: string) {
  await deleteMediaItem(id);
  await revalidate();
}
