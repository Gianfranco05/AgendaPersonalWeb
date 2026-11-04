import apiClient from './client';
import { CURRENT_ONBOARDING_VERSION } from '../components/Onboarding/steps';
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
  FinanceExportParams,
  FinanceExportFile,
  ImportPreset,
  ImportPreview,
  ImportBatch,
  ImportMappingUpdate,
  ImportConfirmRow,
  ParsedImportRow,
  Settings,
  Session,
  Reminder,
  HabitReminderSettings,
  HabitReminderToday,
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
  Investment,
  InvestmentInput,
  InvestmentSummary,
  InvestmentCurrency,
  NetWorth,
  MarketFx,
  FxQuote,
  InflationSeries,
  CryptoAsset,
  RealReturn,
  PortfolioRealReturn,
  AssetType,
  Recurring,
  RecurringDetail,
  RecurringInput,
  RecurringRule,
  RecurringPreview,
  Occurrence,
  Upcoming,
  ConfirmOccurrenceInput,
  RenewFixedTermInput,
  RenewResult,
  RenewalChain,
  RenewalTerm,
  SearchType,
  SearchItem,
  SearchGroup,
  SearchResponse,
} from '../types';
import { parseDateOnly, toLocalDateString } from '../utils/date';
import { nextRuleDates, ruleLabel } from '../utils/recurring';
import { foldText, highlightRanges, matchRank, tokenize } from '../utils/search';
import { enrichInvestment, MOCK_CRYPTO_PRICES, MOCK_MONTHLY_INFLATION } from '../utils/investments';

const MOCK_ENABLED = import.meta.env.VITE_MOCK_ENABLED === 'true';

function generateId(): string {
  return Math.random().toString(36).substring(2, 15);
}

function mockDelay<T>(data: T): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(data), 300));
}

// ── Finance ──

// La API serializa los Decimal de plata como string ("1500.50"). Con el string
// a secas, `toLocaleString('es-AR')` no formatea y los totales salían como
// "$50000.00" en vez de "$50.000". Se convierten a number en la frontera.
function num(value: unknown): number {
  return typeof value === 'number' ? value : Number(value);
}

function mapTransaction(t: Transaction): Transaction {
  return { ...t, amount: num(t.amount) };
}

function mapBudget<T extends Budget>(b: T): T {
  return { ...b, amount: num(b.amount) };
}

function mapBankAccount(a: BankAccount): BankAccount {
  return { ...a, balance: num(a.balance) };
}


// "Hoy" del usuario para los resúmenes del server: sin esto el backend usa su
// fecha UTC y en Argentina el día cambia a las 21:00. Minutos al este de UTC;
// getTimezoneOffset() usa el signo opuesto, por eso se invierte.
function tzOffsetMinutes(): number {
  return -new Date().getTimezoneOffset();
}

// Decimal opcional de la API: null se queda null (no es 0) y ausente, ausente.
function numOrNull(value: unknown): number | null {
  return value === null || value === undefined ? null : num(value);
}

export async function fetchFinanceSummary(): Promise<FinanceSummary> {
  if (MOCK_ENABLED) {
    const net = mockNetWorth();
    return mockDelay({
      total_income: 1250000,
      total_expenses: 870000,
      balance: 380000,
      investments_value_ars: net.investments.total_ars,
      net_worth_ars: net.net_worth_ars,
      investments_missing_rates: net.investments.total_ars === null ? net.investments.missing_rates : [],
      include_investments_in_balance: net.include_investments_in_balance,
    });
  }
  const { data } = await apiClient.get<FinanceSummary>('/api/v1/finance/summary', {
    params: { tz_offset_minutes: tzOffsetMinutes() },
  });
  return {
    total_income: num(data.total_income),
    total_expenses: num(data.total_expenses),
    balance: num(data.balance),
    // Los campos de inversiones son aditivos: un server viejo no los manda.
    ...(data.investments_value_ars !== undefined && {
      investments_value_ars: numOrNull(data.investments_value_ars),
    }),
    ...(data.net_worth_ars !== undefined && { net_worth_ars: numOrNull(data.net_worth_ars) }),
    ...(data.investments_missing_rates !== undefined && {
      investments_missing_rates: data.investments_missing_rates,
    }),
    ...(data.include_investments_in_balance !== undefined && {
      include_investments_in_balance: data.include_investments_in_balance,
    }),
  };
}

// TransactionsResponse is now imported from '../types'

export async function fetchTransactions(params?: {
  page?: number;
  per_page?: number;
  type?: string;
  category?: string;
  date_from?: string;
  date_to?: string;
  recurrence_id?: string;
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
      ...(params?.recurrence_id && { recurrence_id: params.recurrence_id }),
    },
  });
  return { ...data, items: data.items.map(mapTransaction) };
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
  return mapTransaction(data);
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
  return mapTransaction(data);
}

export async function deleteTransaction(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    return mockDelay(undefined);
  }
  await apiClient.delete(`/api/v1/finance/transactions/${id}`);
}

// ── Notes ──

/** `includeArchived`: el buscador puede llevar a una nota archivada, que la lista normal no trae. */
export async function fetchNotes(includeArchived = false): Promise<Note[]> {
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
  const { data } = await apiClient.get<Note[]>('/api/v1/notes', {
    params: includeArchived ? { include_archived: true } : undefined,
  });
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
  // El POST de la API ignora is_pinned (solo lo respeta el PUT): una nota que
  // se fija antes del primer guardado quedaba sin fijar.
  if (note.is_pinned && !data.is_pinned) {
    const { data: pinned } = await apiClient.put<Note>(`/api/v1/notes/${data.id}`, { is_pinned: true });
    return pinned;
  }
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
        reminder_enabled: true,
        reminder_time: null,
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
    reminder_enabled: goal.reminder_enabled ?? true,
    reminder_time: goal.reminder_time || null,
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
    // Solo se mandan si vienen: una meta numérica no toca los avisos del hábito.
    ...('reminder_enabled' in goal && { reminder_enabled: goal.reminder_enabled }),
    ...('reminder_time' in goal && { reminder_time: goal.reminder_time || null }),
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
    record_date: toLocalDateString(),
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
  const { data } = await apiClient.get<Tag[]>('/api/v1/notes/tags');
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
  const { data } = await apiClient.get<FitnessSummary>('/api/v1/fitness/summary', {
    params: { tz_offset_minutes: tzOffsetMinutes() },
  });
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
  const { data } = await apiClient.get<NutritionSummary>('/api/v1/nutrition/summary', {
    params: { tz_offset_minutes: tzOffsetMinutes() },
  });
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
  return data.map((b) => ({ ...mapBudget(b), spent: num(b.spent), remaining: num(b.remaining) }));
}

export async function createBudget(budget: Omit<Budget, 'id'>): Promise<Budget> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...budget, id: generateId() });
  }
  const { data } = await apiClient.post<Budget>('/api/v1/finance/budgets', budget);
  return mapBudget(data);
}

export async function updateBudget(id: string, budget: Partial<Budget>): Promise<Budget> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...budget, id } as Budget);
  }
  const { data } = await apiClient.put<Budget>(`/api/v1/finance/budgets/${id}`, budget);
  return mapBudget(data);
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
  return {
    by_category: data.by_category.map((c) => ({ ...c, total: num(c.total) })),
    monthly: data.monthly.map((m) => ({ ...m, income: num(m.income), expense: num(m.expense) })),
    total_expenses: num(data.total_expenses),
  };
}

// ── Exportar / importar Finanzas ──

function filenameFromDisposition(header: unknown, fallback: string): string {
  const match = typeof header === 'string' ? /filename="?([^";]+)"?/i.exec(header) : null;
  return match?.[1] ?? fallback;
}

export async function downloadFinanceExport(params: FinanceExportParams): Promise<FinanceExportFile> {
  const fallback = `cancen-finanzas.${params.format}`;
  if (MOCK_ENABLED) {
    const mime =
      params.format === 'pdf'
        ? 'application/pdf'
        : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
    return mockDelay({ blob: new Blob(['mock'], { type: mime }), filename: fallback });
  }
  const response = await apiClient.get<Blob>('/api/v1/finance/export', {
    params: { ...params, tz_offset_minutes: tzOffsetMinutes() },
    responseType: 'blob',
    // Generar un PDF o un Excel grande tarda más que los 15 s del cliente.
    timeout: 120000,
  });
  return {
    blob: response.data,
    filename: filenameFromDisposition(response.headers['content-disposition'], fallback),
  };
}

const MOCK_IMPORT_PRESETS: ImportPreset[] = [
  {
    key: 'mercadopago_release',
    label: 'Mercado Pago · Dinero disponible',
    description: 'Reporte de dinero disponible de Mercado Pago, en .csv o .xlsx.',
    required_fields: ['Fecha', 'Tipo de registro', 'Crédito neto', 'Débito neto'],
  },
  {
    key: 'mercadopago_account_money',
    label: 'Mercado Pago · Dinero en cuenta',
    description: 'Reporte de dinero en cuenta de Mercado Pago, en .csv o .xlsx.',
    required_fields: ['Fecha de la transacción', 'Tipo de transacción', 'Monto neto'],
  },
  {
    key: 'generic',
    label: 'Otro banco o billetera (CSV/Excel)',
    description: 'Cualquier archivo con fecha, descripción y monto.',
    required_fields: ['Fecha', 'Monto, o Débito y Crédito'],
  },
];

export async function fetchImportPresets(): Promise<ImportPreset[]> {
  if (MOCK_ENABLED) return mockDelay(MOCK_IMPORT_PRESETS);
  const { data } = await apiClient.get<ImportPreset[]>('/api/v1/finance/imports/presets');
  return data;
}

function mockImportPreview(filename: string): ImportPreview {
  const base = {
    time: null,
    currency: 'ARS',
    reference: '',
    errors: [],
    row_hash: 'x',
    duplicate_of: null,
    suggested_category_id: null,
    suggestion_source: 'none' as const,
    merchant_category: 'other',
  };
  const rows: ParsedImportRow[] = [
    { ...base, index: 0, source_line: 2, date: '2026-10-01', description: 'Compra Coto', amount: '1234.56', type: 'expense', status: 'ok' },
    { ...base, index: 1, source_line: 3, date: '2026-10-02', description: 'Sueldo', amount: '250000.00', type: 'income', status: 'ok' },
    { ...base, index: 2, source_line: 4, date: '2026-10-03', description: 'Netflix', amount: '8500.00', type: 'expense', status: 'ok', suggestion_source: 'rule', merchant_category: 'entertainment' },
    { ...base, index: 3, source_line: 5, date: '2026-10-04', description: 'Uber', amount: '3200.00', type: 'expense', status: 'ok' },
    { ...base, index: 4, source_line: 6, date: '2026-10-05', description: 'Farmacity', amount: '5400.00', type: 'expense', status: 'ok' },
    {
      ...base, index: 5, source_line: 7, date: '2026-10-06', description: 'Compra Coto', amount: '1234.56',
      type: 'expense', status: 'duplicate', errors: ['Ya importado.'],
      duplicate_of: { id: 'm1', date: '2026-10-06', description: 'Compra Coto' },
    },
    {
      ...base, index: 6, source_line: 8, date: '2026-10-07', description: 'Retiro cajero', amount: '20000.00',
      type: 'expense', status: 'possible_duplicate', errors: ['Se parece a un movimiento que ya tenés.'],
      duplicate_of: { id: 'm2', date: '2026-10-07', description: 'Cajero automático' },
    },
    {
      ...base, index: 7, source_line: 9, date: null, description: 'Fila rota', amount: null, type: null,
      currency: null, status: 'error', errors: ['Fecha: fecha inválida'],
    },
  ];
  return {
    batch_id: 'mock-batch',
    preset: 'generic',
    detected_preset: 'generic',
    mapping: {
      date: 0, time: null, description: [1], amount_mode: 'signed', amount: 2, fallback_amount: null,
      debit: null, credit: null, type_column: null, type_values: {}, currency: null,
      default_currency: 'ARS', reference: null, include_when: null, skip_when: null, translations: {},
      date_format: 'auto', decimal_separator: 'auto', invert_sign: false, tz_offset_minutes: -180,
    },
    mapping_source: 'heuristic',
    mapping_complete: true,
    headers: ['Fecha', 'Descripción', 'Importe'],
    header_row: 0,
    sample_rows: [['01/10/2026', 'Compra Coto', '-1.234,56']],
    rows,
    counts: { ok: 5, error: 1, duplicate: 1, possible_duplicate: 1, skipped: 0 },
    totals_by_currency: [{ currency: 'ARS', income: '250000.00', expense: '19334.56', count: 5 }],
    warnings: [],
    expires_at: null,
    filename,
    account_id: null,
  };
}

export async function previewImport(
  file: File,
  opts: { preset?: string; account_id?: string } = {},
): Promise<ImportPreview> {
  if (MOCK_ENABLED) return mockDelay(mockImportPreview(file.name));
  const form = new FormData();
  form.append('file', file);
  if (opts.preset && opts.preset !== 'auto') form.append('preset', opts.preset);
  if (opts.account_id) form.append('account_id', opts.account_id);
  form.append('tz_offset_minutes', String(tzOffsetMinutes()));
  // El cliente trae 'application/json' por defecto: sin pisarlo axios serializa el
  // FormData como JSON y el server responde "Field required". Con 'multipart/form-data'
  // axios lo suelta y el navegador arma el boundary.
  const { data } = await apiClient.post<ImportPreview>('/api/v1/finance/imports/preview', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  });
  return data;
}

export async function updateImportMapping(
  batchId: string,
  update: ImportMappingUpdate,
): Promise<ImportPreview> {
  if (MOCK_ENABLED) return mockDelay(mockImportPreview('mock.csv'));
  const { data } = await apiClient.put<ImportPreview>(`/api/v1/finance/imports/${batchId}/mapping`, {
    ...update,
    tz_offset_minutes: tzOffsetMinutes(),
  });
  return data;
}

function mockImportBatch(over: Partial<ImportBatch> = {}): ImportBatch {
  return {
    id: 'mock-batch', status: 'confirmed', preset: 'generic', filename: 'movimientos.csv', account_id: null,
    row_count: 8, imported_count: 5, skipped_count: 0, duplicate_count: 1, error_count: 1, edited_count: 0,
    created_at: new Date().toISOString(), confirmed_at: new Date().toISOString(), undone_at: null, ...over,
  };
}

export async function confirmImport(batchId: string, rows: ImportConfirmRow[]): Promise<ImportBatch> {
  if (MOCK_ENABLED) {
    const included = rows.filter((r) => r.include).length;
    return mockDelay(mockImportBatch({ id: batchId, status: 'confirmed', imported_count: included }));
  }
  const { data } = await apiClient.post<ImportBatch>(`/api/v1/finance/imports/${batchId}/confirm`, { rows });
  return data;
}

export async function fetchImports(): Promise<ImportBatch[]> {
  if (MOCK_ENABLED) return mockDelay([mockImportBatch()]);
  const { data } = await apiClient.get<ImportBatch[]>('/api/v1/finance/imports', { params: { limit: 20 } });
  return data;
}

/** Deshace un lote confirmado (borra sus movimientos). */
export async function undoImport(batchId: string): Promise<ImportBatch> {
  if (MOCK_ENABLED) {
    return mockDelay(mockImportBatch({ id: batchId, status: 'undone', undone_at: new Date().toISOString() }));
  }
  const { data } = await apiClient.delete<ImportBatch>(`/api/v1/finance/imports/${batchId}`);
  return data;
}

/** Descarta una previsualización (no crea nada). */
export async function discardImportPreview(batchId: string): Promise<void> {
  if (MOCK_ENABLED) return mockDelay(undefined);
  await apiClient.delete(`/api/v1/finance/imports/${batchId}`);
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
  return data.map(mapBankAccount);
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
  return mapBankAccount(data);
}

export async function updateBankAccount(
  id: string,
  account: Partial<BankAccount>,
): Promise<BankAccount> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...account, id } as BankAccount);
  }
  const { data } = await apiClient.put<BankAccount>(`/api/v1/finance/accounts/${id}`, account);
  return mapBankAccount(data);
}

export async function deleteBankAccount(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    return mockDelay(undefined);
  }
  await apiClient.delete(`/api/v1/finance/accounts/${id}`);
}

// ── Settings ──

// Las cotizaciones llegan como string ("1450.5000"): se pasan a number en la frontera.
function mapSettings(data: Settings): Settings {
  return {
    ...data,
    ...(data.fx_usd_ars !== undefined && { fx_usd_ars: numOrNull(data.fx_usd_ars) }),
    ...(data.fx_eur_ars !== undefined && { fx_eur_ars: numOrNull(data.fx_eur_ars) }),
  };
}

// Estado del modo mock: las cotizaciones y el toggle sobreviven entre pantallas.
let mockSettingsState: Settings = {
  currency: 'ARS',
  theme_color: 'violet',
  date_format: 'DD/MM/YYYY',
  google_calendar_id: 'primary',
  google_connected: false,
  fx_usd_ars: null,
  fx_eur_ars: null,
  fx_rates_updated_at: null,
  fx_usd_source: 'mep',
  fx_eur_source: 'oficial',
  include_investments_in_balance: false,
  // Visto: el modo mock no muestra el tutorial (tests y demos no lo esperan).
  onboarding_version_seen: CURRENT_ONBOARDING_VERSION,
};

export async function fetchSettings(): Promise<Settings> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...mockSettingsState });
  }
  const { data } = await apiClient.get<Settings>('/api/v1/settings');
  return mapSettings(data);
}

export async function updateSettings(settings: Partial<Settings>): Promise<Settings> {
  if (MOCK_ENABLED) {
    const ratesChanged =
      ('fx_usd_ars' in settings && settings.fx_usd_ars !== mockSettingsState.fx_usd_ars) ||
      ('fx_eur_ars' in settings && settings.fx_eur_ars !== mockSettingsState.fx_eur_ars);
    // Como el server: el tutorial visto nunca baja.
    const onboardingSeen = Math.max(
      mockSettingsState.onboarding_version_seen ?? 0,
      settings.onboarding_version_seen ?? 0,
    );
    mockSettingsState = {
      ...mockSettingsState,
      ...settings,
      onboarding_version_seen: onboardingSeen,
      ...(ratesChanged && { fx_rates_updated_at: new Date().toISOString() }),
    };
    return mockDelay({ ...mockSettingsState });
  }
  const { data } = await apiClient.put<Settings>('/api/v1/settings', settings);
  return mapSettings(data);
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
  return mapSettings(data);
}

// ── Inversiones ──

// La API serializa los Decimal como string; fecha y hora de "hoy" las pone el
// server a partir de tz_offset_minutes (minutos al este de UTC).
function mapProjection<T extends { nominal_pct: number; inflation_pct: number; real_pct: number }>(p: T): T {
  return { ...p, nominal_pct: num(p.nominal_pct), inflation_pct: num(p.inflation_pct), real_pct: num(p.real_pct) };
}

function mapRealReturn(r: RealReturn | null): RealReturn | null {
  if (!r) return null;
  return {
    ...mapProjection(r),
    projected_at_maturity: r.projected_at_maturity ? mapProjection(r.projected_at_maturity) : null,
  };
}

function mapPortfolioReal(r: PortfolioRealReturn | null | undefined): PortfolioRealReturn | null {
  return r ? mapProjection(r) : null;
}

function mapInvestment(i: Investment): Investment {
  return {
    ...i,
    quantity: numOrNull(i.quantity),
    invested_amount: num(i.invested_amount),
    current_value: numOrNull(i.current_value),
    interest_rate_tna: numOrNull(i.interest_rate_tna),
    effective_value: num(i.effective_value),
    gain: num(i.gain),
    gain_pct: numOrNull(i.gain_pct),
    ...(i.last_price !== undefined && { last_price: numOrNull(i.last_price) }),
    ...(i.real_return !== undefined && { real_return: mapRealReturn(i.real_return) }),
    fixed_term: i.fixed_term
      ? {
          ...i.fixed_term,
          interest_total: num(i.fixed_term.interest_total),
          amount_at_maturity: num(i.fixed_term.amount_at_maturity),
          accrued_interest: num(i.fixed_term.accrued_interest),
          tea_pct: num(i.fixed_term.tea_pct),
        }
      : null,
  };
}

function mapInvestmentSummary(s: InvestmentSummary): InvestmentSummary {
  return {
    ...s,
    by_currency: s.by_currency.map((c) => ({
      ...c,
      invested: num(c.invested),
      current_value: num(c.current_value),
      gain: num(c.gain),
    })),
    by_type: s.by_type.map((t) => ({ ...t, value_ars: numOrNull(t.value_ars) })),
    total_ars: numOrNull(s.total_ars),
    total_usd: numOrNull(s.total_usd),
    upcoming_maturities: s.upcoming_maturities.map((u) => ({ ...u, amount: num(u.amount) })),
    ...(s.real_return_ars !== undefined && { real_return_ars: mapPortfolioReal(s.real_return_ars) }),
  };
}

function mapNetWorth(n: NetWorth): NetWorth {
  return {
    ...n,
    cash_balance_ars: num(n.cash_balance_ars),
    cash_balance_usd: numOrNull(n.cash_balance_usd),
    investments: mapInvestmentSummary(n.investments),
    net_worth_ars: numOrNull(n.net_worth_ars),
    net_worth_usd: numOrNull(n.net_worth_usd),
    rates: {
      ...n.rates,
      usd_ars: numOrNull(n.rates.usd_ars),
      eur_ars: numOrNull(n.rates.eur_ars),
      ...(n.rates.usd_buy !== undefined && { usd_buy: numOrNull(n.rates.usd_buy) }),
      ...(n.rates.eur_buy !== undefined && { eur_buy: numOrNull(n.rates.eur_buy) }),
    },
  };
}

// Mock: una cartera en memoria con la misma forma que la API real. Create,
// update y delete la modifican, así que el flujo completo funciona sin backend.
type MockInvestmentBase = Parameters<typeof enrichInvestment>[0];

function isoDaysFromToday(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return toLocalDateString(d);
}

function mockBase(overrides: Partial<MockInvestmentBase> & Pick<MockInvestmentBase, 'id' | 'asset_type' | 'name' | 'currency' | 'invested_amount'>): MockInvestmentBase {
  return {
    ticker: null,
    quantity: null,
    current_value: null,
    interest_rate_tna: null,
    start_date: null,
    maturity_date: null,
    institution: null,
    notes: null,
    status: 'active',
    notify_maturity: true,
    value_updated_at: null,
    ...overrides,
  };
}

let mockInvestmentBases: MockInvestmentBase[] = [
  mockBase({
    id: 'mock-inv-1',
    asset_type: 'fixed_term',
    name: 'Plazo fijo Galicia',
    currency: 'ARS',
    invested_amount: 1000000,
    interest_rate_tna: 30,
    start_date: isoDaysFromToday(-12),
    maturity_date: isoDaysFromToday(18),
    institution: 'Banco Galicia',
  }),
  mockBase({
    id: 'mock-inv-2',
    asset_type: 'stock',
    name: 'Apple CEDEAR',
    ticker: 'AAPL',
    currency: 'ARS',
    quantity: 10,
    invested_amount: 150000,
    current_value: 172500,
    institution: 'Balanz',
  }),
  mockBase({
    id: 'mock-inv-3',
    asset_type: 'fx',
    name: 'Dólares billete',
    currency: 'USD',
    quantity: 2000,
    invested_amount: 1800,
    current_value: 2000,
  }),
];

function mockQuoteFields(source: string | undefined, ticker: string | null | undefined) {
  if (source !== 'coingecko') return { price_source: 'manual' as const, last_price: null, last_price_at: null };
  const price = ticker ? MOCK_CRYPTO_PRICES[ticker.toUpperCase()] : undefined;
  return {
    price_source: 'coingecko' as const,
    last_price: price ?? null,
    last_price_at: price === undefined ? null : new Date().toISOString(),
  };
}

// Renovaciones del mock: {id renovado -> id de su renovación} y la inversa.
const mockRenewals = new Map<string, string>();
const mockRenewedFrom = new Map<string, string>();

function addLocalDays(d: Date, days: number): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate() + days);
}

function withRenewalFields(i: Investment): Investment {
  const renewedTo = mockRenewals.get(i.id) ?? null;
  return {
    ...i,
    renewed_from_id: mockRenewedFrom.get(i.id) ?? null,
    renewed_to_id: renewedTo,
    can_renew:
      i.asset_type === 'fixed_term' &&
      i.status === 'active' &&
      i.days_to_maturity !== null &&
      i.days_to_maturity <= 0 &&
      renewedTo === null,
  };
}

function mockInvestmentList(status: 'active' | 'closed' | 'all' = 'active'): Investment[] {
  return mockInvestmentBases
    .filter((b) => status === 'all' || b.status === status)
    .map((b) => withRenewalFields(enrichInvestment(b)))
    .sort(
      (a, b) =>
        a.asset_type.localeCompare(b.asset_type) ||
        (a.maturity_date ?? '9999').localeCompare(b.maturity_date ?? '9999') ||
        a.name.localeCompare(b.name),
    );
}

// Mock del mercado: cotizaciones fijas "de hoy" (las mismas que se vieron en DolarAPI).
function mockMarketQuote(
  kind: FxQuote['kind'],
  buy: number,
  sell: number,
  minutesAgo = 12,
): FxQuote {
  const label = kind === 'mep' ? 'MEP' : kind === 'blue' ? 'Blue' : 'Oficial';
  return {
    kind,
    label,
    buy,
    sell,
    provider: 'dolarapi',
    as_of: new Date(Date.now() - minutesAgo * 60_000).toISOString(),
    stale: false,
  };
}

function mockMarketFx(): MarketFx {
  return {
    usd: [
      mockMarketQuote('oficial', 1500, 1550),
      mockMarketQuote('mep', 1557.4, 1563.9),
      mockMarketQuote('blue', 1545, 1565),
    ],
    eur: [mockMarketQuote('oficial', 1700.07, 1713.96), mockMarketQuote('blue', 1662, 1698)],
    last_success_at: new Date(Date.now() - 12 * 60_000).toISOString(),
    degraded: false,
  };
}

/** Cotización efectiva del modo mock según la fuente elegida. */
function mockEffectiveRates(): NetWorth['rates'] {
  const market = mockMarketFx();
  const resolve = (
    quotes: FxQuote[],
    source: string,
    manual: number | null,
  ): { rate: number | null; buy: number | null; effective: NetWorth['rates']['usd_effective_source']; asOf: string | null; provider: string | null } => {
    if (source === 'manual') {
      return { rate: manual, buy: null, effective: manual === null ? null : 'manual', asOf: mockSettingsState.fx_rates_updated_at ?? null, provider: null };
    }
    const q = quotes.find((x) => x.kind === source);
    return q
      ? { rate: q.sell, buy: q.buy, effective: q.kind, asOf: q.as_of, provider: q.provider }
      : { rate: manual, buy: null, effective: manual === null ? null : 'manual_fallback', asOf: null, provider: null };
  };
  const usdSource = mockSettingsState.fx_usd_source ?? 'mep';
  const eurSource = mockSettingsState.fx_eur_source ?? 'oficial';
  const usd = resolve(market.usd, usdSource, mockSettingsState.fx_usd_ars ?? null);
  const eur = resolve(market.eur, eurSource, mockSettingsState.fx_eur_ars ?? null);
  return {
    usd_ars: usd.rate,
    eur_ars: eur.rate,
    updated_at: usd.asOf,
    usd_source: usdSource,
    usd_effective_source: usd.effective,
    usd_buy: usd.buy,
    usd_provider: usd.provider,
    usd_as_of: usd.asOf,
    usd_stale: false,
    eur_source: eurSource,
    eur_effective_source: eur.effective,
    eur_buy: eur.buy,
    eur_provider: eur.provider,
    eur_as_of: eur.asOf,
    eur_stale: false,
  };
}

function mockPortfolioReal(active: Investment[]): PortfolioRealReturn | null {
  const items = active.filter((i) => i.real_return);
  if (items.length === 0) return null;
  const invested = items.reduce((a, i) => a + i.invested_amount, 0);
  const value = items.reduce((a, i) => a + i.effective_value, 0);
  const inflated = items.reduce((a, i) => a + i.invested_amount * (1 + i.real_return!.inflation_pct / 100), 0);
  const r2 = (n: number) => Math.round(n * 100) / 100;
  return {
    nominal_pct: r2((value / invested - 1) * 100),
    inflation_pct: r2((inflated / invested - 1) * 100),
    real_pct: r2((value / inflated - 1) * 100),
    estimated: items.some((i) => i.real_return!.estimated),
    included_count: items.length,
    excluded_count: active.filter((i) => i.currency === 'ARS').length - items.length,
  };
}

function mockInvestmentSummary(): InvestmentSummary {
  const effective = mockEffectiveRates();
  const rates = { usd: effective.usd_ars, eur: effective.eur_ars };
  const active = mockInvestmentList('active');
  const order: InvestmentCurrency[] = ['ARS', 'USD', 'USDT', 'EUR'];
  const sub = new Map<InvestmentCurrency, { invested: number; value: number; count: number }>();
  for (const i of active) {
    const cur = sub.get(i.currency) ?? { invested: 0, value: 0, count: 0 };
    cur.invested += i.invested_amount;
    cur.value += i.effective_value;
    cur.count += 1;
    sub.set(i.currency, cur);
  }
  const has = (c: InvestmentCurrency) => sub.has(c);
  const hasUsd = has('USD') || has('USDT');
  const usdLike = (sub.get('USD')?.value ?? 0) + (sub.get('USDT')?.value ?? 0);
  const ars = sub.get('ARS')?.value ?? 0;
  const eur = sub.get('EUR')?.value ?? 0;
  const missing: string[] = [];
  if (rates.usd === null && (hasUsd || has('ARS') || has('EUR'))) missing.push('USD');
  if (rates.eur === null && has('EUR')) missing.push('EUR');
  const totalArs =
    (hasUsd && rates.usd === null) || (has('EUR') && rates.eur === null)
      ? null
      : Math.round((ars + usdLike * (rates.usd ?? 0) + eur * (rates.eur ?? 0)) * 100) / 100;
  const totalUsd =
    ((has('ARS') || has('EUR')) && rates.usd === null) || (has('EUR') && rates.eur === null)
      ? null
      : Math.round((usdLike + (rates.usd ? (ars + eur * (rates.eur ?? 0)) / rates.usd : 0)) * 100) / 100;
  const byType = new Map<AssetType, { count: number; ars: number | null }>();
  for (const i of active) {
    const rate = i.currency === 'ARS' ? 1 : i.currency === 'EUR' ? rates.eur : rates.usd;
    const t = byType.get(i.asset_type) ?? { count: 0, ars: 0 };
    t.count += 1;
    t.ars = t.ars === null || rate === null ? null : t.ars + i.effective_value * rate;
    byType.set(i.asset_type, t);
  }
  return {
    by_currency: order
      .filter(has)
      .map((c) => {
        const v = sub.get(c)!;
        return {
          currency: c,
          invested: v.invested,
          current_value: v.value,
          gain: Math.round((v.value - v.invested) * 100) / 100,
          count: v.count,
        };
      }),
    by_type: [...byType.entries()].map(([asset_type, t]) => ({
      asset_type,
      count: t.count,
      value_ars: t.ars === null ? null : Math.round(t.ars * 100) / 100,
    })),
    total_ars: totalArs,
    total_usd: totalUsd,
    missing_rates: missing,
    count_active: active.length,
    real_return_ars: mockPortfolioReal(active),
    upcoming_maturities: active
      .filter((i) => i.days_to_maturity !== null && i.days_to_maturity >= 0 && i.days_to_maturity <= 30)
      .sort((a, b) => a.days_to_maturity! - b.days_to_maturity!)
      .slice(0, 5)
      .map((i) => ({
        id: i.id,
        name: i.name,
        asset_type: i.asset_type,
        currency: i.currency,
        maturity_date: i.maturity_date!,
        days_to_maturity: i.days_to_maturity!,
        amount: i.fixed_term ? i.fixed_term.amount_at_maturity : i.effective_value,
      })),
  };
}

function mockNetWorth(): NetWorth {
  const investments = mockInvestmentSummary();
  const mockRates = mockEffectiveRates();
  const usd = mockRates.usd_ars;
  const cash = 380000;
  const cashUsd = usd ? Math.round((cash / usd) * 100) / 100 : null;
  const missing = [...investments.missing_rates];
  if (usd === null && !missing.includes('USD')) missing.unshift('USD');
  return {
    cash_balance_ars: cash,
    cash_balance_usd: cashUsd,
    investments,
    net_worth_ars: investments.total_ars === null ? null : Math.round((cash + investments.total_ars) * 100) / 100,
    net_worth_usd:
      cashUsd === null || investments.total_usd === null
        ? null
        : Math.round((cashUsd + investments.total_usd) * 100) / 100,
    rates: mockRates,
    missing_rates: missing,
    include_investments_in_balance: mockSettingsState.include_investments_in_balance ?? false,
  };
}

export async function fetchInvestments(
  params: { status?: 'active' | 'closed' | 'all'; asset_type?: AssetType } = {},
): Promise<Investment[]> {
  if (MOCK_ENABLED) {
    return mockDelay(
      mockInvestmentList(params.status).filter((i) => !params.asset_type || i.asset_type === params.asset_type),
    );
  }
  const { data } = await apiClient.get<Investment[]>('/api/v1/finance/investments', {
    params: {
      ...(params.status && { status: params.status }),
      ...(params.asset_type && { asset_type: params.asset_type }),
      tz_offset_minutes: tzOffsetMinutes(),
    },
  });
  return data.map(mapInvestment);
}

export async function fetchInvestment(id: string): Promise<Investment> {
  if (MOCK_ENABLED) {
    const found = mockInvestmentList('all').find((i) => i.id === id);
    if (!found) throw new Error('Inversión no encontrada');
    return mockDelay(found);
  }
  const { data } = await apiClient.get<Investment>(`/api/v1/finance/investments/${id}`, {
    params: { tz_offset_minutes: tzOffsetMinutes() },
  });
  return mapInvestment(data);
}

export async function fetchInvestmentSummary(): Promise<InvestmentSummary> {
  if (MOCK_ENABLED) {
    return mockDelay(mockInvestmentSummary());
  }
  const { data } = await apiClient.get<InvestmentSummary>('/api/v1/finance/investments/summary', {
    params: { tz_offset_minutes: tzOffsetMinutes() },
  });
  return mapInvestmentSummary(data);
}

export async function fetchNetWorth(): Promise<NetWorth> {
  if (MOCK_ENABLED) {
    return mockDelay(mockNetWorth());
  }
  const { data } = await apiClient.get<NetWorth>('/api/v1/finance/net-worth', {
    params: { tz_offset_minutes: tzOffsetMinutes() },
  });
  return mapNetWorth(data);
}

export async function createInvestment(input: InvestmentInput): Promise<Investment> {
  if (MOCK_ENABLED) {
    const base: MockInvestmentBase = {
      ...input,
      id: `mock-inv-${generateId()}`,
      status: 'active',
      value_updated_at: input.current_value !== null ? new Date().toISOString() : null,
      ...mockQuoteFields(input.price_source, input.ticker),
    };
    mockInvestmentBases = [...mockInvestmentBases, base];
    return mockDelay(enrichInvestment(base));
  }
  const { data } = await apiClient.post<Investment>('/api/v1/finance/investments', {
    ...input,
    timezone_offset_minutes: tzOffsetMinutes(),
  });
  return mapInvestment(data);
}

export async function updateInvestment(
  id: string,
  input: Partial<InvestmentInput> & { status?: 'active' | 'closed' },
): Promise<Investment> {
  if (MOCK_ENABLED) {
    const current = mockInvestmentBases.find((b) => b.id === id);
    if (!current) throw new Error('Inversión no encontrada');
    const next = {
      ...current,
      ...input,
      ...('price_source' in input ? mockQuoteFields(input.price_source, input.ticker ?? current.ticker) : {}),
    };
    if ('current_value' in input && input.current_value !== current.current_value) {
      next.value_updated_at = input.current_value === null ? null : new Date().toISOString();
    }
    mockInvestmentBases = mockInvestmentBases.map((b) => (b.id === id ? next : b));
    return mockDelay(enrichInvestment(next));
  }
  const { data } = await apiClient.put<Investment>(`/api/v1/finance/investments/${id}`, {
    ...input,
    timezone_offset_minutes: tzOffsetMinutes(),
  });
  return mapInvestment(data);
}

export async function deleteInvestment(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    mockInvestmentBases = mockInvestmentBases.filter((b) => b.id !== id);
    return mockDelay(undefined);
  }
  await apiClient.delete(`/api/v1/finance/investments/${id}`);
}

// ── Movimientos recurrentes ──

function mapRecurring<T extends Recurring>(r: T): T {
  return { ...r, amount: numOrNull(r.amount), last_amount: numOrNull(r.last_amount) };
}

function mapOccurrence(o: Occurrence): Occurrence {
  return {
    ...o,
    suggested_amount: numOrNull(o.suggested_amount),
    ...(o.transaction ? { transaction: mapTransaction(o.transaction) } : {}),
  };
}

function mapUpcoming(u: Upcoming): Upcoming {
  return {
    ...u,
    items: u.items.map((i) => ({ ...i, amount: numOrNull(i.amount) })),
    totals: u.totals.map((t) => ({ ...t, total: num(t.total) })),
  };
}

// Mock: plantillas y pendientes en memoria con la misma forma que la API. La
// generación automática es cosa del server: acá solo se simula el alta, el
// ciclo de vida y la confirmación.
let mockRecurring: Recurring[] = [
  {
    id: 'mock-rec-1',
    type: 'income',
    name: 'Sueldo',
    description: null,
    notes: null,
    amount: 850000,
    currency: 'ARS',
    category_id: null,
    bank_account_id: null,
    account_type: 'cash',
    payment_method: 'transfer',
    merchant_name: '',
    merchant_category: 'other',
    frequency: 'monthly',
    interval_count: 1,
    weekday: null,
    day_of_month: 5,
    month_of_year: null,
    start_date: '2026-01-01',
    end_date: null,
    anchor_date: '2026-01-05',
    next_occurrence_date: nextRuleDates(
      { frequency: 'monthly', interval_count: 1, weekday: null, day_of_month: 5, month_of_year: null },
      '2026-01-01',
      toLocalDateString(),
      1,
    )[0],
    last_occurrence_date: null,
    status: 'active',
    requires_confirmation: false,
    notify: true,
    timezone_offset_minutes: -180,
    state: 'active',
    rule_label: 'Todos los meses el día 5',
    pending_count: 0,
    last_amount: 850000,
  },
  {
    id: 'mock-rec-2',
    type: 'expense',
    name: 'Luz',
    description: null,
    notes: null,
    amount: 25000,
    currency: 'ARS',
    category_id: null,
    bank_account_id: null,
    account_type: 'cash',
    payment_method: 'cash',
    merchant_name: '',
    merchant_category: 'utilities',
    frequency: 'monthly',
    interval_count: 2,
    weekday: null,
    day_of_month: 15,
    month_of_year: null,
    start_date: '2026-01-01',
    end_date: null,
    anchor_date: '2026-01-15',
    next_occurrence_date: nextRuleDates(
      { frequency: 'monthly', interval_count: 2, weekday: null, day_of_month: 15, month_of_year: null },
      '2026-01-01',
      toLocalDateString(),
      1,
    )[0],
    last_occurrence_date: null,
    status: 'active',
    requires_confirmation: true,
    notify: true,
    timezone_offset_minutes: -180,
    state: 'active',
    rule_label: 'Cada 2 meses el día 15',
    pending_count: 1,
    last_amount: null,
  },
];

let mockOccurrences: Occurrence[] = [
  {
    id: 'mock-occ-1',
    recurrence_id: 'mock-rec-2',
    occurrence_date: isoDaysFromToday(-2),
    status: 'pending',
    suggested_amount: 25000,
    transaction_id: null,
    resolved_at: null,
    name: 'Luz',
    type: 'expense',
    currency: 'ARS',
  },
];

function mockRefreshRecurring(): Recurring[] {
  return mockRecurring.map((r) => ({
    ...r,
    pending_count: mockOccurrences.filter((o) => o.recurrence_id === r.id && o.status === 'pending').length,
    state: r.status === 'paused' ? 'paused' : r.next_occurrence_date === null ? 'finished' : 'active',
  }));
}

export async function fetchRecurring(status: 'active' | 'paused' | 'all' = 'all'): Promise<Recurring[]> {
  if (MOCK_ENABLED) {
    return mockDelay(mockRefreshRecurring().filter((r) => status === 'all' || r.status === status));
  }
  const { data } = await apiClient.get<Recurring[]>('/api/v1/finance/recurring', {
    params: { status, tz_offset_minutes: tzOffsetMinutes() },
  });
  return data.map(mapRecurring);
}

export async function fetchRecurringOne(id: string): Promise<RecurringDetail> {
  if (MOCK_ENABLED) {
    const found = mockRefreshRecurring().find((r) => r.id === id);
    if (!found) throw new Error('Recurrencia no encontrada');
    return mockDelay({
      ...found,
      recent_occurrences: mockOccurrences.filter((o) => o.recurrence_id === id),
      next_dates: found.next_occurrence_date
        ? nextRuleDates(found, found.start_date, found.next_occurrence_date, 3, found.end_date)
        : [],
    });
  }
  const { data } = await apiClient.get<RecurringDetail>(`/api/v1/finance/recurring/${id}`, {
    params: { tz_offset_minutes: tzOffsetMinutes() },
  });
  return {
    ...mapRecurring(data),
    recent_occurrences: (data.recent_occurrences ?? []).map(mapOccurrence),
  };
}

export async function createRecurring(input: RecurringInput): Promise<Recurring> {
  if (MOCK_ENABLED) {
    const today = toLocalDateString();
    const next = nextRuleDates(input, input.start_date, today, 1, input.end_date)[0] ?? null;
    const created: Recurring = {
      ...input,
      id: `mock-rec-${generateId()}`,
      anchor_date: input.start_date,
      next_occurrence_date: next,
      last_occurrence_date: null,
      status: 'active',
      timezone_offset_minutes: tzOffsetMinutes(),
      state: next === null ? 'finished' : 'active',
      rule_label: ruleLabel(input),
      pending_count: 0,
      last_amount: null,
    };
    mockRecurring = [...mockRecurring, created];
    return mockDelay(created);
  }
  const { data } = await apiClient.post<Recurring>('/api/v1/finance/recurring', {
    ...input,
    timezone_offset_minutes: tzOffsetMinutes(),
  });
  return mapRecurring(data);
}

export async function updateRecurring(id: string, input: Partial<RecurringInput>): Promise<Recurring> {
  if (MOCK_ENABLED) {
    const current = mockRecurring.find((r) => r.id === id);
    if (!current) throw new Error('Recurrencia no encontrada');
    const merged = { ...current, ...input } as Recurring;
    const next =
      nextRuleDates(merged, merged.start_date, toLocalDateString(), 1, merged.end_date)[0] ?? null;
    const updated: Recurring = { ...merged, next_occurrence_date: next, rule_label: ruleLabel(merged) };
    mockRecurring = mockRecurring.map((r) => (r.id === id ? updated : r));
    return mockDelay(updated);
  }
  const { data } = await apiClient.put<Recurring>(`/api/v1/finance/recurring/${id}`, {
    ...input,
    timezone_offset_minutes: tzOffsetMinutes(),
  });
  return mapRecurring(data);
}

export async function deleteRecurring(id: string): Promise<void> {
  if (MOCK_ENABLED) {
    mockRecurring = mockRecurring.filter((r) => r.id !== id);
    mockOccurrences = mockOccurrences.filter((o) => o.recurrence_id !== id);
    return mockDelay(undefined);
  }
  await apiClient.delete(`/api/v1/finance/recurring/${id}`);
}

async function setRecurringPaused(id: string, paused: boolean): Promise<Recurring> {
  if (MOCK_ENABLED) {
    const current = mockRecurring.find((r) => r.id === id);
    if (!current) throw new Error('Recurrencia no encontrada');
    const updated: Recurring = { ...current, status: paused ? 'paused' : 'active' };
    mockRecurring = mockRecurring.map((r) => (r.id === id ? updated : r));
    return mockDelay(updated);
  }
  const { data } = await apiClient.post<Recurring>(
    `/api/v1/finance/recurring/${id}/${paused ? 'pause' : 'resume'}`,
    { timezone_offset_minutes: tzOffsetMinutes() },
  );
  return mapRecurring(data);
}

export const pauseRecurring = (id: string) => setRecurringPaused(id, true);
export const resumeRecurring = (id: string) => setRecurringPaused(id, false);

export async function previewRecurring(
  rule: RecurringRule & { start_date: string; end_date?: string | null; generate_past?: boolean },
): Promise<RecurringPreview> {
  if (MOCK_ENABLED) {
    // Aproximada: el server es quien manda (mismas reglas, ver utils/recurring.ts).
    const from = rule.generate_past ? rule.start_date : toLocalDateString();
    const dates = nextRuleDates(rule, rule.start_date, from, 5, rule.end_date);
    return mockDelay({ anchor_date: dates[0] ?? rule.start_date, dates });
  }
  const { data } = await apiClient.post<RecurringPreview>('/api/v1/finance/recurring/preview', {
    frequency: rule.frequency,
    interval_count: rule.interval_count,
    weekday: rule.weekday,
    day_of_month: rule.day_of_month,
    month_of_year: rule.month_of_year,
    start_date: rule.start_date,
    end_date: rule.end_date ?? null,
    generate_past: rule.generate_past ?? false,
    tz_offset_minutes: tzOffsetMinutes(),
  });
  return data;
}

export async function fetchUpcomingRecurring(days = 30): Promise<Upcoming> {
  if (MOCK_ENABLED) {
    const today = toLocalDateString();
    const horizon = isoDaysFromToday(days);
    const items = mockRecurring
      .filter((r) => r.status === 'active')
      .flatMap((r) =>
        nextRuleDates(r, r.start_date, today, 40, r.end_date)
          .filter((d) => d <= horizon)
          .map((date) => ({
            recurrence_id: r.id,
            date,
            name: r.name,
            type: r.type,
            amount: r.amount,
            currency: r.currency,
            requires_confirmation: r.requires_confirmation,
          })),
      )
      .sort((a, b) => a.date.localeCompare(b.date) || a.name.localeCompare(b.name));
    const totals = new Map<string, { type: 'income' | 'expense'; currency: string; total: number }>();
    for (const i of items) {
      if (i.amount === null) continue;
      const key = `${i.type}-${i.currency}`;
      const cur = totals.get(key) ?? { type: i.type, currency: i.currency, total: 0 };
      cur.total += i.amount;
      totals.set(key, cur);
    }
    return mockDelay({ days, items, totals: [...totals.values()] });
  }
  const { data } = await apiClient.get<Upcoming>('/api/v1/finance/recurring/upcoming', {
    params: { days, tz_offset_minutes: tzOffsetMinutes() },
  });
  return mapUpcoming(data);
}

export async function fetchOccurrences(status: 'pending' | 'all' = 'pending'): Promise<Occurrence[]> {
  if (MOCK_ENABLED) {
    return mockDelay(mockOccurrences.filter((o) => status === 'all' || o.status === 'pending'));
  }
  const { data } = await apiClient.get<Occurrence[]>('/api/v1/finance/recurring/occurrences', {
    params: { status },
  });
  return data.map(mapOccurrence);
}

export async function confirmOccurrence(id: string, input: ConfirmOccurrenceInput): Promise<Occurrence> {
  if (MOCK_ENABLED) {
    const current = mockOccurrences.find((o) => o.id === id);
    if (!current) throw new Error('Movimiento pendiente no encontrado');
    const updated: Occurrence = { ...current, status: 'confirmed', resolved_at: new Date().toISOString() };
    mockOccurrences = mockOccurrences.map((o) => (o.id === id ? updated : o));
    return mockDelay(updated);
  }
  const { data } = await apiClient.post<Occurrence>(`/api/v1/finance/recurring/occurrences/${id}/confirm`, {
    ...input,
    timezone_offset_minutes: tzOffsetMinutes(),
  });
  return mapOccurrence(data);
}

export async function skipOccurrence(id: string): Promise<Occurrence> {
  if (MOCK_ENABLED) {
    const current = mockOccurrences.find((o) => o.id === id);
    if (!current) throw new Error('Movimiento pendiente no encontrado');
    const updated: Occurrence = { ...current, status: 'skipped', resolved_at: new Date().toISOString() };
    mockOccurrences = mockOccurrences.map((o) => (o.id === id ? updated : o));
    return mockDelay(updated);
  }
  const { data } = await apiClient.post<Occurrence>(`/api/v1/finance/recurring/occurrences/${id}/skip`, {
    timezone_offset_minutes: tzOffsetMinutes(),
  });
  return mapOccurrence(data);
}

// ── Renovación de plazo fijo ──

function mapRenewalTerm(t: RenewalTerm): RenewalTerm {
  return {
    ...t,
    invested_amount: num(t.invested_amount),
    interest_rate_tna: numOrNull(t.interest_rate_tna),
    amount_at_maturity: numOrNull(t.amount_at_maturity),
    interest: numOrNull(t.interest),
  };
}

export async function renewInvestment(id: string, input: RenewFixedTermInput): Promise<RenewResult> {
  if (MOCK_ENABLED) {
    const current = mockInvestmentBases.find((b) => b.id === id);
    if (!current) throw new Error('Inversión no encontrada');
    const enriched = enrichInvestment(current);
    const collected = input.amount_collected ?? enriched.fixed_term?.amount_at_maturity ?? current.invested_amount;
    const start = input.start_date ?? toLocalDateString();
    const termDays = input.term_days ?? 30;
    const maturity = input.maturity_date ?? toLocalDateString(addLocalDays(parseDateOnly(start), termDays));
    const closedBase: MockInvestmentBase = { ...current, status: 'closed', current_value: collected };
    const newBase: MockInvestmentBase = {
      ...current,
      id: `mock-inv-${generateId()}`,
      status: 'active',
      invested_amount: input.mode === 'principal_only' ? current.invested_amount : collected,
      current_value: null,
      interest_rate_tna: input.interest_rate_tna,
      start_date: start,
      maturity_date: maturity,
    };
    mockInvestmentBases = [...mockInvestmentBases.map((b) => (b.id === id ? closedBase : b)), newBase];
    mockRenewals.set(id, newBase.id);
    mockRenewedFrom.set(newBase.id, id);
    const list = mockInvestmentList('all');
    return mockDelay({
      closed: list.find((i) => i.id === id)!,
      renewed: list.find((i) => i.id === newBase.id)!,
      interest_transaction_id: null,
    });
  }
  const { data } = await apiClient.post<RenewResult>(`/api/v1/finance/investments/${id}/renew`, {
    ...input,
    timezone_offset_minutes: tzOffsetMinutes(),
  });
  return { ...data, closed: mapInvestment(data.closed), renewed: mapInvestment(data.renewed) };
}

export async function fetchRenewals(id: string): Promise<RenewalChain> {
  if (MOCK_ENABLED) {
    const chain: string[] = [id];
    while (mockRenewedFrom.has(chain[0])) chain.unshift(mockRenewedFrom.get(chain[0])!);
    while (mockRenewals.has(chain[chain.length - 1])) chain.push(mockRenewals.get(chain[chain.length - 1])!);
    const list = mockInvestmentList('all');
    const items: RenewalTerm[] = chain
      .map((cid) => list.find((i) => i.id === cid))
      .filter((i): i is Investment => !!i)
      .map((i) => ({
        id: i.id,
        name: i.name,
        status: i.status,
        start_date: i.start_date,
        maturity_date: i.maturity_date,
        term_days: i.fixed_term?.term_days ?? null,
        invested_amount: i.invested_amount,
        interest_rate_tna: i.interest_rate_tna,
        amount_at_maturity: i.status === 'closed' ? i.current_value : (i.fixed_term?.amount_at_maturity ?? null),
        interest:
          i.status === 'closed' && i.current_value !== null
            ? Math.round((i.current_value - i.invested_amount) * 100) / 100
            : (i.fixed_term?.interest_total ?? null),
        renewed_from_id: mockRenewedFrom.get(i.id) ?? null,
      }));
    const accumulated = items
      .filter((t) => t.status === 'closed' && t.interest !== null)
      .reduce((a, t) => a + (t.interest ?? 0), 0);
    return mockDelay({
      items,
      accumulated_interest: Math.round(accumulated * 100) / 100,
      currency: list.find((i) => i.id === id)?.currency ?? 'ARS',
    });
  }
  const { data } = await apiClient.get<RenewalChain>(`/api/v1/finance/investments/${id}/renewals`);
  return {
    ...data,
    accumulated_interest: num(data.accumulated_interest),
    items: data.items.map(mapRenewalTerm),
  };
}

// ── Datos de mercado ──

function mapQuote(q: FxQuote): FxQuote {
  return { ...q, buy: numOrNull(q.buy), sell: num(q.sell) };
}

export async function fetchMarketFx(): Promise<MarketFx> {
  if (MOCK_ENABLED) {
    return mockDelay(mockMarketFx());
  }
  const { data } = await apiClient.get<MarketFx>('/api/v1/finance/market/fx');
  return { ...data, usd: data.usd.map(mapQuote), eur: data.eur.map(mapQuote) };
}

export async function fetchInflation(months = 12): Promise<InflationSeries> {
  if (MOCK_ENABLED) {
    const series = Array.from({ length: months }, (_, k) => {
      const d = new Date();
      d.setMonth(d.getMonth() - (months - k));
      return { period: d.toISOString().slice(0, 7), pct: MOCK_MONTHLY_INFLATION };
    });
    return mockDelay({
      series,
      last_published_period: series[series.length - 1]?.period ?? null,
      estimate_pct: MOCK_MONTHLY_INFLATION,
    });
  }
  const { data } = await apiClient.get<InflationSeries>('/api/v1/finance/market/inflation', {
    params: { months },
  });
  return {
    ...data,
    series: data.series.map((p) => ({ ...p, pct: num(p.pct) })),
    estimate_pct: numOrNull(data.estimate_pct),
  };
}

export async function fetchCryptoAssets(): Promise<CryptoAsset[]> {
  if (MOCK_ENABLED) {
    return mockDelay(
      Object.keys(MOCK_CRYPTO_PRICES).map((ticker) => ({ ticker, name: ticker })),
    );
  }
  const { data } = await apiClient.get<CryptoAsset[]>('/api/v1/finance/market/crypto-assets');
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
    // El export arma todo el histórico del usuario: con el timeout general
    // (15 s) una cuenta con mucha data fallaba justo la descarga que pide la ley.
    timeout: 120_000,
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

// ── Avisos de hábitos sin marcar ──

let mockHabitReminderSettings: HabitReminderSettings = {
  enabled: true,
  time: '20:00',
  daily_cap: 3,
  streak_alerts: true,
  timezone_offset_minutes: null,
  has_push_devices: false,
};

export async function fetchHabitReminderSettings(): Promise<HabitReminderSettings> {
  if (MOCK_ENABLED) {
    return mockDelay({ ...mockHabitReminderSettings });
  }
  const { data } = await apiClient.get<HabitReminderSettings>('/api/v1/habit-reminders/settings');
  return data;
}

// PUT parcial. Siempre viaja el huso de este navegador: el server decide el
// "hoy" y la hora del aviso con él (minutos al este de UTC).
export async function updateHabitReminderSettings(
  patch: Partial<Omit<HabitReminderSettings, 'has_push_devices'>>,
): Promise<HabitReminderSettings> {
  if (MOCK_ENABLED) {
    mockHabitReminderSettings = {
      ...mockHabitReminderSettings,
      ...patch,
      timezone_offset_minutes: patch.timezone_offset_minutes ?? localTzOffsetMinutes(),
    };
    return mockDelay({ ...mockHabitReminderSettings });
  }
  const { data } = await apiClient.put<HabitReminderSettings>('/api/v1/habit-reminders/settings', {
    ...patch,
    timezone_offset_minutes: localTzOffsetMinutes(),
  });
  return data;
}

export async function fetchHabitReminderToday(): Promise<HabitReminderToday> {
  if (MOCK_ENABLED) {
    const habits = [
      { id: 'g3', title: 'Meditar diariamente', icon: 'fa-bullseye', streak: 4 },
      { id: 'g4', title: 'Tomar agua', icon: null, streak: 0 },
    ];
    return mockDelay({
      local_date: toLocalDateString(),
      enabled: mockHabitReminderSettings.enabled,
      pending_count: habits.length,
      slots: [{ time: mockHabitReminderSettings.time, status: 'upcoming', habits }],
    });
  }
  const { data } = await apiClient.get<HabitReminderToday>('/api/v1/habit-reminders/today', {
    params: { tz_offset_minutes: localTzOffsetMinutes() },
  });
  return data;
}

// Minutos al este de UTC (Buenos Aires = -180): getTimezoneOffset() de JS usa el
// signo opuesto. El backend dispara la push a la hora local del usuario con este
// valor; sin él el recordatorio nunca suena desde el servidor (solo con la
// pestaña abierta).
function localTzOffsetMinutes(): number {
  return -new Date().getTimezoneOffset();
}

export async function createReminder(
  input: Omit<Reminder, 'id'>,
): Promise<Reminder> {
  if (MOCK_ENABLED) {
    return mockDelay({ id: generateId(), ...input });
  }
  const { data } = await apiClient.post<Reminder>('/api/v1/reminders', {
    ...input,
    timezone_offset_minutes: localTzOffsetMinutes(),
  });
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
  // Solo si cambia la hora: prender/apagar el recordatorio no debe pisar la zona con la de este navegador.
  const changesTime = input.hour !== undefined || input.minute !== undefined;
  const { data } = await apiClient.patch<Reminder>(`/api/v1/reminders/${id}`, {
    ...input,
    ...(changesTime && { timezone_offset_minutes: localTzOffsetMinutes() }),
  });
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
  const { data } = await apiClient.get<Exam[]>('/api/v1/study/exams', {
    params: { ...params, tz_offset_minutes: tzOffsetMinutes() },
  });
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
  const { data } = await apiClient.get<StudySummary>('/api/v1/study/summary', {
    params: { tz_offset_minutes: tzOffsetMinutes() },
  });
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
  const { data } = await apiClient.get<FocusSummary>('/api/v1/focus/summary', {
    params: { tz_offset_minutes: tzOffsetMinutes() },
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

// ── Buscador global ──

const SEARCH_LABELS: Record<SearchType, string> = {
  notes: 'Notas',
  tasks: 'Tareas',
  events: 'Eventos',
  transactions: 'Movimientos',
  habits: 'Hábitos',
  goals: 'Metas',
  investments: 'Inversiones',
  study: 'Estudio',
  library: 'Biblioteca',
  media: 'Películas y series',
  work: 'Trabajo',
  travel: 'Viajes',
  vehicle: 'Vehículo',
  projects: 'Proyectos',
};

const SEARCH_TYPE_ORDER = Object.keys(SEARCH_LABELS) as SearchType[];
const PAID_SEARCH_TYPES: SearchType[] = ['study', 'library', 'media', 'work', 'travel', 'vehicle', 'projects'];

/* eslint-disable @typescript-eslint/no-explicit-any */
type MockRow = Record<string, any>;

interface MockSearchSource {
  type: SearchType;
  entity: string;
  load: () => Promise<MockRow[]>;
  title: (r: MockRow) => string;
  content: (r: MockRow) => (string | null | undefined)[];
  path: (id: string) => string;
  date?: (r: MockRow) => string | null | undefined;
  filter?: (r: MockRow) => boolean;
}

const MOCK_SEARCH_SOURCES: MockSearchSource[] = [
  { type: 'notes', entity: 'note', load: fetchNotes, title: (r) => r.title, content: (r) => [r.content, ...(r.tags ?? []).map((t: { name: string }) => t.name)], path: (id) => `/notes?open=${id}`, date: (r) => r.updated_at },
  { type: 'tasks', entity: 'task', load: () => fetchTasks(), title: (r) => r.title, content: (r) => [r.description, r.area], path: (id) => `/tasks?open=${id}`, date: (r) => r.due_date },
  { type: 'events', entity: 'event', load: fetchEvents, title: (r) => r.title, content: (r) => [r.description, r.location], path: (id) => `/events?open=${id}`, date: (r) => r.start_datetime },
  { type: 'transactions', entity: 'transaction', load: async () => (await fetchTransactions({ per_page: 100 })).items, title: (r) => r.product_name, content: (r) => [r.merchant_name, r.product_description, r.notes], path: (id) => `/finances?tab=transacciones&open=${id}`, date: (r) => r.transaction_date },
  { type: 'habits', entity: 'habit', load: fetchGoals, title: (r) => r.title, content: (r) => [r.description], path: (id) => `/habits?open=${id}`, filter: (r) => r.goal_type === 'binary' || r.goal_type === 'metric' },
  { type: 'goals', entity: 'goal', load: fetchGoals, title: (r) => r.title, content: (r) => [r.description], path: (id) => `/goals?open=${id}`, date: (r) => r.end_date, filter: (r) => r.goal_type === 'progress' || r.goal_type === 'savings' },
  { type: 'investments', entity: 'investment', load: () => fetchInvestments(), title: (r) => r.name, content: (r) => [r.ticker, r.institution, r.notes], path: (id) => `/finances?tab=inversiones&open=${id}`, date: (r) => r.maturity_date },
  { type: 'study', entity: 'subject', load: fetchSubjects, title: (r) => r.name, content: (r) => [r.professor], path: (id) => `/study?open=${id}&entity=subject` },
  { type: 'library', entity: 'book', load: () => fetchBooks(), title: (r) => r.title, content: (r) => [r.author, r.notes], path: (id) => `/library?open=${id}&entity=book`, date: (r) => r.finished_date ?? r.started_date },
  { type: 'media', entity: 'media_item', load: () => fetchMediaItems(), title: (r) => r.title, content: (r) => [r.notes], path: (id) => `/media?open=${id}&entity=media_item` },
  { type: 'work', entity: 'opportunity', load: () => fetchOpportunities(), title: (r) => `${r.role} · ${r.company}`, content: (r) => [r.company, r.notes], path: (id) => `/work?open=${id}&entity=opportunity`, date: (r) => r.applied_date },
  { type: 'travel', entity: 'trip', load: fetchTrips, title: (r) => r.destination, content: (r) => [r.notes], path: (id) => `/travel?open=${id}&entity=trip`, date: (r) => r.start_date },
  { type: 'vehicle', entity: 'vehicle', load: fetchVehicles, title: (r) => r.name, content: (r) => [r.brand, r.model, r.plate], path: (id) => `/vehicle?open=${id}&entity=vehicle` },
  { type: 'projects', entity: 'project', load: fetchProjects, title: (r) => r.name, content: (r) => [r.description], path: (id) => `/projects?open=${id}&entity=project` },
];
/* eslint-enable @typescript-eslint/no-explicit-any */

function mockSnippet(fields: (string | null | undefined)[], tokens: string[]): string | null {
  const texts = fields.filter((f): f is string => !!f).map((f) => f.replace(/\s+/g, ' ').trim());
  const hit = texts.find((t) => highlightRanges(t, tokens).length > 0) ?? texts[0];
  return hit ? hit.slice(0, 140) : null;
}

/** Misma lógica que el server (plegado, AND de tokens, ranking, límite por
 *  grupo) sobre los datos mock, respetando las plantillas que el mock da por
 *  compradas y activas. */
async function searchMock(q: string, types: SearchType[] | undefined, limit: number): Promise<SearchResponse> {
  const { query, tokens } = tokenize(q);
  const phrase = foldText(query);
  const modules = await fetchModules();
  const allowed = new Set<SearchType>(
    SEARCH_TYPE_ORDER.filter(
      (t) => !PAID_SEARCH_TYPES.includes(t) || modules.some((m) => m.key === t && m.owned && m.enabled),
    ),
  );
  const wanted = SEARCH_TYPE_ORDER.filter(
    (t) => (!types || types.length === 0 || types.includes(t)) && allowed.has(t),
  );
  const groups: SearchGroup[] = [];
  for (const type of wanted) {
    const ranked: { rank: number; date: string; item: SearchItem }[] = [];
    for (const source of MOCK_SEARCH_SOURCES.filter((s) => s.type === type)) {
      for (const row of await source.load()) {
        if (source.filter && !source.filter(row)) continue;
        const title = source.title(row);
        const content = source.content(row);
        const haystacks = [title, ...content].map((f) => foldText(f ?? ''));
        if (!tokens.every((tok) => haystacks.some((h) => h.includes(tok)))) continue;
        const snippet = mockSnippet(content, tokens);
        const date = source.date?.(row) ?? null;
        ranked.push({
          rank: matchRank(title, phrase, tokens),
          date: date ?? '',
          item: {
            id: String(row.id),
            type,
            entity: source.entity,
            title,
            title_highlights: highlightRanges(title, tokens),
            snippet,
            snippet_highlights: highlightRanges(snippet, tokens),
            date,
            parent_id: null,
            path: source.path(String(row.id)),
            meta:
              type === 'notes'
                ? { tags: (row.tags ?? []).map((t: { name: string }) => t.name), archived: !!row.is_archived }
                : null,
          },
        });
      }
    }
    if (ranked.length === 0) continue;
    ranked.sort((a, b) => a.rank - b.rank || b.date.localeCompare(a.date) || a.item.id.localeCompare(b.item.id));
    groups.push({
      type,
      label: SEARCH_LABELS[type],
      has_more: ranked.length > limit,
      items: ranked.slice(0, limit).map((r) => r.item),
    });
  }
  return mockDelay({ query, groups });
}

export async function searchAll(
  q: string,
  options: { types?: SearchType[]; limit?: number } = {},
): Promise<SearchResponse> {
  const limit = options.limit ?? 5;
  if (MOCK_ENABLED) {
    return searchMock(q, options.types, limit);
  }
  const { data } = await apiClient.get<SearchResponse>('/api/v1/search', {
    params: {
      q,
      limit,
      ...(options.types && options.types.length > 0 && { types: options.types.join(',') }),
    },
  });
  return data;
}
