import apiClient from './client';
import type { Transaction, Note, CalendarEvent, Tag, Category, FinanceSummary } from '../types';

const MOCK_ENABLED = true;

function generateId(): string {
  return Math.random().toString(36).substring(2, 15);
}

function mockDelay<T>(data: T): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(data), 300));
}

// ── Finance ──

export async function fetchFinanceSummary(): Promise<FinanceSummary> {
  if (MOCK_ENABLED) {
    return mockDelay({
      total_income: 1250000,
      total_expense: 870000,
      balance: 380000,
      currency: 'ARS',
    });
  }
  const { data } = await apiClient.get<FinanceSummary>('/finanzas/api/summary');
  return data;
}

export interface TransactionsResponse {
  transactions: Transaction[];
  total: number;
  page: number;
  per_page: number;
}

export async function fetchTransactions(params?: {
  page?: number;
  per_page?: number;
  type?: string;
  category?: string;
  date_from?: string;
  date_to?: string;
}): Promise<TransactionsResponse> {
  if (MOCK_ENABLED) {
    const mockTransactions: Transaction[] = Array.from({ length: 25 }, (_, i) => ({
      id: generateId(),
      amount: Math.round(Math.random() * 500000) / 100,
      currency: i % 4 === 0 ? 'USD' : 'ARS',
      type: i % 3 === 0 ? 'income' : 'expense',
      transaction_date: new Date(2025, 5, 20 - i).toISOString().split('T')[0],
      product_name: `Transacción ${i + 1}`,
      merchant_name: ['Supermercado', 'Restaurante', 'Servicios', 'Freelance', 'Tienda'][i % 5],
      payment_method: ['Efectivo', 'Transferencia', 'Tarjeta', 'Débito'][i % 4],
      category_name: ['Alimentos', 'Transporte', 'Vivienda', 'Entretenimiento', 'Ingresos'][i % 5],
      category_color: ['#10B981', '#F59E0B', '#7C3AED', '#EF4444', '#3B82F6'][i % 5],
    }));
    return mockDelay({
      transactions: mockTransactions,
      total: 25,
      page: 1,
      per_page: 20,
    });
  }
  const { data } = await apiClient.get<TransactionsResponse>('/finanzas/api/transactions', { params });
  return data;
}

export async function createTransaction(transaction: Omit<Transaction, 'id'>): Promise<Transaction> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...transaction, id: generateId() });
  }
  const { data } = await apiClient.post<Transaction>('/finanzas/api/transactions', transaction);
  return data;
}

export async function updateTransaction(id: string, transaction: Partial<Transaction>): Promise<Transaction> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...transaction, id } as Transaction);
  }
  const { data } = await apiClient.put<Transaction>(`/finanzas/api/transactions/${id}`, transaction);
  return data;
}

export async function deleteTransaction(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    return mockDelay(undefined);
  }
  await apiClient.delete(`/finanzas/api/transactions/${id}`);
}

// ── Notes ──

export async function fetchNotes(): Promise<Note[]> {
  if (MOCK_ENABLED) {
    const mockNotes: Note[] = [
      {
        id: 'n1',
        title: 'Ideas para el proyecto',
        content: '# Ideas\n\n- Mejorar la UI\n- Agregar tests\n- Documentar API',
        is_pinned: true,
        is_archived: false,
        color: '#7C3AED',
        tags: [{ id: 't1', name: 'proyecto', color: '#7C3AED' }],
        created_at: '2025-06-15T10:00:00',
        updated_at: '2025-06-18T14:30:00',
      },
      {
        id: 'n2',
        title: 'Receta de cocina',
        content: '## Ingredientes\n\n- Harina\n- Huevos\n- Leche',
        is_pinned: false,
        is_archived: false,
        color: '#F59E0B',
        tags: [{ id: 't2', name: 'cocina', color: '#F59E0B' }],
        created_at: '2025-06-10T08:00:00',
        updated_at: '2025-06-10T08:00:00',
      },
      {
        id: 'n3',
        title: 'Notas de lectura',
        content: '```python\ndef hello():\n    print("Hello World")\n```',
        is_pinned: false,
        is_archived: false,
        color: '#10B981',
        tags: [{ id: 't3', name: 'lectura', color: '#10B981' }, { id: 't4', name: 'python', color: '#3B82F6' }],
        created_at: '2025-06-05T12:00:00',
        updated_at: '2025-06-08T09:00:00',
      },
    ];
    return mockDelay(mockNotes);
  }
  const { data } = await apiClient.get<Note[]>('/anotaciones/api/notes');
  return data;
}

export async function createNote(note: Omit<Note, 'id' | 'created_at' | 'updated_at'>): Promise<Note> {
  if (MOCK_ENABLED) {
    return mockDelay({
      ...note,
      id: generateId(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });
  }
  const { data } = await apiClient.post<Note>('/anotaciones/api/notes', note);
  return data;
}

export async function updateNote(id: string, note: Partial<Note>): Promise<Note> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...note, id } as Note);
  }
  const { data } = await apiClient.put<Note>(`/anotaciones/api/notes/${id}`, note);
  return data;
}

export async function deleteNote(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    return mockDelay(undefined);
  }
  await apiClient.delete(`/anotaciones/api/notes/${id}`);
}

// ── Events ──

export async function fetchEvents(): Promise<CalendarEvent[]> {
  if (MOCK_ENABLED) {
    const now = new Date();
    const mockEvents: CalendarEvent[] = [
      {
        id: 'e1',
        title: 'Reunión de equipo',
        description: 'Weekly sync',
        start_datetime: new Date(now.getTime() + 86400000).toISOString(),
        is_all_day: false,
        color: '#7C3AED',
        location: 'Sala A',
      },
      {
        id: 'e2',
        title: 'Entrega de proyecto',
        start_datetime: new Date(now.getTime() + 172800000).toISOString(),
        is_all_day: true,
        color: '#EF4444',
      },
      {
        id: 'e3',
        title: 'Médico',
        start_datetime: new Date(now.getTime() + 259200000).toISOString(),
        is_all_day: false,
        color: '#10B981',
        location: 'Consultorio 3',
      },
    ];
    return mockDelay(mockEvents);
  }
  const { data } = await apiClient.get<CalendarEvent[]>('/eventos/api/events');
  return data;
}

export async function createEvent(event: Omit<CalendarEvent, 'id'>): Promise<CalendarEvent> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...event, id: generateId() });
  }
  const { data } = await apiClient.post<CalendarEvent>('/eventos/api/events', event);
  return data;
}

// ── Tags ──

export async function fetchTags(): Promise<Tag[]> {
  if (MOCK_ENABLED) {
    const tags: Tag[] = [
      { id: 't1', name: 'proyecto', color: '#7C3AED' },
      { id: 't2', name: 'cocina', color: '#F59E0B' },
      { id: 't3', name: 'lectura', color: '#10B981' },
      { id: 't4', name: 'python', color: '#3B82F6' },
      { id: 't5', name: 'ideas', color: '#EF4444' },
    ];
    return mockDelay(tags);
  }
  const { data } = await apiClient.get<Tag[]>('/anotaciones/api/tags');
  return data;
}

// ── Categories ──

export async function fetchCategories(): Promise<Category[]> {
  if (MOCK_ENABLED) {
    const categories: Category[] = [
      { id: 'c1', name: 'Alimentos', color: '#10B981', icon: 'shopping-cart' },
      { id: 'c2', name: 'Transporte', color: '#F59E0B', icon: 'car' },
      { id: 'c3', name: 'Vivienda', color: '#7C3AED', icon: 'home' },
      { id: 'c4', name: 'Entretenimiento', color: '#EF4444', icon: 'film' },
      { id: 'c5', name: 'Ingresos', color: '#3B82F6', icon: 'dollar-sign' },
    ];
    return mockDelay(categories);
  }
  const { data } = await apiClient.get<Category[]>('/finanzas/api/categories');
  return data;
}
