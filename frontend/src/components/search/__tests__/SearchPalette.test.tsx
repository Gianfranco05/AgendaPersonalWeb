import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Routes, Route } from 'react-router-dom';
import { useState } from 'react';
import { renderWithProviders } from '../../../test/test-utils';
import { LocationProbe } from '../../../test/openParam';
import SearchPalette from '../SearchPalette';
import Highlight from '../Highlight';
import type { SearchItem, SearchResponse } from '../../../types';

vi.mock('../../../api/endpoints', () => ({ searchAll: vi.fn() }));
import { searchAll } from '../../../api/endpoints';

const item = (over: Partial<SearchItem>): SearchItem => ({
  id: 'x',
  type: 'notes' as const,
  entity: 'note',
  title: 'Título',
  title_highlights: [],
  snippet: null,
  snippet_highlights: [],
  date: '2026-10-20T13:05:00Z',
  parent_id: null,
  path: '/notes?open=x',
  meta: null,
  ...over,
});

const RESPONSE: SearchResponse = {
  query: 'cafe',
  groups: [
    {
      type: 'notes',
      label: 'Notas',
      has_more: true,
      items: [
        item({ id: 'n1', title: 'Café con Juan', title_highlights: [[0, 4]], snippet: 'quedamos en el café', snippet_highlights: [[15, 19]], path: '/notes?open=n1', meta: { tags: ['personal'], archived: false } }),
        item({ id: 'n2', title: '<img src=x onerror=alert(1)> café', title_highlights: [[28, 32]], path: '/notes?open=n2', meta: { tags: [], archived: true } }),
      ],
    },
    {
      type: 'transactions',
      label: 'Movimientos',
      has_more: false,
      items: [
        item({ id: 't1', type: 'transactions' as const, entity: 'transaction', title: 'Café molido', title_highlights: [[0, 4]], date: '2026-10-10', path: '/finances?tab=transacciones&open=t1', meta: { amount: '1234.50', currency: 'ARS', type: 'expense' } }),
      ],
    },
  ],
};

function Harness({ initialOpen = true }: { initialOpen?: boolean }) {
  const [open, setOpen] = useState(initialOpen);
  return (
    <>
      <button onClick={() => setOpen(true)}>abrir</button>
      <SearchPalette open={open} onClose={() => setOpen(false)} />
      <LocationProbe />
    </>
  );
}

function renderPalette(initialOpen = true) {
  return renderWithProviders(
    <Routes>
      <Route path="*" element={<Harness initialOpen={initialOpen} />} />
    </Routes>,
    { router: { initialEntries: ['/'] } },
  );
}

beforeEach(() => {
  vi.mocked(searchAll).mockReset();
  vi.mocked(searchAll).mockResolvedValue(RESPONSE);
});

describe('SearchPalette', () => {
  it('muestra ayuda y no llama al server con menos de 2 caracteres', async () => {
    const user = userEvent.setup();
    renderPalette();
    const input = screen.getByRole('combobox');
    await user.type(input, 'c');
    expect(screen.getByText('Escribí al menos 2 letras')).toBeInTheDocument();
    await new Promise((r) => setTimeout(r, 400));
    expect(searchAll).not.toHaveBeenCalled();
  });

  it('el debounce manda una sola request aunque se tipee de corrido', async () => {
    const user = userEvent.setup();
    renderPalette();
    await user.type(screen.getByRole('combobox'), 'cafe');
    await screen.findByText('Notas');
    expect(searchAll).toHaveBeenCalledTimes(1);
    expect(searchAll).toHaveBeenCalledWith('cafe', { types: undefined, limit: undefined });
  });

  it('muestra los grupos con su etiqueta, el resaltado en <mark> y "Archivada"', async () => {
    const user = userEvent.setup();
    renderPalette();
    await user.type(screen.getByRole('combobox'), 'cafe');
    await screen.findByText('Movimientos');
    const options = screen.getAllByRole('option');
    expect(options.some((o) => within(o).queryByText('Café', { selector: 'mark' }))).toBe(true);
    expect(screen.getByText('Archivada')).toBeInTheDocument();
    expect(screen.getByText('personal')).toBeInTheDocument();
    // monto formateado en es-AR con la moneda
    expect(screen.getByText(/1\.234,50/)).toBeInTheDocument();
  });

  it('un título con HTML se muestra literal, sin crear elementos', async () => {
    const user = userEvent.setup();
    renderPalette();
    await user.type(screen.getByRole('combobox'), 'cafe');
    await screen.findByText('Movimientos');
    expect(document.querySelector('img')).toBeNull();
    expect(screen.getByText(/<img src=x onerror=alert\(1\)>/)).toBeInTheDocument();
  });

  it('el teclado recorre la lista aplanada de todos los grupos con wrap', async () => {
    const user = userEvent.setup();
    renderPalette();
    const input = screen.getByRole('combobox');
    await user.type(input, 'cafe');
    await screen.findByText('Movimientos');
    const options = screen.getAllByRole('option');
    // n1, n2, "Ver más en Notas", t1
    expect(options).toHaveLength(4);
    const active = () => input.getAttribute('aria-activedescendant');

    expect(active()).toBe(options[0].id);
    await user.keyboard('{ArrowDown}');
    expect(active()).toBe(options[1].id);
    await user.keyboard('{ArrowDown}{ArrowDown}');
    expect(active()).toBe(options[3].id); // cruzó al grupo siguiente
    await user.keyboard('{ArrowDown}');
    expect(active()).toBe(options[0].id); // wrap al principio
    await user.keyboard('{ArrowUp}');
    expect(active()).toBe(options[3].id); // wrap al final
    expect(options[3]).toHaveAttribute('aria-selected', 'true');
  });

  it('Enter sobre un resultado navega a su path y cierra la paleta', async () => {
    const user = userEvent.setup();
    renderPalette();
    await user.type(screen.getByRole('combobox'), 'cafe');
    await screen.findByText('Movimientos');
    await user.keyboard('{Enter}');
    expect(screen.getByTestId('location')).toHaveTextContent('/notes?open=n1');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('un clic en un resultado navega a su path', async () => {
    const user = userEvent.setup();
    renderPalette();
    await user.type(screen.getByRole('combobox'), 'cafe');
    await screen.findByText('Movimientos');
    await user.click(screen.getAllByRole('option').at(-1)!);
    expect(screen.getByTestId('location')).toHaveTextContent('/finances?tab=transacciones&open=t1');
  });

  it('"Ver más" repite la búsqueda para ese tipo con limit=20', async () => {
    const user = userEvent.setup();
    renderPalette();
    await user.type(screen.getByRole('combobox'), 'cafe');
    await screen.findByText('Notas');
    await user.click(await screen.findByRole('option', { name: /Ver más en Notas/ }));
    await waitFor(() =>
      expect(searchAll).toHaveBeenLastCalledWith('cafe', { types: ['notes'], limit: 20 }),
    );
  });

  it('sin resultados muestra el mensaje con la búsqueda', async () => {
    vi.mocked(searchAll).mockResolvedValue({ query: 'zzz', groups: [] });
    const user = userEvent.setup();
    renderPalette();
    await user.type(screen.getByRole('combobox'), 'zzz');
    expect(await screen.findByText(/No encontramos nada para «zzz»/)).toBeInTheDocument();
  });

  it('un error 429 avisa que se busca muy rápido', async () => {
    vi.mocked(searchAll).mockRejectedValue({ response: { status: 429 }, isAxiosError: true });
    const user = userEvent.setup();
    renderPalette();
    await user.type(screen.getByRole('combobox'), 'cafe');
    expect(await screen.findByText('Estás buscando muy rápido, esperá un momento')).toBeInTheDocument();
  });

  it('otro error muestra un mensaje genérico', async () => {
    vi.mocked(searchAll).mockRejectedValue(new Error('boom'));
    const user = userEvent.setup();
    renderPalette();
    await user.type(screen.getByRole('combobox'), 'cafe');
    expect(await screen.findByText('No pudimos buscar. Probá de nuevo.')).toBeInTheDocument();
  });

  it('Esc cierra y devuelve el foco al elemento que estaba antes', async () => {
    const user = userEvent.setup();
    renderPalette(false);
    const opener = screen.getByText('abrir');
    opener.focus();
    await user.click(opener);
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    expect(screen.getByRole('combobox')).toHaveFocus();
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(opener).toHaveFocus();
  });

  it('el foco queda atrapado dentro del diálogo con Tab', async () => {
    const user = userEvent.setup();
    renderPalette();
    const dialog = screen.getByRole('dialog');
    for (let i = 0; i < 6; i++) {
      await user.tab();
      expect(dialog.contains(document.activeElement)).toBe(true);
    }
  });

  it('la lista sigue el patrón ARIA combobox/listbox', async () => {
    const user = userEvent.setup();
    renderPalette();
    const input = screen.getByRole('combobox');
    await user.type(input, 'cafe');
    await screen.findByText('Movimientos');
    const list = screen.getByRole('listbox');
    expect(input).toHaveAttribute('aria-controls', list.id);
    expect(input).toHaveAttribute('aria-expanded', 'true');
    expect(input.getAttribute('aria-activedescendant')).toBe(screen.getAllByRole('option')[0].id);
  });
});

describe('Highlight', () => {
  it('envuelve los rangos en <mark> sin interpretar HTML', () => {
    const { container } = renderWithProviders(
      <Highlight text="<b>hola</b> mundo" ranges={[[3, 7]]} />,
    );
    expect(container.querySelector('b')).toBeNull();
    expect(container.querySelector('mark')).toHaveTextContent('hola');
    expect(container).toHaveTextContent('<b>hola</b> mundo');
  });

  it('sin rangos no genera marcas', () => {
    const { container } = renderWithProviders(<Highlight text="sin marcas" ranges={[]} />);
    expect(container.querySelector('mark')).toBeNull();
  });
});
