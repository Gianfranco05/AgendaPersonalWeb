import { mutate as globalMutate } from 'swr';
import { useApiSWR } from './useApiSWR';
import {
  fetchNotes,
  fetchTags,
  createNote,
  updateNote,
  deleteNote,
} from '../api/endpoints';
import type { Note } from '../types';

const NOTES_KEY = 'notes';
const TAGS_KEY = 'notes/tags';

export function useNotes() {
  return useApiSWR(NOTES_KEY, fetchNotes);
}

export function useTags() {
  return useApiSWR(TAGS_KEY, fetchTags);
}

async function invalidateNotes() {
  await globalMutate(NOTES_KEY);
}

export async function saveNote(
  existing: Note | null,
  data: Omit<Note, 'id' | 'created_at' | 'updated_at'>,
) {
  if (existing) {
    await updateNote(existing.id, data);
  } else {
    await createNote(data);
  }
  await invalidateNotes();
}

export async function removeNote(id: string) {
  await deleteNote(id);
  await invalidateNotes();
}
