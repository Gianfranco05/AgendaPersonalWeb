import { describe, it, expect } from 'vitest'
import {
  ageLabel,
  daysSince,
  enrichInvestment,
  fixedTermPreview,
  formatMoney,
  maturityLabel,
  maturityTone,
  parseDecimal,
} from '../investments'

describe('parseDecimal', () => {
  it.each([
    ['1500,50', 1500.5],
    ['1500.50', 1500.5],
    ['1.500,50', 1500.5],
    ['1.000.000,25', 1000000.25],
    ['1.000.000', 1000000],
    ['12.345.678', 12345678],
    ['1.5', 1.5],
    ['0,00012345', 0.00012345],
    ['  42 ', 42],
    ['1500', 1500],
    ['0', 0],
  ])('acepta %s', (text, expected) => {
    expect(parseDecimal(text)).toBe(expected)
  })

  it.each([[''], ['   '], ['abc'], ['1,2,3'], ['--5'], ['1e5']])('rechaza %j', (text) => {
    expect(parseDecimal(text)).toBeNull()
  })
})

describe('formatMoney', () => {
  it('formatea es-AR con 2 decimales', () => {
    expect(formatMoney(1024657.53)).toBe('$ 1.024.657,53')
    expect(formatMoney(2000, 'USD')).toBe('US$ 2.000,00')
    expect(formatMoney(0.5, 'EUR')).toBe('€ 0,50')
    expect(formatMoney(-200, 'ARS')).toBe('-$ 200,00')
  })
})

describe('fixedTermPreview', () => {
  it('1.000.000 al 30 % a 30 días rinde 24.657,53', () => {
    const p = fixedTermPreview(1_000_000, 30, '2026-10-01', '2026-10-31')
    expect(p).toEqual({ termDays: 30, interest: 24657.53, amountAtMaturity: 1024657.53 })
  })

  it('devuelve null si falta algo o el plazo no es positivo', () => {
    expect(fixedTermPreview(null, 30, '2026-10-01', '2026-10-31')).toBeNull()
    expect(fixedTermPreview(1000, null, '2026-10-01', '2026-10-31')).toBeNull()
    expect(fixedTermPreview(1000, 30, '', '2026-10-31')).toBeNull()
    expect(fixedTermPreview(1000, 30, '2026-10-31', '2026-10-31')).toBeNull()
    expect(fixedTermPreview(1000, 30, '2026-11-01', '2026-10-31')).toBeNull()
  })
})

describe('chips de vencimiento', () => {
  it('textos', () => {
    expect(maturityLabel(null)).toBeNull()
    expect(maturityLabel(-3)).toBe('venció')
    expect(maturityLabel(0)).toBe('vence hoy')
    expect(maturityLabel(1)).toBe('vence mañana')
    expect(maturityLabel(5)).toBe('vence en 5 días')
  })

  it('tono', () => {
    expect(maturityTone(null)).toBe('calm')
    expect(maturityTone(-1)).toBe('urgent')
    expect(maturityTone(0)).toBe('urgent')
    expect(maturityTone(7)).toBe('soon')
    expect(maturityTone(8)).toBe('calm')
  })
})

describe('antigüedad de la cotización', () => {
  it('cuenta días enteros desde un timestamp del server (UTC sin sufijo)', () => {
    const now = new Date('2026-10-15T12:00:00Z')
    expect(daysSince('2026-10-12T12:00:00', now)).toBe(3)
    expect(daysSince('2026-10-15T01:00:00', now)).toBe(0)
  })

  it('etiquetas', () => {
    expect(ageLabel(0)).toBe('hoy')
    expect(ageLabel(1)).toBe('hace 1 día')
    expect(ageLabel(3)).toBe('hace 3 días')
  })
})

describe('enrichInvestment (modo mock)', () => {
  const base = {
    id: '1',
    asset_type: 'fixed_term' as const,
    name: 'PF',
    ticker: null,
    currency: 'ARS' as const,
    quantity: null,
    invested_amount: 1_000_000,
    current_value: null,
    interest_rate_tna: 30,
    start_date: '2026-10-01',
    maturity_date: '2026-10-31',
    institution: null,
    notes: null,
    status: 'active' as const,
    notify_maturity: true,
    value_updated_at: null,
  }

  it('plazo fijo devenga el interés a hoy', () => {
    const i = enrichInvestment(base, new Date(2026, 9, 13))
    expect(i.fixed_term?.accrued_interest).toBe(9863.01)
    expect(i.effective_value).toBe(1009863.01)
    expect(i.value_source).toBe('fixed_term_accrued')
    expect(i.days_to_maturity).toBe(18)
    expect(i.is_matured).toBe(false)
  })

  it('el valor manual gana y calcula ganancia', () => {
    const i = enrichInvestment(
      { ...base, asset_type: 'stock', invested_amount: 1000, current_value: 800, maturity_date: null },
      new Date(2026, 9, 13),
    )
    expect(i.gain).toBe(-200)
    expect(i.gain_pct).toBe(-20)
    expect(i.value_source).toBe('manual')
  })
})
