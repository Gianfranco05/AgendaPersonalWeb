import {
  StickyNote,
  ListTodo,
  Calendar,
  PiggyBank,
  Repeat,
  Target,
  TrendingUp,
  GraduationCap,
  BookOpen,
  Film,
  Briefcase,
  Plane,
  Car,
  FolderKanban,
  type LucideIcon,
} from 'lucide-react';
import type { SearchItem, SearchType } from '../../types';
import { parseDateOnly } from '../../utils/date';
import Highlight from './Highlight';

export const SEARCH_ICONS: Record<SearchType, LucideIcon> = {
  notes: StickyNote,
  tasks: ListTodo,
  events: Calendar,
  transactions: PiggyBank,
  habits: Repeat,
  goals: Target,
  investments: TrendingUp,
  study: GraduationCap,
  library: BookOpen,
  media: Film,
  work: Briefcase,
  travel: Plane,
  vehicle: Car,
  projects: FolderKanban,
};

/** Fecha corta en es-AR. Una fecha sola es un día de calendario (sin zona);
 *  un timestamp con Z o una hora de pared (eventos) los resuelve `Date`. */
export function formatResultDate(value: string | null): string | null {
  if (!value) return null;
  const date = value.length === 10 ? parseDateOnly(value) : new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString('es-AR', { day: 'numeric', month: 'short', year: 'numeric' });
}

/** Monto de un movimiento con signo y moneda (el server manda el crudo). */
export function formatResultAmount(meta: Record<string, unknown> | null): string | null {
  if (!meta || meta.amount == null) return null;
  const amount = Number(meta.amount);
  if (!Number.isFinite(amount)) return null;
  const currency = typeof meta.currency === 'string' && meta.currency ? meta.currency : 'ARS';
  let formatted: string;
  try {
    formatted = new Intl.NumberFormat('es-AR', { style: 'currency', currency }).format(amount);
  } catch {
    formatted = `${currency} ${amount.toLocaleString('es-AR')}`;
  }
  const sign = meta.type === 'income' ? '+' : meta.type === 'expense' ? '-' : '';
  return `${sign}${formatted}`;
}

interface Props {
  item: SearchItem;
  id: string;
  active: boolean;
  onSelect: () => void;
  onHover: () => void;
}

export default function SearchResultItem({ item, id, active, onSelect, onHover }: Props) {
  const Icon = SEARCH_ICONS[item.type];
  const date = formatResultDate(item.date);
  const amount = formatResultAmount(item.meta);
  const archived = item.meta?.archived === true;
  const tags = Array.isArray(item.meta?.tags) ? (item.meta?.tags as string[]) : [];

  return (
    <div
      id={id}
      role="option"
      aria-selected={active}
      onMouseMove={onHover}
      onClick={onSelect}
      className={`flex cursor-pointer items-start gap-3 rounded-lg px-3 py-2 ${
        active ? 'bg-brand-indigo/10' : 'hover:bg-gray-50 dark:hover:bg-slate-700/50'
      }`}
    >
      <Icon size={16} className="mt-1 shrink-0 text-gray-400 dark:text-slate-400" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-medium text-gray-900 dark:text-slate-100">
            <Highlight text={item.title} ranges={item.title_highlights} />
          </span>
          {archived && (
            <span className="shrink-0 rounded bg-gray-200 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-gray-600 dark:bg-slate-600 dark:text-slate-200">
              Archivada
            </span>
          )}
        </div>
        {item.snippet && (
          <p className="mt-0.5 line-clamp-2 text-xs text-gray-500 dark:text-slate-400">
            <Highlight text={item.snippet} ranges={item.snippet_highlights} />
          </p>
        )}
        {tags.length > 0 && (
          <div className="mt-1 flex flex-wrap gap-1">
            {tags.map((tag) => (
              <span key={tag} className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-600 dark:bg-slate-700 dark:text-slate-300">
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
      <div className="shrink-0 text-right text-xs text-gray-400 dark:text-slate-400">
        {amount && <div className="font-medium text-gray-700 dark:text-slate-200">{amount}</div>}
        {date && <div>{date}</div>}
      </div>
    </div>
  );
}
