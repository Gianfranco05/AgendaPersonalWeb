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

export interface Task {
  id: string;
  title: string;
  description: string;
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
  goal_type: 'binary' | 'progress';
  target_value: number;
  current_value: number;
  unit: string | null;
  end_date: string | null;
  color: string;
  icon: string;
  is_completed: boolean;
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
