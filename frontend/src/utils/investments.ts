// Helpers de inversiones: formato es-AR, coma decimal y la vista previa del
// plazo fijo. Los montos oficiales los calcula el server (Decimal, half-up);
// esto es solo para previsualizar antes de guardar y para el modo mock.

import type {
  AssetType,
  FixedTermInfo,
  Investment,
  InvestmentCurrency,
  ValueSource,
} from '../types';
import { daysUntilDate, parseDateOnly } from './date';

export const ASSET_TYPE_LABELS: Record<AssetType, string> = {
  stock: 'Acciones / CEDEARs',
  fixed_term: 'Plazo fijo',
  crypto: 'Cripto',
  bond: 'Bonos',
  fund: 'Fondos comunes (FCI)',
  fx: 'Dólares / divisas',
  real_estate: 'Inmuebles',
  vehicle: 'Vehículos',
  other: 'Otros',
};

export const ASSET_TYPES = Object.keys(ASSET_TYPE_LABELS) as AssetType[];

export const CURRENCIES: InvestmentCurrency[] = ['ARS', 'USD', 'USDT', 'EUR'];

const CURRENCY_SYMBOLS: Record<InvestmentCurrency, string> = {
  ARS: '$',
  USD: 'US$',
  USDT: 'USDT',
  EUR: '€',
};

/** `$ 1.024.657,53`, `US$ 2.000,00`. Siempre con 2 decimales. */
export function formatMoney(value: number, currency: InvestmentCurrency = 'ARS'): string {
  const sign = value < 0 ? '-' : '';
  const body = Math.abs(value).toLocaleString('es-AR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `${sign}${CURRENCY_SYMBOLS[currency]} ${body}`;
}

/** Cantidad de unidades: hasta 8 decimales (cripto), sin ceros de relleno. */
export function formatQuantity(value: number): string {
  return value.toLocaleString('es-AR', { maximumFractionDigits: 8 });
}

/** Número tipeado por el usuario → number. Acepta coma decimal (`1500,50`),
 *  miles con punto (`1.500,50`, `1.000.000`) y punto decimal (`1500.50`). Un
 *  único punto sin coma se toma como decimal (`1.500` = 1,5).
 *  Devuelve null si está vacío o no es un número. */
export function parseDecimal(text: string): number | null {
  const raw = text.trim().replace(/\s/g, '');
  if (!raw) return null;
  let normalized = raw;
  if (raw.includes(',')) normalized = raw.replace(/\./g, '').replace(',', '.');
  else if (/^[1-9]\d{0,2}(\.\d{3}){2,}$/.test(raw)) normalized = raw.replace(/\./g, '');
  if (!/^-?\d*\.?\d+$|^-?\d+\.$/.test(normalized)) return null;
  const n = Number(normalized);
  return Number.isFinite(n) ? n : null;
}

function round2(n: number): number {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

export interface FixedTermPreview {
  termDays: number;
  interest: number;
  amountAtMaturity: number;
}

/** Interés simple TNA/365 (convención argentina): P × TNA/100 × días/365. */
export function fixedTermPreview(
  principal: number | null,
  tna: number | null,
  start: string,
  maturity: string,
): FixedTermPreview | null {
  if (principal === null || tna === null || !start || !maturity) return null;
  const termDays = Math.round(
    (parseDateOnly(maturity).getTime() - parseDateOnly(start).getTime()) / 86_400_000,
  );
  if (termDays <= 0) return null;
  const interest = round2((principal * tna * termDays) / 100 / 365);
  return { termDays, interest, amountAtMaturity: round2(principal + interest) };
}

/** Chip de vencimiento: "vence hoy" / "vence mañana" / "vence en 5 días" / "venció". */
export function maturityLabel(daysToMaturity: number | null): string | null {
  if (daysToMaturity === null) return null;
  if (daysToMaturity < 0) return 'venció';
  if (daysToMaturity === 0) return 'vence hoy';
  if (daysToMaturity === 1) return 'vence mañana';
  return `vence en ${daysToMaturity} días`;
}

/** Tono del chip: urgente cuando falta poco o ya venció. */
export function maturityTone(daysToMaturity: number | null): 'urgent' | 'soon' | 'calm' {
  if (daysToMaturity === null) return 'calm';
  if (daysToMaturity <= 0) return 'urgent';
  if (daysToMaturity <= 7) return 'soon';
  return 'calm';
}

/** Días enteros desde un timestamp hasta ahora (para "actualizada hace X días"). */
export function daysSince(timestamp: string, now: Date = new Date()): number {
  const t = new Date(/(Z|[+-]\d{2}:?\d{2})$/i.test(timestamp) ? timestamp : `${timestamp}Z`);
  return Math.max(0, Math.floor((now.getTime() - t.getTime()) / 86_400_000));
}

export function ageLabel(days: number): string {
  if (days === 0) return 'hoy';
  if (days === 1) return 'hace 1 día';
  return `hace ${days} días`;
}

// ── Valuación local (solo modo mock) ────────────────────────────────────────

type InvestmentBase = Omit<
  Investment,
  'effective_value' | 'value_source' | 'gain' | 'gain_pct' | 'days_to_maturity' | 'is_matured' | 'fixed_term'
>;

/** Réplica de `valuation.py` para el modo mock: mismos campos que la API real. */
export function enrichInvestment(base: InvestmentBase, now: Date = new Date()): Investment {
  let fixedTerm: FixedTermInfo | null = null;
  if (
    base.asset_type === 'fixed_term' &&
    base.interest_rate_tna !== null &&
    base.start_date &&
    base.maturity_date
  ) {
    const preview = fixedTermPreview(
      base.invested_amount,
      base.interest_rate_tna,
      base.start_date,
      base.maturity_date,
    );
    if (preview) {
      const elapsed = Math.min(
        Math.max(-daysUntilDate(base.start_date, now), 0),
        preview.termDays,
      );
      fixedTerm = {
        term_days: preview.termDays,
        interest_total: preview.interest,
        amount_at_maturity: preview.amountAtMaturity,
        accrued_interest: round2((base.invested_amount * base.interest_rate_tna * elapsed) / 100 / 365),
        tea_pct: round2(
          (Math.pow(1 + (base.interest_rate_tna / 100) * (preview.termDays / 365), 365 / preview.termDays) - 1) * 100,
        ),
      };
    }
  }

  let value = base.invested_amount;
  let source: ValueSource = 'invested';
  if (base.current_value !== null) {
    value = base.current_value;
    source = 'manual';
  } else if (fixedTerm) {
    value = round2(base.invested_amount + fixedTerm.accrued_interest);
    source = 'fixed_term_accrued';
  }
  const gain = round2(value - base.invested_amount);
  const days = base.maturity_date ? daysUntilDate(base.maturity_date, now) : null;
  return {
    ...base,
    effective_value: value,
    value_source: source,
    gain,
    gain_pct: base.invested_amount > 0 ? round2((gain / base.invested_amount) * 100) : null,
    days_to_maturity: days,
    is_matured: days !== null && days < 0,
    fixed_term: fixedTerm,
  };
}
