/** Mensaje de error de una respuesta de la API: `detail` como string, o el
 *  primer `msg` de la lista de un 422. Si no hay nada usable, `fallback`. */
export function apiErrorMessage(err: unknown, fallback: string): string {
  const data = (err as { response?: { data?: { detail?: unknown } } })?.response?.data;
  const detail = data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && typeof detail[0]?.msg === 'string') return detail[0].msg;
  return fallback;
}
