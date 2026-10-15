export interface Transaction {
  id: string;
  amount: number;
  currency: string;
  type: 'income' | 'expense';
  transaction_date: string;
  product_name: string;
  merchant_name: string;
  // Valor del enum PaymentMethod del backend (cash, debit_card, credit_card,
  // transfer, check, other), no la etiqueta en español.
  payment_method: string;
  // La API devuelve solo el id; el nombre/color se resuelven contra
  // useCategories() donde hacen falta.
  category_id?: string;
  notes?: string;
}

export interface Note {
  id: string;
  title: string;
  content: string;
  is_pinned: boolean;
  is_archived: boolean;
  color: string;
  tags: Tag[];
  event_date?: string;
  created_at: string;
  updated_at: string;
}

export interface Tag {
  id: string;
  name: string;
  color: string;
}

export interface CalendarEvent {
  id: string;
  title: string;
  description?: string;
  start_datetime: string;
  end_datetime?: string;
  is_all_day: boolean;
  color: string;
  location?: string;
}

export type TaskPriority = 'alta' | 'media' | 'baja';

export interface Task {
  id: string;
  title: string;
  description: string;
  area: string;
  priority: TaskPriority;
  due_date: string | null;
  status: 'pending' | 'in_progress' | 'completed';
  order: number;
}

export interface Category {
  id: string;
  name: string;
  color: string;
  icon: string;
}

export interface FinanceSummary {
  total_income: number;
  total_expenses: number;
  // Solo efectivo (se asume ARS), tenga o no activado "Sumar inversiones al balance".
  balance: number;
  // Aditivos: null = falta una cotización para valuar las inversiones en ARS.
  investments_value_ars?: number | null;
  net_worth_ars?: number | null;
  investments_missing_rates?: string[];
  include_investments_in_balance?: boolean;
}

export interface TransactionsResponse {
  items: Transaction[];
  total: number;
  page: number;
  page_size: number;
}

export interface Budget {
  id: string;
  category_id: string;
  amount: number;
  period: string;
  alert_threshold: number;
}

export interface BudgetProgress extends Budget {
  category_name: string;
  spent: number;
  remaining: number;
  percentage: number;
}

export interface CategoryExpenseTotal {
  name: string;
  color: string;
  total: number;
}

export interface MonthlyTotal {
  month: string;
  income: number;
  expense: number;
}

export interface FinanceReports {
  by_category: CategoryExpenseTotal[];
  monthly: MonthlyTotal[];
  total_expenses: number;
}

export type BankAccountType = 'checking' | 'savings' | 'credit' | 'cash' | 'investment';

export interface BankAccount {
  id: string;
  user_id: string;
  created_at: string;
  name: string;
  bank_name?: string;
  account_type: BankAccountType;
  account_number?: string;
  last4?: string;
  currency: string;
  balance: number;
}

export interface Settings {
  currency: string;
  theme_color: string;
  date_format: string;
  google_calendar_id: string;
  google_connected: boolean;
  // Cotizaciones que carga el usuario (ARS por 1 USD / 1 EUR); null = sin cargar.
  fx_usd_ars?: number | null;
  fx_eur_ars?: number | null;
  fx_rates_updated_at?: string | null;
  include_investments_in_balance?: boolean;
}

export type TaskStatus = 'pending' | 'in_progress' | 'completed';

export interface KanbanColumn {
  id: TaskStatus;
  title: string;
  tasks: Task[];
}

export interface Goal {
  id: string;
  title: string;
  description: string | null;
  goal_type: 'binary' | 'progress' | 'metric' | 'savings';
  target_value: number;
  current_value: number;
  unit: string | null;
  end_date: string | null;
  color: string;
  icon: string;
  is_completed: boolean;
}

export interface HabitRecord {
  id: string;
  goal_id: string;
  record_date: string;
  value: number;
  notes: string | null;
}

export interface MonthlySummaryItem {
  goal_id: string;
  title: string;
  unit: string | null;
  total: number;
  average: number;
}

// ── Fitness ──

export interface Exercise {
  id?: string;
  name: string;
  sets: number;
  reps: number;
  weight_kg: number | null;
  order: number;
}

export interface WorkoutSession {
  id: string;
  date: string;
  name: string;
  duration_minutes: number | null;
  notes: string | null;
  exercises: Exercise[];
}

export interface FitnessSummary {
  sessions_this_month: number;
  total_exercises: number;
  last_session_date: string | null;
}

// ── Nutrition ──

export type MealType = 'breakfast' | 'lunch' | 'dinner' | 'snack';

export interface Meal {
  id: string;
  date: string;
  meal_type: MealType;
  name: string;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}

export interface NutritionSummary {
  today_calories: number;
  today_protein_g: number;
  today_carbs_g: number;
  today_fat_g: number;
  week_calories: number;
  week_protein_g: number;
  week_carbs_g: number;
  week_fat_g: number;
}

// ── Sessions ──

export interface Session {
  id: string;
  device_info: string | null;
  created_at: string;
  last_used_at: string | null;
  expires_at: string;
}

// ── Reminders ──

export interface Reminder {
  id: string;
  message: string;
  icon: string;
  hour: number;
  minute: number;
  enabled: boolean;
}

// ── Módulos y Tienda ──

export interface ModuleInfo {
  key: string;
  label: string;
  description: string;
  icon: string;
  /** Incluido en la app: gratis y no se puede desactivar. */
  is_base: boolean;
  /** El usuario la tiene: base, o comprada. */
  owned: boolean;
  enabled: boolean;
  /** Tiene precio cargado en Stripe: ya se puede comprar. */
  for_sale: boolean;
}

export interface StoreItem {
  key: string;
  label: string;
  description: string;
  icon: string;
  owned: boolean;
  /** En la unidad mínima de la moneda (centavos). null si todavía no tiene precio en Stripe. */
  amount: number | null;
  currency: string | null;
}

export interface StoreCatalog {
  billing_enabled: boolean;
  items: StoreItem[];
}

// ── Study ──

export type SubjectStatus = 'cursando' | 'aprobada' | 'pendiente';

export interface Subject {
  id: string;
  name: string;
  professor: string | null;
  color: string;
  status: SubjectStatus;
}

export interface Exam {
  id: string;
  subject_id: string;
  title: string;
  exam_date: string;
  grade: number | null;
  notes: string | null;
}

export interface StudySummary {
  subjects_total: number;
  subjects_cursando: number;
  subjects_aprobadas: number;
  average_grade: number | null;
  next_exam: Exam | null;
  upcoming_count: number;
}

// ── Library ──

export type BookStatus = 'pendiente' | 'leyendo' | 'leido';

export interface Book {
  id: string;
  title: string;
  author: string | null;
  status: BookStatus;
  rating: number | null;
  pages: number | null;
  notes: string | null;
  started_date: string | null;
  finished_date: string | null;
}

export interface LibrarySummary {
  total: number;
  pendientes: number;
  leyendo: number;
  leidos: number;
  average_rating: number | null;
}

// ── Media (películas y series) ──

export type MediaType = 'pelicula' | 'serie';
export type MediaStatus = 'pendiente' | 'viendo' | 'visto';

export interface MediaItem {
  id: string;
  title: string;
  media_type: MediaType;
  status: MediaStatus;
  rating: number | null;
  year: number | null;
  notes: string | null;
}

export interface MediaSummary {
  total: number;
  pendientes: number;
  viendo: number;
  vistos: number;
  average_rating: number | null;
}

// ── Work (trabajo y carrera) ──

export type OpportunityStatus = 'aplicado' | 'entrevista' | 'oferta' | 'rechazado' | 'aceptado';

export interface WorkOpportunity {
  id: string;
  company: string;
  role: string;
  status: OpportunityStatus;
  salary: number | null;
  applied_date: string | null;
  notes: string | null;
}

export interface WorkSummary {
  total: number;
  active: number;
  entrevista: number;
  oferta: number;
  aceptado: number;
}

// ── Focus (deep work) ──

export interface FocusSession {
  id: string;
  started_at: string;
  ended_at: string | null;
  duration_seconds: number | null;
  label: string | null;
}

export interface FocusSummary {
  today_seconds: number;
  week_seconds: number;
  active: FocusSession | null;
}

// ── Travel (viajes y equipaje) ──

export type TripStatus = 'planeado' | 'en_curso' | 'completado';

export interface Trip {
  id: string;
  destination: string;
  start_date: string | null;
  end_date: string | null;
  status: TripStatus;
  budget: number | null;
  notes: string | null;
}

export interface PackingItem {
  id: string;
  trip_id: string;
  name: string;
  packed: boolean;
}

export interface TravelSummary {
  total: number;
  planeados: number;
  completados: number;
  next_trip: Trip | null;
}

// ── Vehicle (vehículo y mantenimiento) ──

export type MaintenanceRecordType = 'combustible' | 'revision' | 'itv' | 'gasto';

export interface Vehicle {
  id: string;
  name: string;
  brand: string | null;
  model: string | null;
  plate: string | null;
}

export interface MaintenanceRecord {
  id: string;
  vehicle_id: string;
  record_type: MaintenanceRecordType;
  record_date: string;
  cost: number | null;
  odometer_km: number | null;
  notes: string | null;
}

export interface VehicleSummary {
  vehicles_total: number;
  records_total: number;
  total_spent: number;
  last_record: MaintenanceRecord | null;
}

// ── Projects (gestión de proyectos) ──

export type ProjectStatus = 'activo' | 'pausado' | 'completado';
export type ProjectTaskStatus = 'pendiente' | 'en_progreso' | 'hecho';

export interface Project {
  id: string;
  name: string;
  description: string | null;
  status: ProjectStatus;
}

export interface ProjectTask {
  id: string;
  project_id: string;
  title: string;
  status: ProjectTaskStatus;
  due_date: string | null;
  notes: string | null;
}

export interface ProjectsSummary {
  projects_total: number;
  projects_active: number;
  tasks_pending: number;
  tasks_in_progress: number;
  tasks_done: number;
}

// ── Inversiones ──

export type AssetType =
  | 'stock'
  | 'fixed_term'
  | 'crypto'
  | 'bond'
  | 'fund'
  | 'fx'
  | 'real_estate'
  | 'vehicle'
  | 'other';

export type InvestmentCurrency = 'ARS' | 'USD' | 'USDT' | 'EUR';

export type InvestmentStatus = 'active' | 'closed';

export type ValueSource = 'quote' | 'manual' | 'fixed_term_accrued' | 'invested';

export interface FixedTermInfo {
  term_days: number;
  interest_total: number;
  amount_at_maturity: number;
  accrued_interest: number;
  tea_pct: number;
}

export interface Investment {
  id: string;
  asset_type: AssetType;
  name: string;
  ticker: string | null;
  currency: InvestmentCurrency;
  quantity: number | null;
  invested_amount: number;
  current_value: number | null;
  interest_rate_tna: number | null;
  start_date: string | null;
  maturity_date: string | null;
  institution: string | null;
  notes: string | null;
  status: InvestmentStatus;
  notify_maturity: boolean;
  value_updated_at: string | null;
  // Calculados por el server a "hoy" del usuario.
  effective_value: number;
  value_source: ValueSource;
  gain: number;
  gain_pct: number | null;
  days_to_maturity: number | null;
  is_matured: boolean;
  fixed_term: FixedTermInfo | null;
}

// Lo que se manda al crear/editar. En PUT, `null` en un campo opcional lo borra.
export interface InvestmentInput {
  asset_type: AssetType;
  name: string;
  ticker: string | null;
  currency: InvestmentCurrency;
  quantity: number | null;
  invested_amount: number;
  current_value: number | null;
  interest_rate_tna: number | null;
  start_date: string | null;
  maturity_date: string | null;
  institution: string | null;
  notes: string | null;
  notify_maturity: boolean;
}

export interface CurrencyBreakdown {
  currency: InvestmentCurrency;
  invested: number;
  current_value: number;
  gain: number;
  count: number;
}

export interface TypeBreakdown {
  asset_type: AssetType;
  count: number;
  value_ars: number | null;
}

export interface UpcomingMaturity {
  id: string;
  name: string;
  asset_type: AssetType;
  currency: InvestmentCurrency;
  maturity_date: string;
  days_to_maturity: number;
  amount: number;
}

export interface InvestmentSummary {
  by_currency: CurrencyBreakdown[];
  by_type: TypeBreakdown[];
  total_ars: number | null;
  total_usd: number | null;
  missing_rates: string[];
  count_active: number;
  upcoming_maturities: UpcomingMaturity[];
}

export interface NetWorth {
  cash_balance_ars: number;
  cash_balance_usd: number | null;
  investments: InvestmentSummary;
  net_worth_ars: number | null;
  net_worth_usd: number | null;
  rates: { usd_ars: number | null; eur_ars: number | null; updated_at: string | null };
  missing_rates: string[];
  include_investments_in_balance: boolean;
}
