import { splitByRanges } from '../../utils/search';

interface Props {
  text: string;
  ranges: ReadonlyArray<readonly [number, number]>;
}

/** Texto con los rangos que mandó el server envueltos en <mark>. Nunca
 *  interpreta HTML: el contenido de una nota se muestra siempre como texto. */
export default function Highlight({ text, ranges }: Props) {
  const parts = splitByRanges(text, ranges);
  return (
    <>
      {parts.map((part, i) =>
        part.mark ? (
          <mark
            key={i}
            className="rounded-sm bg-brand-indigo/20 px-0.5 font-semibold text-inherit"
          >
            {part.text}
          </mark>
        ) : (
          <span key={i}>{part.text}</span>
        ),
      )}
    </>
  );
}
