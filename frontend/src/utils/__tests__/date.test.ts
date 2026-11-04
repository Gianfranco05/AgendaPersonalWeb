import { describe, it, expect } from 'vitest';
import { toLocalDateString, parseDateOnly, parseServerTimestamp, daysUntilDate } from '../date';

describe('toLocalDateString', () => {
  it('usa el día local, no el UTC', () => {
    // 23:30 locales: en UTC-3 el toISOString() ya diría el día siguiente.
    expect(toLocalDateString(new Date(2026, 9, 6, 23, 30))).toBe('2026-10-06');
    expect(toLocalDateString(new Date(2026, 0, 5, 0, 5))).toBe('2026-01-05');
  });
});

describe('parseDateOnly', () => {
  it('devuelve medianoche local del mismo día', () => {
    const d = parseDateOnly('2026-10-06');
    expect([d.getFullYear(), d.getMonth(), d.getDate(), d.getHours()]).toEqual([2026, 9, 6, 0]);
  });
});

describe('parseServerTimestamp', () => {
  it('trata un timestamp sin sufijo como UTC', () => {
    expect(parseServerTimestamp('2026-10-06T17:26:55').toISOString()).toBe('2026-10-06T17:26:55.000Z');
    expect(parseServerTimestamp('2026-10-06T17:26:55.899893').getTime()).toBe(
      Date.parse('2026-10-06T17:26:55.899Z'),
    );
  });
  it('respeta Z y offsets explícitos', () => {
    expect(parseServerTimestamp('2026-10-06T17:26:55Z').toISOString()).toBe('2026-10-06T17:26:55.000Z');
    expect(parseServerTimestamp('2026-10-06T14:26:55-03:00').toISOString()).toBe('2026-10-06T17:26:55.000Z');
  });
});

describe('daysUntilDate', () => {
  const now = new Date(2026, 9, 6, 22, 0); // 22:00 locales
  it('cuenta días de calendario, sin importar la hora', () => {
    expect(daysUntilDate('2026-10-06', now)).toBe(0);
    expect(daysUntilDate('2026-10-07', now)).toBe(1);
    expect(daysUntilDate('2026-10-05', now)).toBe(-1);
  });
});
