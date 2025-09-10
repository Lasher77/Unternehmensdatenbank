'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import clsx from 'clsx';

interface Facets {
  [key: string]: { value: string; count: number }[];
}

export default function FiltersPanel({ facets }: { facets: Facets }) {
  const params = useSearchParams();
  const router = useRouter();

  function toggleFilter(key: string, value: string) {
    const url = new URL(window.location.href);
    const current = url.searchParams.getAll(key);
    if (current.includes(value)) {
      const next = current.filter((v) => v !== value);
      url.searchParams.delete(key);
      next.forEach((v) => url.searchParams.append(key, v));
    } else {
      url.searchParams.append(key, value);
    }
    url.searchParams.set('page', '1');
    router.push(url.pathname + '?' + url.searchParams.toString());
  }

  return (
    <aside className="space-y-4">
      {Object.entries(facets).map(([key, buckets]) => (
        <div key={key}>
          <h3 className="font-medium mb-2 capitalize">{key}</h3>
          <div className="flex flex-wrap gap-2">
            {buckets.map((b) => {
              const active = params.getAll(key).includes(b.value);
              return (
                <button
                  key={b.value}
                  onClick={() => toggleFilter(key, b.value)}
                  className={clsx(
                    'px-2 py-1 text-sm border rounded',
                    active && 'bg-primary text-primary-foreground'
                  )}
                >
                  {b.value} ({b.count})
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </aside>
  );
}
