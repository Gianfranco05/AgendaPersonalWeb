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
  Settings,
  Session,
  Reminder,
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
    category_id: transaction.category_id ?? null,
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
    category_id: transaction.category_id ?? null,
    notes: transaction.notes ?? null,
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
  const { data } = await apiClient.post<Note>('/api/v1/notes', note);
  return data;
}

export async function updateNote(id: string, note: Partial<Note>): Promise<Note> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...note, id } as Note);
  }
  const { data } = await apiClient.put<Note>(`/api/v1/notes/${id}`, note);
  return data;
}

export async function deleteNote(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    return mockDelay(undefined);
  }
  await apiClient.delete(`/api/v1/notes/${id}`);
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
