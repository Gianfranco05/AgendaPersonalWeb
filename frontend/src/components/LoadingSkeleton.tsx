interface LoadingSkeletonProps {
  type?: 'card' | 'table' | 'widget' | 'page';
  rows?: number;
}

function SkeletonBar({ className = '' }: { className?: string }) {
  return (
    <div className={`skeleton-shimmer rounded ${className}`} />
  );
}

export function LoadingSkeleton({ type = 'card', rows = 3 }: LoadingSkeletonProps) {
  if (type === 'table') {
    return (
      <div className="space-y-3">
        <div className="flex gap-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <SkeletonBar key={i} className="h-4 flex-1" />
          ))}
        </div>
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex gap-4">
            {Array.from({ length: 5 }).map((_, j) => (
              <SkeletonBar key={j} className="h-6 flex-1" />
            ))}
          </div>
        ))}
      </div>
    );
  }

  if (type === 'page') {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <SkeletonBar className="h-8 w-48" />
          <SkeletonBar className="h-10 w-36" />
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <SkeletonBar className="h-28 rounded-xl" />
          <SkeletonBar className="h-28 rounded-xl" />
          <SkeletonBar className="h-28 rounded-xl" />
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <SkeletonBar className="h-80 rounded-xl" />
          <SkeletonBar className="h-80 rounded-xl" />
        </div>
        <SkeletonBar className="h-64 rounded-xl" />
      </div>
    );
  }

  if (type === 'widget') {
    return (
      <div className="space-y-3 rounded-xl bg-white dark:bg-slate-800 p-6 shadow-sm">
        <SkeletonBar className="h-5 w-1/3" />
        <SkeletonBar className="h-8 w-1/2" />
        <SkeletonBar className="h-4 w-full" />
        <SkeletonBar className="h-4 w-4/5" />
      </div>
    );
  }

  // card
  return (
    <div className="space-y-3 rounded-xl bg-white dark:bg-slate-800 p-6 shadow-sm">
      <SkeletonBar className="h-5 w-2/3" />
      <SkeletonBar className="h-4 w-full" />
      <SkeletonBar className="h-4 w-3/4" />
    </div>
  );
}
