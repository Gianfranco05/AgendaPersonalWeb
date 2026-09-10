import { createResourceHooks } from './createResourceHooks';
import { fetchBooks, createBook, updateBook, deleteBook, fetchLibrarySummary } from '../api/endpoints';
import type { Book } from '../types';

const library = createResourceHooks<Book, Awaited<ReturnType<typeof fetchLibrarySummary>>, Parameters<typeof fetchBooks>[0]>({
  listKey: 'library/books',
  summaryKey: 'library/summary',
  fetchList: fetchBooks,
  fetchSummary: fetchLibrarySummary,
  createItem: createBook,
  updateItem: updateBook,
  deleteItem: deleteBook,
});

export const useBooks = library.useList;
export const useLibrarySummary = library.useSummary;
export const saveBook = library.save;
export const removeBook = library.remove;
