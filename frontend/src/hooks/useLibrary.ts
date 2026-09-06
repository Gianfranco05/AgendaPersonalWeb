import { mutate as globalMutate } from 'swr';
import { useApiSWR } from './useApiSWR';
import { fetchBooks, createBook, updateBook, deleteBook, fetchLibrarySummary } from '../api/endpoints';
import type { Book } from '../types';

const BOOKS_KEY = 'library/books';
const SUMMARY_KEY = 'library/summary';

export function useBooks(params?: Parameters<typeof fetchBooks>[0]) {
  return useApiSWR([BOOKS_KEY, JSON.stringify(params ?? {})], () => fetchBooks(params));
}

export function useLibrarySummary() {
  return useApiSWR(SUMMARY_KEY, fetchLibrarySummary);
}

async function revalidate() {
  await Promise.all([
    globalMutate((key) => Array.isArray(key) && key[0] === BOOKS_KEY),
    globalMutate(SUMMARY_KEY),
  ]);
}

export async function saveBook(book: Book | null, data: Partial<Book>) {
  if (book) {
    await updateBook(book.id, data);
  } else {
    await createBook(data);
  }
  await revalidate();
}

export async function removeBook(id: string) {
  await deleteBook(id);
  await revalidate();
}
