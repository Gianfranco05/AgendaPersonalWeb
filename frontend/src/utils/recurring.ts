// Helpers de movimientos recurrentes. El calendario OFICIAL lo calcula el server
// (`/finance/recurring/preview`); esto replica la misma regla para el modo mock
// y para textos de la UI. Todas las fechas son "YYYY-MM-DD" de calendario local.

import type { RecurringFrequency, RecurringRule } from '../types';
import { parseDateOnly, toLocalDateString } from './date';

export const FREQUENCY_LABELS: Record<RecurringFrequency, string> = {
  daily: 'Diaria',
  weekly: 'Semanal',
  monthly: 'Mensual',
  yearly: 'Anual',
};

// Máximo de "cada N" por frecuencia (mismos límites que el server).
export const MAX_INTERVAL: Record<RecurringFrequency, number> = {
  daily: 365,
  weekly: 52,
  monthly: 12,
  yearly: 10,
};

export const INTERVAL_UNITS: Record<RecurringFrequency, [string, string]> = {
  daily: ['día', 'días'],
  weekly: ['semana', 'semanas'],
  monthly: ['mes', 'meses'],
  yearly: ['año', 'años'],
};

// 0 = lunes ... 6 = domingo (como `date.weekday()` de Python).
export const WEEKDAY_NAMES = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];
const WEEKDAYS_PLURAL = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábados', 'domingos'];

export const MONTH_NAMES = [
  'Enero',
  'Febrero',
  'Marzo',
  'Abril',
  'Mayo',
  'Junio',
  'Julio',
  'Agosto',
  'Septiembre',
  'Octubre',
  'Noviembre',
  'Diciembre',
];

const pad = (n: number) => String(n).padStart(2, '0');

function lastDayOfMonth(year: number, month1: number): number {
  return new Date(year, month1, 0).getDate();
}

function clamped(year: number, month1: number, day: number): Date {
  return new Date(year, month1 - 1, Math.min(day, lastDayOfMonth(year, month1)));
}

function addDays(d: Date, days: number): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate() + days);
}

/** Primera fecha que cumple la regla en o después de `floor`. */
function anchorFrom(rule: RecurringRule, floor: Date): Date {
  if (rule.frequency === 'daily') return floor;
  if (rule.frequency === 'weekly') {
    // getDay(): 0 = domingo; la regla usa 0 = lunes.
    const current = (floor.getDay() + 6) % 7;
    return addDays(floor, (((rule.weekday ?? 0) - current) % 7 + 7) % 7);
  }
  if (rule.frequency === 'monthly') {
    const day = rule.day_of_month ?? 1;
    let candidate = clamped(floor.getFullYear(), floor.getMonth() + 1, day);
    if (candidate < floor) candidate = clamped(floor.getFullYear(), floor.getMonth() + 2, day);
    return candidate;
  }
  const day = rule.day_of_month ?? 1;
  const month = rule.month_of_year ?? 1;
  let candidate = clamped(floor.getFullYear(), month, day);
  if (candidate < floor) candidate = clamped(floor.getFullYear() + 1, month, day);
  return candidate;
}

/** Ocurrencia k contada desde el ancla (nunca desde la anterior: sin arrastre de fin de mes). */
function occurrence(rule: RecurringRule, anchor: Date, k: number): Date {
  const n = rule.interval_count;
  if (rule.frequency === 'daily') return addDays(anchor, n * k);
  if (rule.frequency === 'weekly') return addDays(anchor, 7 * n * k);
  if (rule.frequency === 'monthly') {
    const index = anchor.getFullYear() * 12 + anchor.getMonth() + n * k;
    return clamped(Math.floor(index / 12), (index % 12) + 1, rule.day_of_month ?? 1);
  }
  return clamped(anchor.getFullYear() + n * k, rule.month_of_year ?? 1, rule.day_of_month ?? 1);
}

/** Próximas fechas de la regla (hasta `count`), a partir de `max(start, from)` y
 *  sin pasar de `end`. Con `from` = hoy replica la vista previa del server. */
export function nextRuleDates(
  rule: RecurringRule,
  start: string,
  from: string,
  count: number,
  end?: string | null,
): string[] {
  if (!start) return [];
  const startDate = parseDateOnly(start);
  const anchor = anchorFrom(rule, startDate);
  const floor = parseDateOnly(from > start ? from : start);
  const endDate = end ? parseDateOnly(end) : null;
  const dates: string[] = [];
  for (let k = 0; k < 5000 && dates.length < count; k++) {
    const d = occurrence(rule, anchor, k);
    if (endDate && d > endDate) break;
    if (d >= floor) dates.push(toLocalDateString(d));
  }
  return dates;
}

/** Etiqueta en español de la regla (la misma que arma el server). */
export function ruleLabel(rule: RecurringRule): string {
  const n = rule.interval_count;
  if (rule.frequency === 'daily') return n === 1 ? 'Todos los días' : `Cada ${n} días`;
  if (rule.frequency === 'weekly') {
    const day = WEEKDAYS_PLURAL[rule.weekday ?? 0];
    return n === 1 ? `Todas las semanas los ${day}` : `Cada ${n} semanas los ${day}`;
  }
  const dom = rule.day_of_month ?? 1;
  const suffix = dom > 28 ? ' (o el último día del mes)' : '';
  if (rule.frequency === 'monthly') {
    return `${n === 1 ? 'Todos los meses' : `Cada ${n} meses`} el día ${dom}${suffix}`;
  }
  return `${n === 1 ? 'Todos los años' : `Cada ${n} años`} el ${pad(dom)}/${pad(rule.month_of_year ?? 1)}${suffix}`;
}

/** "5 nov 2026" para listas (sin pasar por Date UTC). */
export function formatShortDate(value: string): string {
  const d = parseDateOnly(value);
  const month = MONTH_NAMES[d.getMonth()].slice(0, 3).toLowerCase();
  return `${d.getDate()} ${month} ${d.getFullYear()}`;
}
