// Helpers de inversiones: formato es-AR, coma decimal y la vista previa del
// plazo fijo. Los montos oficiales los calcula el server (Decimal, half-up);
// esto es solo para previsualizar antes de guardar y para el modo mock.

import type {
  AssetType,
  FixedTermInfo,
  Investment,
  InvestmentCurrency,
  RealReturn,
  RealReturnReason,
  ValueSource,
} from '../types';
import { daysUntilDate, parseDateOnly, toLocalDateString } from './date';

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

// ── Rendimiento real: textos y formato ──────────────────────────────────────

/** `+0,56 %` / `-1,94 %`, siempre con signo explícito y coma decimal. */
export function formatPct(value: number, withSign = true): string {
  const sign = withSign && value > 0 ? '+' : '';
  return `${sign}${value.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} %`;
}

const MONTHS_ES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

/** "2026-10" → "oct 2026". */
export function monthLabel(period: string): string {
  const [year, month] = period.split('-');
  return `${MONTHS_ES[Number(month) - 1] ?? month} ${year}`;
}

/** Por qué no hay rendimiento real, en castellano llano. */
export function realReturnReasonText(reason: RealReturnReason | null | undefined): string | null {
  switch (reason) {
    case 'currency':
      return 'En dólares no se compara con la inflación local';
    case 'no_start_date':
      return 'Cargá la fecha de compra para ver el rendimiento real';
    case 'too_short':
      return 'Todavía es muy reciente para medir el rendimiento real';
    case 'no_inflation_data':
      return 'No tenemos la inflación de ese período';
    default:
      return null;
  }
}

/** "hace 4 min" / "hace 3 h" / "hace 2 días" a partir de un timestamp del server. */
export function relativeTime(timestamp: string, now: Date = new Date()): string {
  const t = new Date(/(Z|[+-]\d{2}:?\d{2})$/i.test(timestamp) ? timestamp : `${timestamp}Z`);
  const minutes = Math.max(0, Math.floor((now.getTime() - t.getTime()) / 60_000));
  if (minutes < 1) return 'hace un momento';
  if (minutes < 60) return `hace ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `hace ${hours} h`;
  const days = Math.floor(hours / 24);
  return days === 1 ? 'hace 1 día' : `hace ${days} días`;
}

// ── Valuación local (solo modo mock) ────────────────────────────────────────

/** Variación mensual del IPC que usa el modo mock (no hay serie real). */
export const MOCK_MONTHLY_INFLATION = 1.9;

/** Precios de cripto que usa el modo mock (USD). */
export const MOCK_CRYPTO_PRICES: Record<string, number> = {
  BTC: 79509,
  ETH: 2500,
  USDT: 1,
  USDC: 1,
  SOL: 150,
};

type InvestmentBase = Omit<
  Investment,
  | 'effective_value'
  | 'value_source'
  | 'gain'
  | 'gain_pct'
  | 'days_to_maturity'
  | 'is_matured'
  | 'fixed_term'
  | 'quote_provider'
  | 'quote_stale'
  | 'real_return'
  | 'real_return_unavailable_reason'
>;

function mockProjection(
  invested: number,
  interest: number,
  start: string,
  maturity: string,
) {
  const days = Math.round((parseDateOnly(maturity).getTime() - parseDateOnly(start).getTime()) / 86_400_000);
  if (days < 1 || invested <= 0) return null;
  const factor = Math.pow(1 + MOCK_MONTHLY_INFLATION / 100, days / 30.4);
  const nominal = interest / invested;
  return {
    nominal_pct: round2(nominal * 100),
    inflation_pct: round2((factor - 1) * 100),
    real_pct: round2(((1 + nominal) / factor - 1) * 100),
    estimated: true,
  };
}

/** Réplica simplificada del cálculo del server para el modo mock. */
function mockRealReturn(
  base: InvestmentBase,
  value: number,
  fixedTerm: FixedTermInfo | null,
  now: Date,
): { real: RealReturn | null; reason: RealReturnReason | null } {
  if (base.currency !== 'ARS') return { real: null, reason: 'currency' };
  if (!base.start_date) return { real: null, reason: 'no_start_date' };
  let end = toLocalDateString(now);
  const matured = base.maturity_date !== null && base.maturity_date < end;
  if (base.asset_type === 'fixed_term' && matured && base.maturity_date) end = base.maturity_date;
  const days = Math.round((parseDateOnly(end).getTime() - parseDateOnly(base.start_date).getTime()) / 86_400_000);
  if (days < 1 || base.invested_amount <= 0) return { real: null, reason: 'too_short' };
  const factor = Math.pow(1 + MOCK_MONTHLY_INFLATION / 100, days / 30.4);
  const nominal = value / base.invested_amount - 1;
  const month = end.slice(0, 7);
  const projection =
    base.status === 'active' && fixedTerm && base.maturity_date && !matured
      ? mockProjection(base.invested_amount, fixedTerm.interest_total, base.start_date, base.maturity_date)
      : null;
  return {
    real: {
      nominal_pct: round2(nominal * 100),
      inflation_pct: round2((factor - 1) * 100),
      real_pct: round2(((1 + nominal) / factor - 1) * 100),
      estimated: true,
      estimated_months: [month],
      period_start: base.start_date,
      period_end: end,
      projected_at_maturity: projection,
    },
    reason: null,
  };
}

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
  const automatic = base.price_source === 'coingecko';
  if (automatic && base.quantity !== null && base.last_price != null) {
    value = round2(base.quantity * base.last_price);
    source = 'quote';
  } else if (base.current_value !== null) {
    value = base.current_value;
    source = 'manual';
  } else if (fixedTerm) {
    value = round2(base.invested_amount + fixedTerm.accrued_interest);
    source = 'fixed_term_accrued';
  }
  const gain = round2(value - base.invested_amount);
  const days = base.maturity_date ? daysUntilDate(base.maturity_date, now) : null;
  const { real, reason } = mockRealReturn(base, value, fixedTerm, now);
  return {
    ...base,
    effective_value: value,
    value_source: source,
    gain,
    gain_pct: base.invested_amount > 0 ? round2((gain / base.invested_amount) * 100) : null,
    days_to_maturity: days,
    is_matured: days !== null && days < 0,
    fixed_term: fixedTerm,
    quote_provider: automatic ? 'CoinGecko' : null,
    quote_stale: automatic && base.last_price_at ? false : null,
    real_return: real,
    real_return_unavailable_reason: real ? null : reason,
  };
}

// ── Cotización del dólar / euro ─────────────────────────────────────────────

const FX_KIND_LABELS: Record<string, string> = {
  oficial: 'Oficial',
  mep: 'MEP',
  blue: 'Blue',
  manual: 'Manual',
};

export const USD_SOURCE_OPTIONS = ['oficial', 'mep', 'blue', 'manual'] as const;
export const EUR_SOURCE_OPTIONS = ['oficial', 'blue', 'manual'] as const;

export function fxKindLabel(kind: string | null | undefined): string {
  return (kind && FX_KIND_LABELS[kind]) || '';
}

const PROVIDER_LABELS: Record<string, string> = {
  dolarapi: 'DolarAPI',
  bluelytics: 'Bluelytics',
  argentinadatos: 'ArgentinaDatos',
};

export function providerLabel(provider: string | null | undefined): string {
  return (provider && PROVIDER_LABELS[provider]) || provider || '';
}

/** "Dólar MEP $ 1.563,90 · DolarAPI · hace 12 min" (o la versión manual). */
export function describeFxRate(
  currency: 'USD' | 'EUR',
  rate: number | null,
  effective: string | null | undefined,
  provider: string | null | undefined,
  asOf: string | null | undefined,
): string | null {
  if (rate === null || !effective) return null;
  const name = currency === 'USD' ? 'Dólar' : 'Euro';
  const symbolCurrency: InvestmentCurrency = 'ARS';
  const value = formatMoney(rate, symbolCurrency);
  if (effective === 'manual' || effective === 'manual_fallback') {
    return `${name} manual ${value}${asOf ? ` · actualizada ${relativeTime(asOf)}` : ''}`;
  }
  const parts = [`${name} ${fxKindLabel(effective)} ${value}`];
  if (provider) parts.push(providerLabel(provider));
  if (asOf) parts.push(relativeTime(asOf));
  return parts.join(' · ');
}
