export interface Transaction {
  id: string;
  amount: number;
  currency: 'ARS' | 'USD';
  type: 'income' | 'expense';
  transaction_date: string;
  product_name: string;
  merchant_name: string;
  payment_method: string;
  category_name?: string;
  category_color?: string;
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
  total_expense: number;
  balance: number;
  currency: string;
}

export type TaskStatus = 'pending' | 'in_progress' | 'completed';

export interface KanbanColumn {
  id: TaskStatus;
  title: string;
  tasks: Task[];
}
