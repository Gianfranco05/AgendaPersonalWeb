import { useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { showToast } from '../store/toastStore';

export interface OpenRequest {
  id: string;
  /** Qué entidad es (exam, packing_item, maintenance...) cuando la página tiene varias. */
  entity: string | null;
  /** Id del padre de una entidad hija (materia de un examen, viaje de un ítem...). */
  parent: string | null;
  /** Pestaña inicial (Finanzas: transacciones | inversiones). */
  tab: string | null;
}

/** `true` abrió el elemento, `false` no existe más, `'wait'` todavía no se
 *  puede decidir (falta cargar algo) y se reintenta en el próximo render. */
export type OpenResult = boolean | 'wait';

interface Options {
  /** La lista de la página ya cargó: antes de eso no se puede saber si el id existe. */
  ready: boolean;
  onOpen: (req: OpenRequest) => OpenResult;
}

const PARAMS = ['open', 'entity', 'parent', 'tab'] as const;

/**
 * Abre el elemento que pide el buscador (`?open=<id>`): llama al handler de la
 * página (abrir su modal de edición, o hacer scroll y resaltarlo), avisa si el
 * id ya no existe y limpia la URL con `replace` para que volver atrás o
 * re-renderizar no lo reabra.
 */
export function useOpenParam({ ready, onOpen }: Options): void {
  const [params, setParams] = useSearchParams();
  const handled = useRef<string | null>(null);
  const onOpenRef = useRef(onOpen);
  onOpenRef.current = onOpen;

  const id = params.get('open');
  const entity = params.get('entity');
  const parent = params.get('parent');
  const tab = params.get('tab');

  useEffect(() => {
    if (!id || !ready) return;
    const key = `${id}|${entity ?? ''}|${parent ?? ''}|${tab ?? ''}`;
    if (handled.current === key) return;

    const result = onOpenRef.current({ id, entity, parent, tab });
    if (result === 'wait') return;

    handled.current = key;
    if (result === false) showToast('Ese elemento ya no existe');
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        PARAMS.forEach((p) => next.delete(p));
        return next;
      },
      { replace: true },
    );
  });
}
