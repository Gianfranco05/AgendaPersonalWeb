import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { revealItem, REVEAL_CLASS } from '../reveal';

describe('revealItem', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    document.body.innerHTML = '<div id="item-abc">uno</div><div id="item-x y">dos</div>';
    Element.prototype.scrollIntoView = vi.fn();
  });
  afterEach(() => {
    vi.useRealTimers();
    document.body.innerHTML = '';
  });

  it('hace scroll al elemento, lo resalta un rato y devuelve true', () => {
    expect(revealItem('abc')).toBe(true);
    const el = document.getElementById('item-abc')!;
    expect(el.scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'center' });
    expect(el.classList.contains(REVEAL_CLASS)).toBe(true);
    vi.advanceTimersByTime(3000);
    expect(el.classList.contains(REVEAL_CLASS)).toBe(false);
  });

  it('devuelve false si el elemento no está en la página', () => {
    expect(revealItem('no-existe')).toBe(false);
  });

  it('encuentra ids con caracteres raros sin romper el selector', () => {
    expect(revealItem('x y')).toBe(true);
    expect(document.getElementById('item-x y')!.classList.contains(REVEAL_CLASS)).toBe(true);
  });
});
