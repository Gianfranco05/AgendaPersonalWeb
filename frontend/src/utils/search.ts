// Plegado, tokenizado y resaltado del buscador. Replica exactamente el mapeo
// de backend/app/modules/buscador/normalize.py: si se amplía la tabla hay que
// hacerlo en los dos lados (hay un test que fija la tabla).

export const FOLD_TABLE: Record<string, string> = {
  á: 'a', é: 'e', í: 'i', ó: 'o', ú: 'u', ü: 'u', ñ: 'n',
  Á: 'a', É: 'e', Í: 'i', Ó: 'o', Ú: 'u', Ü: 'u', Ñ: 'n',
};

export const MIN_QUERY_LENGTH = 2;
export const MAX_QUERY_LENGTH = 100;
export const MAX_TOKENS = 5;

/** Minúsculas + sin tildes + ñ→n, 1 carácter a 1 carácter (conserva el largo).
 *  Solo baja ASCII y la tabla, como `lower()` de SQLite. */
export function foldText(text: string): string {
  let out = '';
  for (const ch of text) {
    const mapped = FOLD_TABLE[ch];
    if (mapped !== undefined) out += mapped;
    else if (ch.charCodeAt(0) < 128) out += ch.toLowerCase();
    else out += ch;
  }
  return out;
}

/** Query normalizada (NFC, espacios colapsados, sin caracteres de control). */
export function normalizeQuery(raw: string): string {
  return raw
    .normalize('NFC')
    .replace(/\s+/g, ' ')
    // eslint-disable-next-line no-control-regex
    .replace(/[\u0000-\u001f\u007f-\u009f]/g, '')
    .trim();
}

export function tokenize(raw: string): { query: string; tokens: string[] } {
  const query = normalizeQuery(raw);
  const tokens = query
    .split(' ')
    .filter(Boolean)
    .slice(0, MAX_TOKENS)
    .map(foldText);
  return { query, tokens };
}

/** Si la query ya se puede mandar al server (2 a 100 caracteres). */
export function isSearchable(raw: string): boolean {
  const { length } = normalizeQuery(raw);
  return length >= MIN_QUERY_LENGTH && length <= MAX_QUERY_LENGTH;
}

export type Range = [number, number];

/** Rangos `[inicio, fin)` donde aparece algún token, fusionando los que se pisan. */
export function highlightRanges(text: string | null | undefined, tokens: string[]): Range[] {
  if (!text || tokens.length === 0) return [];
  const folded = foldText(text);
  const spans: Range[] = [];
  for (const token of tokens) {
    if (!token) continue;
    let pos = folded.indexOf(token);
    while (pos !== -1) {
      spans.push([pos, pos + token.length]);
      pos = folded.indexOf(token, pos + 1);
    }
  }
  spans.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const merged: Range[] = [];
  for (const [start, end] of spans) {
    const last = merged[merged.length - 1];
    if (last && start <= last[1]) last[1] = Math.max(last[1], end);
    else merged.push([start, end]);
  }
  return merged;
}

export interface TextPart {
  text: string;
  mark: boolean;
}

/** Corta `text` por los rangos del server. Recorta rangos fuera de límite: el
 *  texto es siempre texto plano, nunca HTML. */
export function splitByRanges(text: string, ranges: ReadonlyArray<readonly [number, number]>): TextPart[] {
  const clean = ranges
    .map(([s, e]) => [Math.max(0, s), Math.min(text.length, e)] as const)
    .filter(([s, e]) => e > s)
    .sort((a, b) => a[0] - b[0]);
  if (clean.length === 0) return [{ text, mark: false }];
  const parts: TextPart[] = [];
  let cursor = 0;
  for (const [start, end] of clean) {
    const from = Math.max(start, cursor);
    if (end <= from) continue;
    if (from > cursor) parts.push({ text: text.slice(cursor, from), mark: false });
    parts.push({ text: text.slice(from, end), mark: true });
    cursor = end;
  }
  if (cursor < text.length) parts.push({ text: text.slice(cursor), mark: false });
  return parts;
}

/** Rango de relevancia (igual que el server): 0 el título empieza con la frase
 *  completa, 1 contiene todos los tokens, 2 coincide solo en otros campos. */
export function matchRank(title: string, foldedPhrase: string, tokens: string[]): 0 | 1 | 2 {
  const t = foldText(title);
  if (foldedPhrase && t.startsWith(foldedPhrase)) return 0;
  if (tokens.length > 0 && tokens.every((tok) => t.includes(tok))) return 1;
  return 2;
}
