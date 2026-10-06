// Helpers de fechas. La API mezcla tres formatos y cada uno se interpreta distinto:
//
//  - Solo fecha ("2026-10-06", transaction_date, due_date, session_date...):
//    es un día de calendario, sin zona horaria.
//  - Timestamps de sistema (created_at, updated_at, started_at...): el backend
//    los manda en UTC pero SIN sufijo ("2026-10-06T17:26:55").
//  - Fecha y hora de un evento (start_datetime): hora de pared tal cual la
//    cargó el usuario, también sin sufijo.
//
// `new Date()` pelado interpreta mal los dos primeros en Argentina (UTC-3): la
// fecha sola la corre al día anterior y el timestamp sin sufijo lo toma como
// hora local, con 3 horas de error.

const pad = (n: number) => String(n).padStart(2, '0');

/** YYYY-MM-DD de un Date en hora LOCAL. `toISOString()` da el día en UTC, que
 *  desde las 21:00 en Argentina ya es el día siguiente. */
export function toLocalDateString(date: Date = new Date()): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/** "YYYY-MM-DD" como Date a medianoche LOCAL (no UTC). */
export function parseDateOnly(value: string): Date {
  const [y, m, d] = value.slice(0, 10).split('-').map(Number);
  return new Date(y, (m || 1) - 1, d || 1);
}

const HAS_TIMEZONE = /(Z|[+-]\d{2}:?\d{2})$/i;

/** Timestamp de sistema de la API (UTC, a veces sin sufijo) como Date. */
export function parseServerTimestamp(value: string): Date {
  const hasTime = value.includes('T');
  return new Date(hasTime && !HAS_TIMEZONE.test(value) ? `${value}Z` : value);
}

/** Días de calendario entre hoy y un "YYYY-MM-DD" (negativo si ya pasó). */
export function daysUntilDate(value: string, now: Date = new Date()): number {
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.round((parseDateOnly(value).getTime() - today.getTime()) / 86_400_000);
}
