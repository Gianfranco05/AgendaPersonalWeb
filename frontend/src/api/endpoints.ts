import apiClient from './client';
import type {
  Transaction,
  Note,
  CalendarEvent,
  Tag,
  Category,
  FinanceSummary,
  Goal,
  TransactionsResponse,
  WorkoutSession,
  FitnessSummary,
  Meal,
  NutritionSummary,
  Task,
  HabitRecord,
  MonthlySummaryItem,
  Budget,
  BudgetProgress,
  FinanceReports,
  BankAccount,
  Settings,
  Session,
  Reminder,
  ModuleInfo,
  StoreCatalog,
  Subject,
  Exam,
  StudySummary,
  Book,
  BookStatus,
  LibrarySummary,
  MediaItem,
  MediaType,
  MediaStatus,
  MediaSummary,
  WorkOpportunity,
  OpportunityStatus,
  WorkSummary,
  FocusSession,
  FocusSummary,
  Trip,
  PackingItem,
  TravelSummary,
  Vehicle,
  MaintenanceRecord,
  VehicleSummary,
  Project,
  ProjectTask,
  ProjectsSummary,
} from '../types';

const MOCK_ENABLED = import.meta.env.VITE_MOCK_ENABLED === 'true';

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
      total_expenses: 870000,
      balance: 380000,
    });
  }
  const { data } = await apiClient.get<FinanceSummary>('/api/v1/finance/summary');
  return data;
}

// TransactionsResponse is now imported from '../types'

export async function fetchTransactions(params?: {
  page?: number;
  per_page?: number;
  type?: string;
  category?: string;
  date_from?: string;
  date_to?: string;
}): Promise<TransactionsResponse> {
  if (MOCK_ENABLED) {
    // Misma forma que la API real (category_id + valores del enum de
    // payment_method): un mock que devolvia category_name y etiquetas en
    // español escondio durante meses que el formulario real rompia con 500.
    const mockTransactions: Transaction[] = Array.from({ length: 25 }, (_, i) => ({
      id: generateId(),
      amount: Math.round(Math.random() * 500000) / 100,
      currency: i % 4 === 0 ? 'USD' : 'ARS',
      type: i % 3 === 0 ? 'income' : 'expense',
      transaction_date: new Date(2025, 5, 20 - i).toISOString().split('T')[0],
      product_name: `Transacción ${i + 1}`,
      merchant_name: ['Supermercado', 'Restaurante', 'Servicios', 'Freelance', 'Tienda'][i % 5],
      payment_method: ['cash', 'transfer', 'credit_card', 'debit_card'][i % 4],
      category_id: ['c1', 'c2', 'c3', 'c4', 'c5'][i % 5],
    }));
    return mockDelay({
      items: mockTransactions,
      total: 25,
      page: 1,
      page_size: 20,
    });
  }
  const { data } = await apiClient.get<TransactionsResponse>('/api/v1/finance/transactions', {
    params: {
      skip: params?.page ? (params.page - 1) * (params.per_page ?? 20) : 0,
      limit: params?.per_page ?? 20,
      ...(params?.type && { transaction_type: params.type }),
      ...(params?.category && { category_id: params.category }),
      ...(params?.date_from && { date_from: params.date_from }),
      ...(params?.date_to && { date_to: params.date_to }),
    },
  });
  return data;
}

export async function createTransaction(transaction: Record<string, unknown>): Promise<Transaction> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...transaction, id: generateId() } as Transaction);
  }
  const { data } = await apiClient.post<Transaction>('/api/v1/finance/transactions', {
    amount: transaction.amount,
    currency: transaction.currency ?? 'ARS',
    type: transaction.type,
    transaction_date: transaction.transaction_date,
    product_name: transaction.product_name,
    merchant_name: transaction.merchant_name ?? '',
    payment_method: transaction.payment_method ?? 'cash',
    account_type: 'cash',
    // `||` y no `??`: "Sin categoría" en el select es '' y la API espera
    // un UUID o null, no un string vacío.
    category_id: transaction.category_id || null,
    notes: transaction.notes ?? null,
  });
  return data;
}

export async function updateTransaction(id: string, transaction: Record<string, unknown>): Promise<Transaction> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...transaction, id } as Transaction);
  }
  const { data } = await apiClient.put<Transaction>(`/api/v1/finance/transactions/${id}`, {
    amount: transaction.amount,
    currency: transaction.currency,
    type: transaction.type,
    transaction_date: transaction.transaction_date,
    product_name: transaction.product_name,
    merchant_name: transaction.merchant_name,
    payment_method: transaction.payment_method,
    // null explícito = quitar la categoría (la API ahora lo respeta).
    category_id: transaction.category_id || null,
    // Solo si el llamador lo manda: el formulario web no tiene campo de
    // notas, y mandar null en cada edición borraría las cargadas desde mobile.
    ...('notes' in transaction && { notes: transaction.notes ?? null }),
  });
  return data;
}

export async function deleteTransaction(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    return mockDelay(undefined);
  }
  await apiClient.delete(`/api/v1/finance/transactions/${id}`);
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
  const { data } = await apiClient.get<Note[]>('/api/v1/notes');
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
  // La API recibe los tags como `tag_names: string[]`, no como objetos Tag:
  // mandar `tags` los descartaba en silencio.
  const { data } = await apiClient.post<Note>('/api/v1/notes', {
    title: note.title,
    content: note.content,
    color: note.color,
    is_pinned: note.is_pinned,
    tag_names: note.tags.map((t) => t.name),
  });
  return data;
}

export async function updateNote(id: string, note: Partial<Note>): Promise<Note> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...note, id } as Note);
  }
  const { tags, ...rest } = note;
  const { data } = await apiClient.put<Note>(`/api/v1/notes/${id}`, {
    title: rest.title,
    content: rest.content,
    color: rest.color,
    is_pinned: rest.is_pinned,
    is_archived: rest.is_archived,
    // Sin `tags` en la llamada, no se tocan (la API reemplaza la lista entera
    // cuando llega tag_names).
    ...(tags && { tag_names: tags.map((t) => t.name) }),
  });
  return data;
}

export async function deleteNote(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    return mockDelay(undefined);
  }
  await apiClient.delete(`/api/v1/notes/${id}`);
}

export async function exportNotesJson(): Promise<Blob> {
  if (MOCK_ENABLED) {
    return mockDelay(
      new Blob([JSON.stringify({ notes: [], format_version: 1 }, null, 2)], {
        type: 'application/json',
      }),
    );
  }
  const { data } = await apiClient.get<Blob>('/api/v1/notes/export/json', {
    responseType: 'blob',
  });
  return data;
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
  const { data } = await apiClient.get<CalendarEvent[]>('/api/v1/events');
  return data;
}

export async function createEvent(event: Omit<CalendarEvent, 'id'>): Promise<CalendarEvent> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...event, id: generateId() });
  }
  const { data } = await apiClient.post<CalendarEvent>('/api/v1/events', event);
  return data;
}

export async function updateEvent(id: string, event: Partial<CalendarEvent>): Promise<CalendarEvent> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...event, id } as CalendarEvent);
  }
  const { data } = await apiClient.put<CalendarEvent>(`/api/v1/events/${id}`, event);
  return data;
}

export async function deleteEvent(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    return mockDelay(undefined);
  }
  await apiClient.delete(`/api/v1/events/${id}`);
}

export async function exportEventsIcs(): Promise<Blob> {
  if (MOCK_ENABLED) {
    return mockDelay(
      new Blob(['BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR\n'], { type: 'text/calendar' }),
    );
  }
  const { data } = await apiClient.get<Blob>('/api/v1/events/export/ics', {
    responseType: 'blob',
  });
  return data;
}

// ── Goals ──

export async function fetchGoals(): Promise<Goal[]> {
  if (MOCK_ENABLED) {
    const mockGoals: Goal[] = [
      {
        id: 'g1',
        title: 'Leer 12 libros',
        description: 'Leer un libro por mes durante el año',
        goal_type: 'progress',
        target_value: 12,
        current_value: 5,
        unit: 'libros',
        end_date: '2026-12-31',
        color: '#7C3AED',
        icon: 'fa-bullseye',
        is_completed: false,
      },
      {
        id: 'g2',
        title: 'Correr 100 km',
        description: 'Correr 100 kilómetros en el mes',
        goal_type: 'progress',
        target_value: 100,
        current_value: 42,
        unit: 'km',
        end_date: '2026-07-31',
        color: '#10B981',
        icon: 'fa-bullseye',
        is_completed: false,
      },
      {
        id: 'g3',
        title: 'Meditar diariamente',
        description: 'Meditar al menos 10 minutos cada día',
        goal_type: 'binary',
        target_value: 1,
        current_value: 0,
        unit: null,
        end_date: '2026-07-01',
        color: '#3B82F6',
        icon: 'fa-bullseye',
        is_completed: false,
      },
    ];
    return mockDelay(mockGoals);
  }
  const { data } = await apiClient.get<Goal[]>('/api/v1/goals');
  return data;
}

export async function createGoal(goal: Record<string, unknown>): Promise<Goal> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...goal, id: generateId() } as Goal);
  }
  const { data } = await apiClient.post<Goal>('/api/v1/goals', {
    title: goal.title,
    description: goal.description || null,
    goal_type: goal.goal_type ?? 'binary',
    target_value: goal.target_value ?? 1,
    unit: goal.unit || null,
    color: goal.color ?? '#7C3AED',
    icon: goal.icon ?? 'fa-bullseye',
    end_date: goal.end_date || null,
  });
  return data;
}

export async function updateGoal(id: string, goal: Record<string, unknown>): Promise<Goal> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...goal, id } as Goal);
  }
  const { data } = await apiClient.put<Goal>(`/api/v1/goals/${id}`, {
    title: goal.title,
    description: goal.description,
    goal_type: goal.goal_type,
    target_value: goal.target_value,
    unit: goal.unit,
    color: goal.color,
    icon: goal.icon,
    end_date: goal.end_date,
  });
  return data;
}

export async function deleteGoal(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    return mockDelay(undefined);
  }
  await apiClient.delete(`/api/v1/goals/${id}`);
}

// El backend suma `value` a current_value, así que acá viaja el delta, no el total
export async function updateGoalProgress(id: string, delta: number): Promise<Goal> {
  if (MOCK_ENABLED) {
    return mockDelay({ id } as Goal);
  }
  const { data } = await apiClient.put<Goal>(`/api/v1/goals/${id}/checkin`, {
    value: delta,
    record_date: new Date().toISOString().split('T')[0],
  });
  return data;
}

// ── Habit records (registro diario de habitos tipo 'metric') ──

export async function fetchHabitRecords(
  goalId: string,
  year: number,
  month: number,
): Promise<HabitRecord[]> {
  if (MOCK_ENABLED) {
    return mockDelay([]);
  }
  const { data } = await apiClient.get<HabitRecord[]>(`/api/v1/goals/${goalId}/records`, {
    params: { year, month },
  });
  return data;
}

export async function upsertHabitRecord(
  goalId: string,
  recordDate: string,
  value: number,
  notes?: string | null,
): Promise<HabitRecord> {
  if (MOCK_ENABLED) {
    return mockDelay({ id: generateId(), goal_id: goalId, record_date: recordDate, value, notes: notes ?? null });
  }
  const { data } = await apiClient.post<HabitRecord>(`/api/v1/goals/${goalId}/records`, {
    record_date: recordDate,
    value,
    notes: notes ?? null,
  });
  return data;
}

export async function fetchMonthlySummary(year: number, month: number): Promise<MonthlySummaryItem[]> {
  if (MOCK_ENABLED) {
    return mockDelay([]);
  }
  const { data } = await apiClient.get<MonthlySummaryItem[]>('/api/v1/goals/summary/monthly', {
    params: { year, month },
  });
  return data;
}

// ── Tasks ──

export async function fetchTasks(params?: { area?: string; status?: string }): Promise<Task[]> {
  if (MOCK_ENABLED) {
    const mockTasks: Task[] = [
      { id: 'tk1', title: 'Enviar propuesta a cliente X', description: '', area: 'Trabajo', priority: 'alta', due_date: '2026-07-20', status: 'pending', order: 0 },
      { id: 'tk2', title: 'Revisar PR de backend', description: '', area: 'Trabajo', priority: 'media', due_date: null, status: 'in_progress', order: 0 },
      { id: 'tk3', title: 'Renovar DNI', description: '', area: 'Otras Tareas', priority: 'media', due_date: '2026-07-31', status: 'pending', order: 1 },
      { id: 'tk4', title: 'Comprar regalo cumpleaños', description: '', area: 'Otras Tareas', priority: 'baja', due_date: null, status: 'completed', order: 0 },
    ];
    let items = mockTasks;
    if (params?.area) items = items.filter((t) => t.area === params.area);
    if (params?.status) items = items.filter((t) => t.status === params.status);
    return mockDelay(items);
  }
  const { data } = await apiClient.get<Task[]>('/api/v1/tasks', { params });
  return data;
}

export async function createTask(task: Omit<Task, 'id'>): Promise<Task> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...task, id: generateId() });
  }
  const { data } = await apiClient.post<Task>('/api/v1/tasks', task);
  return data;
}

export async function updateTask(id: string, task: Partial<Task>): Promise<Task> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...task, id } as Task);
  }
  const { data } = await apiClient.patch<Task>(`/api/v1/tasks/${id}`, task);
  return data;
}

export async function deleteTask(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    return mockDelay(undefined);
  }
  await apiClient.delete(`/api/v1/tasks/${id}`);
}

export async function moveTask(id: string, status: Task['status'], order: number): Promise<Task> {
  if (MOCK_ENABLED) {
    return mockDelay({ id, status, order } as Task);
  }
  const { data } = await apiClient.post<Task>(`/api/v1/tasks/${id}/move`, { status, order });
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
  const { data } = await apiClient.get<Tag[]>('/api/v1/tags');
  return data;
}

// ── Fitness ──

// El backend usa title/session_date; la UI usa name/date. Mapeamos en la frontera.
function mapSessionFromApi(s: Record<string, unknown>): WorkoutSession {
  return {
    id: s.id as string,
    date: (s.session_date as string) ?? (s.date as string),
    name: (s.title as string) ?? (s.name as string),
    duration_minutes: (s.duration_minutes as number | null) ?? null,
    notes: (s.notes as string | null) ?? null,
    exercises: (s.exercises as WorkoutSession['exercises']) ?? [],
  };
}

function mapSessionToApi(session: Omit<WorkoutSession, 'id'>): Record<string, unknown> {
  return {
    title: session.name,
    session_date: session.date,
    duration_minutes: session.duration_minutes,
    notes: session.notes,
    exercises: (session.exercises ?? []).map((ex, i) => ({
      name: ex.name,
      sets: ex.sets,
      reps: ex.reps,
      weight_kg: ex.weight_kg,
      order: ex.order ?? i,
    })),
  };
}

export async function fetchFitnessSummary(): Promise<FitnessSummary> {
  if (MOCK_ENABLED) {
    return mockDelay({
      sessions_this_month: 8,
      total_exercises: 34,
      last_session_date: new Date().toISOString().split('T')[0],
    });
  }
  const { data } = await apiClient.get<FitnessSummary>('/api/v1/fitness/summary');
  return data;
}

export async function fetchWorkoutSessions(): Promise<WorkoutSession[]> {
  if (MOCK_ENABLED) {
    const mockSessions: WorkoutSession[] = [
      {
        id: 'ws1',
        date: new Date().toISOString().split('T')[0],
        name: 'Tren superior',
        duration_minutes: 60,
        notes: 'Buen ritmo',
        exercises: [
          { id: 'ex1', name: 'Press banca', sets: 4, reps: 8, weight_kg: 60, order: 0 },
          { id: 'ex2', name: 'Remo con barra', sets: 4, reps: 10, weight_kg: 50, order: 1 },
        ],
      },
      {
        id: 'ws2',
        date: new Date(Date.now() - 172800000).toISOString().split('T')[0],
        name: 'Piernas',
        duration_minutes: 50,
        notes: null,
        exercises: [
          { id: 'ex3', name: 'Sentadilla', sets: 5, reps: 5, weight_kg: 80, order: 0 },
        ],
      },
    ];
    return mockDelay(mockSessions);
  }
  const { data } = await apiClient.get<Record<string, unknown>[]>('/api/v1/fitness/sessions');
  return data.map(mapSessionFromApi);
}

export async function createWorkoutSession(
  session: Omit<WorkoutSession, 'id'>,
): Promise<WorkoutSession> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...session, id: generateId() });
  }
  const { data } = await apiClient.post<Record<string, unknown>>(
    '/api/v1/fitness/sessions',
    mapSessionToApi(session),
  );
  return mapSessionFromApi(data);
}

export async function updateWorkoutSession(
  id: string,
  session: Omit<WorkoutSession, 'id'>,
): Promise<WorkoutSession> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...session, id });
  }
  const { data } = await apiClient.put<Record<string, unknown>>(
    `/api/v1/fitness/sessions/${id}`,
    mapSessionToApi(session),
  );
  return mapSessionFromApi(data);
}

export async function deleteWorkoutSession(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    return mockDelay(undefined);
  }
  await apiClient.delete(`/api/v1/fitness/sessions/${id}`);
}

// ── Nutrition ──

// El backend usa meal_date; la UI usa date.
function mapMealFromApi(m: Record<string, unknown>): Meal {
  return {
    id: m.id as string,
    date: (m.meal_date as string) ?? (m.date as string),
    meal_type: m.meal_type as Meal['meal_type'],
    name: m.name as string,
    calories: (m.calories as number) ?? 0,
    protein_g: (m.protein_g as number) ?? 0,
    carbs_g: (m.carbs_g as number) ?? 0,
    fat_g: (m.fat_g as number) ?? 0,
  };
}

function mapMealToApi(meal: Omit<Meal, 'id'>): Record<string, unknown> {
  return {
    meal_date: meal.date,
    meal_type: meal.meal_type,
    name: meal.name,
    calories: meal.calories,
    protein_g: meal.protein_g,
    carbs_g: meal.carbs_g,
    fat_g: meal.fat_g,
  };
}

export async function fetchNutritionSummary(): Promise<NutritionSummary> {
  if (MOCK_ENABLED) {
    return mockDelay({
      today_calories: 1650,
      today_protein_g: 110,
      today_carbs_g: 160,
      today_fat_g: 55,
      week_calories: 11500,
      week_protein_g: 770,
      week_carbs_g: 1120,
      week_fat_g: 385,
    });
  }
  const { data } = await apiClient.get<NutritionSummary>('/api/v1/nutrition/summary');
  return data;
}

export async function fetchMeals(params?: {
  date_from?: string;
  date_to?: string;
}): Promise<Meal[]> {
  if (MOCK_ENABLED) {
    const today = new Date().toISOString().split('T')[0];
    const mockMeals: Meal[] = [
      { id: 'm1', date: today, meal_type: 'breakfast', name: 'Avena con frutas', calories: 350, protein_g: 15, carbs_g: 55, fat_g: 8 },
      { id: 'm2', date: today, meal_type: 'lunch', name: 'Pollo con arroz', calories: 620, protein_g: 45, carbs_g: 70, fat_g: 12 },
      { id: 'm3', date: today, meal_type: 'dinner', name: 'Ensalada con atún', calories: 420, protein_g: 35, carbs_g: 20, fat_g: 18 },
      { id: 'm4', date: today, meal_type: 'snack', name: 'Yogur con nueces', calories: 260, protein_g: 15, carbs_g: 15, fat_g: 17 },
    ];
    return mockDelay(mockMeals);
  }
  const { data } = await apiClient.get<Record<string, unknown>[]>('/api/v1/nutrition/meals', { params });
  return data.map(mapMealFromApi);
}

export async function createMeal(meal: Omit<Meal, 'id'>): Promise<Meal> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...meal, id: generateId() });
  }
  const { data } = await apiClient.post<Record<string, unknown>>(
    '/api/v1/nutrition/meals',
    mapMealToApi(meal),
  );
  return mapMealFromApi(data);
}

export async function updateMeal(id: string, meal: Omit<Meal, 'id'>): Promise<Meal> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...meal, id });
  }
  const { data } = await apiClient.put<Record<string, unknown>>(
    `/api/v1/nutrition/meals/${id}`,
    mapMealToApi(meal),
  );
  return mapMealFromApi(data);
}

export async function deleteMeal(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    return mockDelay(undefined);
  }
  await apiClient.delete(`/api/v1/nutrition/meals/${id}`);
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
  const { data } = await apiClient.get<Category[]>('/api/v1/finance/categories');
  return data;
}

export async function createCategory(category: Omit<Category, 'id'>): Promise<Category> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...category, id: generateId() });
  }
  const { data } = await apiClient.post<Category>('/api/v1/finance/categories', category);
  return data;
}

export async function updateCategory(id: string, category: Partial<Category>): Promise<Category> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...category, id } as Category);
  }
  const { data } = await apiClient.put<Category>(`/api/v1/finance/categories/${id}`, category);
  return data;
}

export async function deleteCategory(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    return mockDelay(undefined);
  }
  await apiClient.delete(`/api/v1/finance/categories/${id}`);
}

// ── Budgets ──

export async function fetchBudgets(year: number, month: number): Promise<BudgetProgress[]> {
  if (MOCK_ENABLED) {
    return mockDelay([]);
  }
  const { data } = await apiClient.get<BudgetProgress[]>('/api/v1/finance/budgets', {
    params: { year, month },
  });
  return data;
}

export async function createBudget(budget: Omit<Budget, 'id'>): Promise<Budget> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...budget, id: generateId() });
  }
  const { data } = await apiClient.post<Budget>('/api/v1/finance/budgets', budget);
  return data;
}

export async function updateBudget(id: string, budget: Partial<Budget>): Promise<Budget> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...budget, id } as Budget);
  }
  const { data } = await apiClient.put<Budget>(`/api/v1/finance/budgets/${id}`, budget);
  return data;
}

export async function deleteBudget(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    return mockDelay(undefined);
  }
  await apiClient.delete(`/api/v1/finance/budgets/${id}`);
}

// ── Finance Reports ──

export async function fetchFinanceReports(): Promise<FinanceReports> {
  if (MOCK_ENABLED) {
    const now = new Date();
    const monthly = Array.from({ length: 6 }).map((_, i) => {
      const d = new Date(now.getFullYear(), now.getMonth() - (5 - i), 1);
      return {
        month: d.toISOString().slice(0, 10),
        income: 200000 + i * 15000,
        expense: 120000 + i * 9000,
      };
    });
    const byCategory = [
      { name: 'Alimentos', color: '#10B981', total: 85000 },
      { name: 'Transporte', color: '#F59E0B', total: 32000 },
      { name: 'Vivienda', color: '#7C3AED', total: 150000 },
      { name: 'Entretenimiento', color: '#EF4444', total: 21000 },
    ];
    return mockDelay({
      by_category: byCategory,
      monthly,
      total_expenses: byCategory.reduce((sum, c) => sum + c.total, 0),
    });
  }
  const { data } = await apiClient.get<FinanceReports>('/api/v1/finance/reports');
  return data;
}

// ── Bank Accounts ──

export async function fetchBankAccounts(): Promise<BankAccount[]> {
  if (MOCK_ENABLED) {
    const accounts: BankAccount[] = [
      {
        id: 'a1',
        user_id: 'u1',
        created_at: new Date().toISOString(),
        name: 'Cuenta sueldo',
        bank_name: 'Banco Nación',
        account_type: 'checking',
        last4: '4821',
        currency: 'ARS',
        balance: 350000,
      },
      {
        id: 'a2',
        user_id: 'u1',
        created_at: new Date().toISOString(),
        name: 'Caja de ahorro',
        bank_name: 'Banco Galicia',
        account_type: 'savings',
        last4: '1092',
        currency: 'ARS',
        balance: 120000,
      },
    ];
    return mockDelay(accounts);
  }
  const { data } = await apiClient.get<BankAccount[]>('/api/v1/finance/accounts');
  return data;
}

export async function createBankAccount(
  account: Omit<BankAccount, 'id' | 'user_id' | 'created_at'>,
): Promise<BankAccount> {
  if (MOCK_ENABLED) {
    return mockDelay({
      ...account,
      id: generateId(),
      user_id: 'u1',
      created_at: new Date().toISOString(),
    });
  }
  const { data } = await apiClient.post<BankAccount>('/api/v1/finance/accounts', account);
  return data;
}

export async function updateBankAccount(
  id: string,
  account: Partial<BankAccount>,
): Promise<BankAccount> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...account, id } as BankAccount);
  }
  const { data } = await apiClient.put<BankAccount>(`/api/v1/finance/accounts/${id}`, account);
  return data;
}

export async function deleteBankAccount(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    return mockDelay(undefined);
  }
  await apiClient.delete(`/api/v1/finance/accounts/${id}`);
}

// ── Settings ──

export async function fetchSettings(): Promise<Settings> {
  if (MOCK_ENABLED) {
    return mockDelay({
      currency: 'ARS',
      theme_color: 'violet',
      date_format: 'DD/MM/YYYY',
      google_calendar_id: 'primary',
      google_connected: false,
    });
  }
  const { data } = await apiClient.get<Settings>('/api/v1/settings');
  return data;
}

export async function updateSettings(settings: Partial<Settings>): Promise<Settings> {
  if (MOCK_ENABLED) {
    return mockDelay(settings as Settings);
  }
  const { data } = await apiClient.put<Settings>('/api/v1/settings', settings);
  return data;
}

export async function syncGoogleCalendar(): Promise<{ synced: number }> {
  if (MOCK_ENABLED) {
    return mockDelay({ synced: 0 });
  }
  const { data } = await apiClient.post<{ synced: number }>('/api/v1/settings/google/sync');
  return data;
}

export async function disconnectGoogleCalendar(): Promise<Settings> {
  if (MOCK_ENABLED) {
    return mockDelay({
      currency: 'ARS',
      theme_color: 'violet',
      date_format: 'DD/MM/YYYY',
      google_calendar_id: 'primary',
      google_connected: false,
    });
  }
  const { data } = await apiClient.post<Settings>('/api/v1/settings/google/disconnect');
  return data;
}

// ── Cuenta (export y baja) ──

export async function exportMyData(): Promise<Blob> {
  if (MOCK_ENABLED) {
    return mockDelay(
      new Blob([JSON.stringify({ user: {}, format_version: 1 }, null, 2)], {
        type: 'application/json',
      }),
    );
  }
  // responseType blob: el export puede ser grande y se baja como archivo, no se
  // parsea a un objeto en memoria.
  const { data } = await apiClient.get<Blob>('/api/v1/me/export', {
    responseType: 'blob',
  });
  return data;
}

export async function deleteMyAccount(password: string): Promise<void> {
  if (MOCK_ENABLED) {
    await mockDelay(null);
    return;
  }
  // El backend pide la contraseña en el body para reautenticar antes de un
  // borrado irreversible; axios manda body en DELETE via `data`.
  await apiClient.delete('/api/v1/me', { data: { password } });
}

// ── Sessions ──

export async function fetchSessions(): Promise<Session[]> {
  if (MOCK_ENABLED) {
    return mockDelay([
      {
        id: generateId(),
        device_info: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0',
        created_at: new Date(Date.now() - 30 * 24 * 3600 * 1000).toISOString(),
        last_used_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 30 * 24 * 3600 * 1000).toISOString(),
      },
      {
        id: generateId(),
        device_info: 'okhttp/4.12.0 (Android 14)',
        created_at: new Date(Date.now() - 5 * 24 * 3600 * 1000).toISOString(),
        last_used_at: new Date(Date.now() - 2 * 3600 * 1000).toISOString(),
        expires_at: new Date(Date.now() + 25 * 24 * 3600 * 1000).toISOString(),
      },
    ]);
  }
  const { data } = await apiClient.get<Session[]>('/auth/api/sessions');
  return data;
}

export async function revokeSession(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    await mockDelay(null);
    return;
  }
  await apiClient.delete(`/auth/api/sessions/${id}`);
}

// ── Reminders ──

export async function fetchReminders(): Promise<Reminder[]> {
  if (MOCK_ENABLED) {
    return mockDelay([
      { id: generateId(), message: '¿Cargaste tus hábitos de hoy?', icon: '🔔', hour: 21, minute: 0, enabled: true },
    ]);
  }
  const { data } = await apiClient.get<Reminder[]>('/api/v1/reminders');
  return data;
}

export async function createReminder(
  input: Omit<Reminder, 'id'>,
): Promise<Reminder> {
  if (MOCK_ENABLED) {
    return mockDelay({ id: generateId(), ...input });
  }
  const { data } = await apiClient.post<Reminder>('/api/v1/reminders', input);
  return data;
}

export async function updateReminder(
  id: string,
  input: Partial<Omit<Reminder, 'id'>>,
): Promise<Reminder> {
  if (MOCK_ENABLED) {
    return mockDelay({
      id,
      message: '',
      icon: '🔔',
      hour: 9,
      minute: 0,
      enabled: true,
      ...input,
    });
  }
  const { data } = await apiClient.patch<Reminder>(`/api/v1/reminders/${id}`, input);
  return data;
}

export async function deleteReminder(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    await mockDelay(null);
    return;
  }
  await apiClient.delete(`/api/v1/reminders/${id}`);
}

// ── Módulos (plantillas) ──

const MOCK_MODULES: ModuleInfo[] = [
  { key: 'habits', label: 'Hábitos', description: 'Seguimiento diario de hábitos', icon: 'check_circle', is_base: true, owned: true, enabled: true, for_sale: false },
  { key: 'tasks', label: 'Tareas', description: 'Tareas y tablero por estado', icon: 'task_alt', is_base: true, owned: true, enabled: true, for_sale: false },
  { key: 'notes', label: 'Notas y Documentos', description: 'Notas rápidas y adjuntos', icon: 'description', is_base: true, owned: true, enabled: true, for_sale: false },
  { key: 'finance', label: 'Finanzas Personales', description: 'Ingresos, gastos y balance', icon: 'payments', is_base: true, owned: true, enabled: true, for_sale: false },
  { key: 'fitness_nutrition', label: 'Rutinas y Dietas', description: 'Entrenamiento y nutrición', icon: 'fitness_center', is_base: true, owned: true, enabled: true, for_sale: false },
  { key: 'calendar', label: 'Calendario y Eventos', description: 'Agenda y eventos', icon: 'calendar_today', is_base: true, owned: true, enabled: true, for_sale: false },
  { key: 'study', label: 'Estudio & Universidad', description: 'Materias, exámenes y promedio', icon: 'school', is_base: false, owned: true, enabled: true, for_sale: true },
  { key: 'library', label: 'Biblioteca & Lecturas', description: 'Libros leídos y pendientes, con puntaje', icon: 'menu_book', is_base: false, owned: false, enabled: false, for_sale: true },
  { key: 'media', label: 'Películas & Series', description: 'Lo que viste y lo que querés ver, con puntaje', icon: 'movie', is_base: false, owned: false, enabled: false, for_sale: true },
  { key: 'work', label: 'Trabajo & Carrera', description: 'Tareas laborales, reuniones y pipeline', icon: 'work', is_base: false, owned: false, enabled: false, for_sale: true },
  { key: 'travel', label: 'Viajes & Equipaje', description: 'Itinerarios, reservas y checklist de equipaje', icon: 'flight', is_base: false, owned: false, enabled: false, for_sale: true },
  { key: 'vehicle', label: 'Vehículo & Mantenimiento', description: 'Combustible, revisiones técnicas e ITV', icon: 'directions_car', is_base: false, owned: false, enabled: false, for_sale: true },
  { key: 'projects', label: 'Gestión de Proyectos', description: 'Tableros Kanban, sprints y entregables', icon: 'view_kanban', is_base: false, owned: false, enabled: false, for_sale: true },
];

export async function fetchModules(): Promise<ModuleInfo[]> {
  if (MOCK_ENABLED) {
    return mockDelay(MOCK_MODULES.map((m) => ({ ...m })));
  }
  const { data } = await apiClient.get<ModuleInfo[]>('/api/v1/modules');
  return data;
}

export async function toggleModule(key: string, enabled: boolean): Promise<ModuleInfo> {
  if (MOCK_ENABLED) {
    const mock = MOCK_MODULES.find((m) => m.key === key);
    return mockDelay({ ...(mock as ModuleInfo), enabled });
  }
  const { data } = await apiClient.put<ModuleInfo>(`/api/v1/modules/${key}`, { enabled });
  return data;
}

// ── Tienda (compra de plantillas) ──

export async function fetchStore(): Promise<StoreCatalog> {
  if (MOCK_ENABLED) {
    return mockDelay({
      billing_enabled: true,
      items: MOCK_MODULES.filter((m) => !m.is_base).map((m) => ({
        key: m.key,
        label: m.label,
        description: m.description,
        icon: m.icon,
        owned: m.owned,
        amount: m.owned ? null : 199900,
        currency: m.owned ? null : 'ars',
      })),
    });
  }
  const { data } = await apiClient.get<StoreCatalog>('/api/v1/billing/store');
  return data;
}

// Pensado solo para web: no se manda `app_redirect` (eso es exclusivo del
// flujo mobile con deep link), así el backend arma success/cancel URLs HTTPS
// normales con BILLING_SUCCESS_URL / PUBLIC_BASE_URL.
export async function createCheckout(moduleKey: string): Promise<{ url: string }> {
  if (MOCK_ENABLED) {
    return mockDelay({ url: `${window.location.origin}/store?checkout=ok` });
  }
  const { data } = await apiClient.post<{ url: string }>('/api/v1/billing/checkout', null, {
    params: { module: moduleKey },
  });
  return data;
}

// ── Botón de arrepentimiento (público: no requiere sesión) ──

export interface WithdrawalRequestInput {
  full_name: string;
  email: string;
  purchase_detail: string;
  message?: string;
}

export interface WithdrawalRequestResult {
  code: string;
  created_at: string;
}

export async function createWithdrawalRequest(
  input: WithdrawalRequestInput,
): Promise<WithdrawalRequestResult> {
  if (MOCK_ENABLED) {
    return mockDelay({ code: 'ARR-MOCK23', created_at: new Date().toISOString() });
  }
  const { data } = await apiClient.post<WithdrawalRequestResult>('/api/v1/arrepentimiento', input);
  return data;
}

// ── Travel (plantilla de pago: /travel requiere haber comprado el módulo) ──

export async function fetchTrips(): Promise<Trip[]> {
  if (MOCK_ENABLED) {
    return mockDelay([]);
  }
  const { data } = await apiClient.get<Trip[]>('/api/v1/travel/trips');
  return data;
}

export async function createTrip(input: Partial<Trip>): Promise<Trip> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...input, id: generateId() } as Trip);
  }
  const { data } = await apiClient.post<Trip>('/api/v1/travel/trips', input);
  return data;
}

export async function updateTrip(id: string, input: Partial<Trip>): Promise<Trip> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...input, id } as Trip);
  }
  const { data } = await apiClient.patch<Trip>(`/api/v1/travel/trips/${id}`, input);
  return data;
}

export async function deleteTrip(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    return mockDelay(undefined);
  }
  await apiClient.delete(`/api/v1/travel/trips/${id}`);
}

export async function fetchPackingItems(tripId: string): Promise<PackingItem[]> {
  if (MOCK_ENABLED) {
    return mockDelay([]);
  }
  const { data } = await apiClient.get<PackingItem[]>(`/api/v1/travel/trips/${tripId}/items`);
  return data;
}

export async function addPackingItem(tripId: string, name: string): Promise<PackingItem> {
  if (MOCK_ENABLED) {
    return mockDelay({ id: generateId(), trip_id: tripId, name, packed: false });
  }
  const { data } = await apiClient.post<PackingItem>(`/api/v1/travel/trips/${tripId}/items`, { name });
  return data;
}

export async function setPackingItemPacked(id: string, packed: boolean): Promise<PackingItem> {
  if (MOCK_ENABLED) {
    return mockDelay({ id, packed } as PackingItem);
  }
  const { data } = await apiClient.patch<PackingItem>(`/api/v1/travel/items/${id}`, { packed });
  return data;
}

export async function deletePackingItem(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    return mockDelay(undefined);
  }
  await apiClient.delete(`/api/v1/travel/items/${id}`);
}

export async function fetchTravelSummary(): Promise<TravelSummary> {
  if (MOCK_ENABLED) {
    return mockDelay({ total: 0, planeados: 0, completados: 0, next_trip: null });
  }
  const { data } = await apiClient.get<TravelSummary>('/api/v1/travel/summary');
  return data;
}

// ── Vehicle (plantilla de pago: /vehicle requiere haber comprado el módulo) ──

export async function fetchVehicles(): Promise<Vehicle[]> {
  if (MOCK_ENABLED) {
    return mockDelay([]);
  }
  const { data } = await apiClient.get<Vehicle[]>('/api/v1/vehicle/vehicles');
  return data;
}

export async function createVehicle(input: Partial<Vehicle>): Promise<Vehicle> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...input, id: generateId() } as Vehicle);
  }
  const { data } = await apiClient.post<Vehicle>('/api/v1/vehicle/vehicles', input);
  return data;
}

export async function updateVehicle(id: string, input: Partial<Vehicle>): Promise<Vehicle> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...input, id } as Vehicle);
  }
  const { data } = await apiClient.patch<Vehicle>(`/api/v1/vehicle/vehicles/${id}`, input);
  return data;
}

export async function deleteVehicle(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    return mockDelay(undefined);
  }
  await apiClient.delete(`/api/v1/vehicle/vehicles/${id}`);
}

// El backend no tiene PATCH para records: solo se crean o se borran.
export async function fetchMaintenanceRecords(vehicleId?: string): Promise<MaintenanceRecord[]> {
  if (MOCK_ENABLED) {
    return mockDelay([]);
  }
  const { data } = await apiClient.get<MaintenanceRecord[]>('/api/v1/vehicle/records', {
    params: vehicleId ? { vehicle_id: vehicleId } : undefined,
  });
  return data;
}

// ── Study (plantilla de pago) ──

export async function fetchSubjects(): Promise<Subject[]> {
  if (MOCK_ENABLED) {
    return mockDelay([
      { id: 'sub1', name: 'Álgebra II', professor: 'Prof. Gómez', color: '#6366F1', status: 'cursando' },
      { id: 'sub2', name: 'Física I', professor: null, color: '#F59E0B', status: 'aprobada' },
      { id: 'sub3', name: 'Programación III', professor: 'Prof. Ruiz', color: '#10B981', status: 'pendiente' },
    ]);
  }
  const { data } = await apiClient.get<Subject[]>('/api/v1/study/subjects');
  return data;
}

export async function createSubject(subject: Partial<Subject>): Promise<Subject> {
  if (MOCK_ENABLED) {
    return mockDelay({
      id: generateId(),
      name: subject.name ?? '',
      professor: subject.professor ?? null,
      color: subject.color ?? '#6366F1',
      status: subject.status ?? 'cursando',
    });
  }
  const { data } = await apiClient.post<Subject>('/api/v1/study/subjects', subject);
  return data;
}

export async function updateSubject(id: string, subject: Partial<Subject>): Promise<Subject> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...subject, id } as Subject);
  }
  const { data } = await apiClient.patch<Subject>(`/api/v1/study/subjects/${id}`, subject);
  return data;
}

export async function deleteSubject(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    return mockDelay(undefined);
  }
  await apiClient.delete(`/api/v1/study/subjects/${id}`);
}

export async function fetchExams(params?: { upcoming?: boolean }): Promise<Exam[]> {
  if (MOCK_ENABLED) {
    const today = new Date().toISOString().split('T')[0];
    const mockExams: Exam[] = [
      { id: 'ex1', subject_id: 'sub1', title: 'Primer parcial', exam_date: today, grade: null, notes: null },
      { id: 'ex2', subject_id: 'sub2', title: 'Final', exam_date: '2026-03-10', grade: 8.5, notes: null },
    ];
    if (params?.upcoming) {
      return mockDelay(mockExams.filter((e) => e.exam_date >= today));
    }
    return mockDelay(mockExams);
  }
  const { data } = await apiClient.get<Exam[]>('/api/v1/study/exams', { params });
  return data;
}

export async function createExam(exam: Partial<Exam>): Promise<Exam> {
  if (MOCK_ENABLED) {
    return mockDelay({
      id: generateId(),
      subject_id: exam.subject_id ?? '',
      title: exam.title ?? '',
      exam_date: exam.exam_date ?? new Date().toISOString().split('T')[0],
      grade: exam.grade ?? null,
      notes: exam.notes ?? null,
    });
  }
  const { data } = await apiClient.post<Exam>('/api/v1/study/exams', exam);
  return data;
}

export async function updateExam(id: string, exam: Partial<Exam>): Promise<Exam> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...exam, id } as Exam);
  }
  const { data } = await apiClient.patch<Exam>(`/api/v1/study/exams/${id}`, exam);
  return data;
}

export async function deleteExam(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    return mockDelay(undefined);
  }
  await apiClient.delete(`/api/v1/study/exams/${id}`);
}

export async function fetchStudySummary(): Promise<StudySummary> {
  if (MOCK_ENABLED) {
    return mockDelay({
      subjects_total: 3,
      subjects_cursando: 1,
      subjects_aprobadas: 1,
      average_grade: 8.5,
      next_exam: null,
      upcoming_count: 0,
    });
  }
  const { data } = await apiClient.get<StudySummary>('/api/v1/study/summary');
  return data;
}

// ── Library / Biblioteca (plantilla de pago) ──

export async function fetchBooks(params?: { status?: BookStatus }): Promise<Book[]> {
  if (MOCK_ENABLED) {
    const mockBooks: Book[] = [
      {
        id: 'bk1', title: 'Rayuela', author: 'Julio Cortázar', status: 'leido', rating: 4.5,
        pages: 640, notes: null, started_date: null, finished_date: null,
      },
      {
        id: 'bk2', title: 'Sapiens', author: 'Yuval Noah Harari', status: 'leyendo', rating: null,
        pages: 450, notes: null, started_date: null, finished_date: null,
      },
    ];
    return mockDelay(params?.status ? mockBooks.filter((b) => b.status === params.status) : mockBooks);
  }
  const { data } = await apiClient.get<Book[]>('/api/v1/library/books', { params });
  return data;
}

export async function createBook(book: Partial<Book>): Promise<Book> {
  if (MOCK_ENABLED) {
    return mockDelay({
      id: generateId(),
      title: book.title ?? '',
      author: book.author ?? null,
      status: book.status ?? 'pendiente',
      rating: book.rating ?? null,
      pages: book.pages ?? null,
      notes: book.notes ?? null,
      started_date: book.started_date ?? null,
      finished_date: book.finished_date ?? null,
    });
  }
  const { data } = await apiClient.post<Book>('/api/v1/library/books', book);
  return data;
}

export async function updateBook(id: string, book: Partial<Book>): Promise<Book> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...book, id } as Book);
  }
  const { data } = await apiClient.patch<Book>(`/api/v1/library/books/${id}`, book);
  return data;
}

export async function deleteBook(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    return mockDelay(undefined);
  }
  await apiClient.delete(`/api/v1/library/books/${id}`);
}

export async function fetchLibrarySummary(): Promise<LibrarySummary> {
  if (MOCK_ENABLED) {
    return mockDelay({ total: 2, pendientes: 0, leyendo: 1, leidos: 1, average_rating: 4.5 });
  }
  const { data } = await apiClient.get<LibrarySummary>('/api/v1/library/summary');
  return data;
}

// ── Media / Películas y series (plantilla de pago) ──

export async function fetchMediaItems(params?: {
  status?: MediaStatus;
  media_type?: MediaType;
}): Promise<MediaItem[]> {
  if (MOCK_ENABLED) {
    let mockItems: MediaItem[] = [
      { id: 'md1', title: 'Interstellar', media_type: 'pelicula', status: 'visto', rating: 5, year: 2014, notes: null },
      { id: 'md2', title: 'Breaking Bad', media_type: 'serie', status: 'viendo', rating: null, year: 2008, notes: null },
    ];
    if (params?.status) mockItems = mockItems.filter((i) => i.status === params.status);
    if (params?.media_type) mockItems = mockItems.filter((i) => i.media_type === params.media_type);
    return mockDelay(mockItems);
  }
  const { data } = await apiClient.get<MediaItem[]>('/api/v1/media/items', { params });
  return data;
}

export async function createMediaItem(item: Partial<MediaItem>): Promise<MediaItem> {
  if (MOCK_ENABLED) {
    return mockDelay({
      id: generateId(),
      title: item.title ?? '',
      media_type: item.media_type ?? 'pelicula',
      status: item.status ?? 'pendiente',
      rating: item.rating ?? null,
      year: item.year ?? null,
      notes: item.notes ?? null,
    });
  }
  const { data } = await apiClient.post<MediaItem>('/api/v1/media/items', item);
  return data;
}

export async function updateMediaItem(id: string, item: Partial<MediaItem>): Promise<MediaItem> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...item, id } as MediaItem);
  }
  const { data } = await apiClient.patch<MediaItem>(`/api/v1/media/items/${id}`, item);
  return data;
}

export async function deleteMediaItem(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    return mockDelay(undefined);
  }
  await apiClient.delete(`/api/v1/media/items/${id}`);
}

export async function fetchMediaSummary(): Promise<MediaSummary> {
  if (MOCK_ENABLED) {
    return mockDelay({ total: 2, pendientes: 0, viendo: 1, vistos: 1, average_rating: 5 });
  }
  const { data } = await apiClient.get<MediaSummary>('/api/v1/media/summary');
  return data;
}

// ── Work / Trabajo y carrera (plantilla de pago) ──

export async function fetchOpportunities(params?: { status?: OpportunityStatus }): Promise<WorkOpportunity[]> {
  if (MOCK_ENABLED) {
    const mockOpportunities: WorkOpportunity[] = [
      {
        id: 'wk1', company: 'Acme', role: 'Backend Developer', status: 'entrevista',
        salary: 1500000, applied_date: '2026-08-01', notes: null,
      },
      {
        id: 'wk2', company: 'Globex', role: 'Fullstack Developer', status: 'aplicado',
        salary: null, applied_date: '2026-08-20', notes: null,
      },
    ];
    return mockDelay(
      params?.status ? mockOpportunities.filter((o) => o.status === params.status) : mockOpportunities,
    );
  }
  const { data } = await apiClient.get<WorkOpportunity[]>('/api/v1/work/opportunities', { params });
  return data;
}

export async function createOpportunity(opportunity: Partial<WorkOpportunity>): Promise<WorkOpportunity> {
  if (MOCK_ENABLED) {
    return mockDelay({
      id: generateId(),
      company: opportunity.company ?? '',
      role: opportunity.role ?? '',
      status: opportunity.status ?? 'aplicado',
      salary: opportunity.salary ?? null,
      applied_date: opportunity.applied_date ?? null,
      notes: opportunity.notes ?? null,
    });
  }
  const { data } = await apiClient.post<WorkOpportunity>('/api/v1/work/opportunities', opportunity);
  return data;
}

export async function updateOpportunity(
  id: string,
  opportunity: Partial<WorkOpportunity>,
): Promise<WorkOpportunity> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...opportunity, id } as WorkOpportunity);
  }
  const { data } = await apiClient.patch<WorkOpportunity>(`/api/v1/work/opportunities/${id}`, opportunity);
  return data;
}

export async function deleteOpportunity(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    return mockDelay(undefined);
  }
  await apiClient.delete(`/api/v1/work/opportunities/${id}`);
}

export async function fetchWorkSummary(): Promise<WorkSummary> {
  if (MOCK_ENABLED) {
    return mockDelay({ total: 2, active: 2, entrevista: 1, oferta: 0, aceptado: 0 });
  }
  const { data } = await apiClient.get<WorkSummary>('/api/v1/work/summary');
  return data;
}

// ── Focus / Enfoque (gratis, sin gate de módulo) ──

export async function fetchFocusSummary(): Promise<FocusSummary> {
  if (MOCK_ENABLED) {
    return mockDelay({ today_seconds: 3600, week_seconds: 14400, active: null });
  }
  // Minutos al este de UTC: getTimezoneOffset() de JS usa el signo opuesto
  // (positivo al oeste), por eso se invierte antes de mandarlo.
  const tzOffsetMinutes = -new Date().getTimezoneOffset();
  const { data } = await apiClient.get<FocusSummary>('/api/v1/focus/summary', {
    params: { tz_offset_minutes: tzOffsetMinutes },
  });
  return data;
}

export async function createMaintenanceRecord(
  input: Partial<MaintenanceRecord>,
): Promise<MaintenanceRecord> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...input, id: generateId() } as MaintenanceRecord);
  }
  const { data } = await apiClient.post<MaintenanceRecord>('/api/v1/vehicle/records', input);
  return data;
}

export async function deleteMaintenanceRecord(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    return mockDelay(undefined);
  }
  await apiClient.delete(`/api/v1/vehicle/records/${id}`);
}

export async function fetchVehicleSummary(): Promise<VehicleSummary> {
  if (MOCK_ENABLED) {
    return mockDelay({ vehicles_total: 0, records_total: 0, total_spent: 0, last_record: null });
  }
  const { data } = await apiClient.get<VehicleSummary>('/api/v1/vehicle/summary');
  return data;
}

// ── Projects (plantilla de pago: /projects requiere haber comprado el módulo) ──

export async function fetchProjects(): Promise<Project[]> {
  if (MOCK_ENABLED) {
    return mockDelay([]);
  }
  const { data } = await apiClient.get<Project[]>('/api/v1/projects');
  return data;
}

export async function createProject(input: Partial<Project>): Promise<Project> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...input, id: generateId() } as Project);
  }
  const { data } = await apiClient.post<Project>('/api/v1/projects', input);
  return data;
}

export async function updateProject(id: string, input: Partial<Project>): Promise<Project> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...input, id } as Project);
  }
  const { data } = await apiClient.patch<Project>(`/api/v1/projects/${id}`, input);
  return data;
}

export async function deleteProject(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    return mockDelay(undefined);
  }
  await apiClient.delete(`/api/v1/projects/${id}`);
}

export async function fetchProjectTasks(projectId?: string): Promise<ProjectTask[]> {
  if (MOCK_ENABLED) {
    return mockDelay([]);
  }
  const { data } = await apiClient.get<ProjectTask[]>('/api/v1/projects/tasks', {
    params: projectId ? { project_id: projectId } : undefined,
  });
  return data;
}

export async function fetchFocusSessions(params?: { limit?: number }): Promise<FocusSession[]> {
  if (MOCK_ENABLED) {
    return mockDelay([
      {
        id: 'fc1',
        started_at: new Date(Date.now() - 3600_000).toISOString(),
        ended_at: new Date(Date.now() - 1800_000).toISOString(),
        duration_seconds: 1800,
        label: 'Informe mensual',
      },
    ]);
  }
  const { data } = await apiClient.get<FocusSession[]>('/api/v1/focus/sessions', { params });
  return data;
}

export async function startFocusSession(label?: string): Promise<FocusSession> {
  if (MOCK_ENABLED) {
    return mockDelay({
      id: generateId(),
      started_at: new Date().toISOString(),
      ended_at: null,
      duration_seconds: null,
      label: label ?? null,
    });
  }
  const { data } = await apiClient.post<FocusSession>('/api/v1/focus/start', label ? { label } : {});
  return data;
}

export async function stopFocusSession(): Promise<FocusSession> {
  if (MOCK_ENABLED) {
    return mockDelay({
      id: generateId(),
      started_at: new Date(Date.now() - 60_000).toISOString(),
      ended_at: new Date().toISOString(),
      duration_seconds: 60,
      label: null,
    });
  }
  const { data } = await apiClient.post<FocusSession>('/api/v1/focus/stop');
  return data;
}

export async function deleteFocusSession(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    return mockDelay(undefined);
  }
  await apiClient.delete(`/api/v1/focus/sessions/${id}`);
}

export async function createProjectTask(input: Partial<ProjectTask>): Promise<ProjectTask> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...input, id: generateId() } as ProjectTask);
  }
  const { data } = await apiClient.post<ProjectTask>('/api/v1/projects/tasks', input);
  return data;
}

export async function updateProjectTask(
  id: string,
  input: Partial<ProjectTask>,
): Promise<ProjectTask> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...input, id } as ProjectTask);
  }
  const { data } = await apiClient.patch<ProjectTask>(`/api/v1/projects/tasks/${id}`, input);
  return data;
}

export async function deleteProjectTask(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    return mockDelay(undefined);
  }
  await apiClient.delete(`/api/v1/projects/tasks/${id}`);
}

export async function fetchProjectsSummary(): Promise<ProjectsSummary> {
  if (MOCK_ENABLED) {
    return mockDelay({
      projects_total: 0,
      projects_active: 0,
      tasks_pending: 0,
      tasks_in_progress: 0,
      tasks_done: 0,
    });
  }
  const { data } = await apiClient.get<ProjectsSummary>('/api/v1/projects/summary');
  return data;
}
