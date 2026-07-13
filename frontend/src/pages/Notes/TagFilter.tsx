import type { Tag } from '../../types';

interface TagFilterProps {
  tags: Tag[];
  activeTag: string | null;
  onSelect: (tagId: string | null) => void;
}

export default function TagFilter({ tags, activeTag, onSelect }: TagFilterProps) {
  return (
    <div className="flex gap-1.5 overflow-x-auto py-1">
      <button
        onClick={() => onSelect(null)}
        className={`flex-shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
          activeTag === null
            ? 'bg-gray-200 text-gray-700 dark:text-slate-200'
            : 'bg-gray-100 dark:bg-slate-700 text-gray-500 dark:text-slate-400 hover:bg-gray-200 dark:hover:bg-slate-600'
        }`}
      >
        Todas
      </button>
      {tags.map((tag) => (
        <button
          key={tag.id}
          onClick={() => onSelect(tag.id === activeTag ? null : tag.id)}
          className="flex-shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors"
          style={{
            backgroundColor: tag.id === activeTag ? tag.color : `${tag.color}20`,
            color: tag.id === activeTag ? '#fff' : tag.color,
          }}
        >
          {tag.name}
        </button>
      ))}
    </div>
  );
}
