/** Clase que anima el resaltado (definida en index.css). */
export const REVEAL_CLASS = 'search-reveal';
const REVEAL_MS = 2500;

/**
 * Lleva la vista a `#item-<id>` y lo resalta un momento. Es el destino de
 * respaldo del buscador cuando la página no tiene un modal de detalle para esa
 * entidad. Devuelve `false` si el elemento no está en el DOM.
 */
export function revealItem(id: string): boolean {
  const el = document.getElementById(`item-${id}`);
  if (!el) return false;
  el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  el.classList.add(REVEAL_CLASS);
  setTimeout(() => el.classList.remove(REVEAL_CLASS), REVEAL_MS);
  return true;
}
