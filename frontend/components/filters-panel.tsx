'use client';

import React, { useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { MapPin, Scale, Shield, Building2, Filter } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Input } from './ui/input';
import { Badge } from './ui/badge';

interface Facets {
  [key: string]: { value: string; count: number }[];
}

const facetLabels: Record<string, { label: string; icon?: React.ElementType }> = {
  city: { label: 'Stadt', icon: MapPin },
  state: { label: 'Bundesland', icon: MapPin },
  status: { label: 'Status', icon: Shield },
  legal_form: { label: 'Rechtsform', icon: Scale },
  country: { label: 'Land', icon: Building2 },
  postal_code: { label: 'PLZ', icon: MapPin },
  wz: { label: 'WZ', icon: Filter }
};

export default function FiltersPanel({ facets }: { facets: Facets }) {
  const params = useSearchParams();
  const router = useRouter();
  const [searchTerms, setSearchTerms] = useState<Record<string, string>>({});
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const facetEntries = useMemo(() => Object.entries(facets ?? {}), [facets]);

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

  function filteredBuckets(key: string, buckets: { value: string; count: number }[]) {
    const term = searchTerms[key]?.toLowerCase().trim();
    if (!term) return buckets;
    return buckets.filter((b) => b.value.toLowerCase().includes(term));
  }

  return (
    <aside className="space-y-4 lg:sticky lg:top-24">
      <Card>
        <CardHeader className="pb-4">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <CardTitle className="text-lg">Filter</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {facetEntries.length === 0 && (
            <p className="text-sm text-muted-foreground">Keine Filter verfügbar.</p>
          )}
          {facetEntries.map(([key, buckets]) => {
            const labelInfo = facetLabels[key] ?? { label: key };
            const Icon = labelInfo.icon;
            const filtered = filteredBuckets(key, buckets);
            const showAll = expanded[key];
            const displayBuckets = showAll ? filtered : filtered.slice(0, 8);
            const hasMore = filtered.length > displayBuckets.length;
            return (
              <Card key={key} className="border-muted">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 text-sm font-semibold">
                      {Icon && <Icon className="h-4 w-4 text-muted-foreground" />}
                      <span className="capitalize">{labelInfo.label}</span>
                    </div>
                    <Badge variant="outline" className="text-[11px]">
                      {params.getAll(key).length} aktiv
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3 pt-0">
                  {buckets.length > 6 && (
                    <Input
                      value={searchTerms[key] ?? ''}
                      onChange={(e) => setSearchTerms((prev) => ({ ...prev, [key]: e.target.value }))}
                      placeholder="In dieser Facette suchen"
                      className="h-9"
                    />
                  )}
                  <div className="space-y-2 max-h-64 overflow-auto pr-1">
                    {displayBuckets.map((b) => {
                      const active = params.getAll(key).includes(b.value);
                      return (
                        <label
                          key={b.value}
                          className={`flex cursor-pointer items-start gap-2 rounded-md border border-transparent px-2 py-1 text-sm transition hover:border-muted-foreground/20 hover:bg-muted/60 ${
                            active ? 'bg-primary/5 text-foreground' : ''
                          }`}
                        >
                          <input
                            type="checkbox"
                            className="mt-0.5 h-4 w-4 rounded border-muted-foreground/30 text-primary focus:ring-1 focus:ring-primary"
                            checked={active}
                            onChange={() => toggleFilter(key, b.value)}
                          />
                          <div className="flex flex-1 items-center justify-between gap-3">
                            <span className="truncate text-sm" title={b.value}>
                              {b.value}
                            </span>
                            <span className="text-xs text-muted-foreground">{b.count.toLocaleString()}</span>
                          </div>
                        </label>
                      );
                    })}
                    {displayBuckets.length === 0 && (
                      <p className="text-xs text-muted-foreground">Keine Werte gefunden.</p>
                    )}
                  </div>
                  {hasMore && (
                    <button
                      className="text-sm font-semibold text-primary hover:underline"
                      onClick={() => setExpanded((prev) => ({ ...prev, [key]: !prev[key] }))}
                    >
                      {showAll ? 'Weniger anzeigen' : 'Mehr anzeigen'}
                    </button>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </CardContent>
      </Card>
    </aside>
  );
}
