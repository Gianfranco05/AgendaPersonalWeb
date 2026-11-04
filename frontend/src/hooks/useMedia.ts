import { createResourceHooks } from './createResourceHooks';
import {
  fetchMediaItems,
  createMediaItem,
  updateMediaItem,
  deleteMediaItem,
  fetchMediaSummary,
} from '../api/endpoints';
import type { MediaItem } from '../types';

const media = createResourceHooks<
  MediaItem,
  Awaited<ReturnType<typeof fetchMediaSummary>>,
  Parameters<typeof fetchMediaItems>[0]
>({
  listKey: 'media/items',
  summaryKey: 'media/summary',
  fetchList: fetchMediaItems,
  fetchSummary: fetchMediaSummary,
  createItem: createMediaItem,
  updateItem: updateMediaItem,
  deleteItem: deleteMediaItem,
});

export const useMediaItems = media.useList;
export const useMediaSummary = media.useSummary;
export const saveMediaItem = media.save;
export const removeMediaItem = media.remove;
