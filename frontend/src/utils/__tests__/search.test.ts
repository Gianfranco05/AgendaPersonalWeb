import { describe, it, expect } from 'vitest';
import {
  FOLD_TABLE,
  foldText,
  tokenize,
  highlightRanges,
  splitByRanges,
  matchRank,
  MIN_QUERY_LENGTH,
  isSearchable,
} from '../search';

describe('foldText', () => {
  it('quita tildes, baja mayúsculas y pliega la ñ', () => {
    expect(foldText('Café')).toBe('cafe');
    expect(foldText('REUNIÓN ANUAL')).toBe('reunion anual');
    expect(foldText('Niña')).toBe('nina');
    expect(foldText('Pingüino')).toBe('pinguino');
  });

  it('conserva el largo (los offsets del plegado valen para el original)', () => {
    for (const s of ['Café con Juan', 'ÁÉÍÓÚÜÑ', 'x_y%z\\', '日本語 ABC', 'ß ç']) {
      expect(foldText(s)).toHaveLength(s.length);
    }
  });

  it('no toca lo que está fuera de la tabla (igual que el backend)', () => {
    expect(foldText('ç')).toBe('ç');
    expect(foldText('Ç')).toBe('Ç');
  });

  it('usa exactamente la misma tabla que backend/app/modules/buscador/normalize.py', () => {
    // Si alguien amplía la tabla en un lado y no en el otro, este test avisa.
    expect(FOLD_TABLE).toEqual({
      á: 'a', é: 'e', í: 'i', ó: 'o', ú: 'u', ü: 'u', ñ: 'n',
      Á: 'a', É: 'e', Í: 'i', Ó: 'o', Ú: 'u', Ü: 'u', Ñ: 'n',
    });
  });
});

describe('tokenize', () => {
  it('recorta, colapsa espacios y pliega los tokens', () => {
    expect(tokenize('  Café   Con\tJuan ')).toEqual({
      query: 'Café Con Juan',
      tokens: ['cafe', 'con', 'juan'],
    });
  });

  it('se queda con 5 tokens como mucho', () => {
    expect(tokenize('a1 b2 c3 d4 e5 f6 g7').tokens).toEqual(['a1', 'b2', 'c3', 'd4', 'e5']);
  });

  it('isSearchable exige entre 2 y 100 caracteres reales', () => {
    expect(MIN_QUERY_LENGTH).toBe(2);
    expect(isSearchable(' a ')).toBe(false);
    expect(isSearchable('ab')).toBe(true);
    expect(isSearchable('   ')).toBe(false);
    expect(isSearchable('a'.repeat(101))).toBe(false);
  });
});

describe('highlightRanges', () => {
  it('devuelve offsets sobre el texto original, aun con tildes', () => {
    expect(highlightRanges('Café con Juan', ['cafe'])).toEqual([[0, 4]]);
  });

  it('encuentra todas las apariciones y fusiona las que se pisan', () => {
    expect(highlightRanges('Juan, el café de Juan', ['juan', 'cafe'])).toEqual([[0, 4], [9, 13], [17, 21]]);
    expect(highlightRanges('banana', ['ana', 'nan'])).toEqual([[1, 6]]);
  });

  it('sin coincidencias o sin texto devuelve vacío', () => {
    expect(highlightRanges('nada', ['zzz'])).toEqual([]);
    expect(highlightRanges(null, ['x'])).toEqual([]);
  });
});

describe('splitByRanges', () => {
  it('corta el texto en partes marcadas y sin marcar', () => {
    expect(splitByRanges('Café con Juan', [[0, 4], [9, 13]])).toEqual([
      { text: 'Café', mark: true },
      { text: ' con ', mark: false },
      { text: 'Juan', mark: true },
    ]);
  });

  it('sin rangos devuelve el texto entero y recorta rangos fuera de límite', () => {
    expect(splitByRanges('hola', [])).toEqual([{ text: 'hola', mark: false }]);
    expect(splitByRanges('hola', [[2, 99], [-3, 1]])).toEqual([
      { text: 'h', mark: true },
      { text: 'o', mark: false },
      { text: 'la', mark: true },
    ]);
  });

  it('el HTML queda como texto plano', () => {
    const parts = splitByRanges('<b>hola</b>', [[3, 7]]);
    expect(parts.map((p) => p.text).join('')).toBe('<b>hola</b>');
    expect(parts[1]).toEqual({ text: 'hola', mark: true });
  });
});

describe('matchRank', () => {
  const tokens = ['pagar', 'luz'];
  it('0 si el título empieza con la frase completa', () => {
    expect(matchRank('Pagar luz', 'pagar luz', tokens)).toBe(0);
  });
  it('1 si el título contiene todos los tokens', () => {
    expect(matchRank('Recordar pagar la luz', 'pagar luz', tokens)).toBe(1);
  });
  it('2 si coincide solo en otros campos', () => {
    expect(matchRank('Cuentas', 'pagar luz', tokens)).toBe(2);
  });
});
