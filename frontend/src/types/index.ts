export interface Transaction {
  id: string;
  amount: number;
  currency: string;
  type: 'income' | 'expense';
  transaction_date: string;
  product_name: string;
  merchant_name: string;
  payment_method: string;
  category_id?: string;
  // Enriquecidos solo por mocks/joins; la API base no los devuelve
  category_name?: string;
  category_color?: string;
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
  balance: number;
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

export interface Settings {
  currency: string;
  theme_color: string;
  date_format: string;
  google_calendar_id: string;
  google_connected: boolean;
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
