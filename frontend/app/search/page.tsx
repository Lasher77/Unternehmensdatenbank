'use client';

import { useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useIndexStats, useSearchCompanies } from '@/lib/queries';
import { SearchRequest } from '@/lib/schemas';
import FiltersPanel from '@/components/filters-panel';
import ResultsTable from '@/components/results-table';
import ExportDialog from '@/components/export-dialog';
import SearchBar from '@/components/search-bar';
import { AlertCircle, FilterX, Info, RefreshCcw } from 'lucide-react';

export default function SearchPage() {
  const params = useSearchParams();
  const router = useRouter();
  const queryObj = useMemo<SearchRequest>(() => {
    const toInt = (value: string | null, fallback: number) => {
      const parsed = Number(value);
      return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
    };

    const toNumber = (value: string | null) => {
      if (value === null) {
        return undefined;
      }
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : undefined;
    };

    return {
      query: params.get('query') ?? undefined,
      state: params.get('state') ?? undefined,
      city: params.get('city') ?? undefined,
      postal_code: params.get('postal_code') ?? undefined,
      wz: params.get('wz') ?? undefined,
      status: params.get('status') ?? undefined,
      legal_form: params.get('legal_form') ?? undefined,
      lat: toNumber(params.get('lat')),
      lng: toNumber(params.get('lng')),
      radius_km: toNumber(params.get('radius_km')),
      sort: params.get('sort') ?? undefined,
      page: toInt(params.get('page'), 1),
      per_page: toInt(params.get('per_page'), 20)
    };
  }, [params]);

  const { data, isLoading, isError, error } = useSearchCompanies(queryObj);
  const stats = useIndexStats();
  const [selected, setSelected] = useState<string[]>([]);

  const activeFilters = useMemo(() => {
    const filterKeys = ['state', 'city', 'postal_code', 'wz', 'status', 'legal_form'];
    const labels: Record<string, string> = {
      state: 'Bundesland',
      city: 'Stadt',
      postal_code: 'PLZ',
      wz: 'WZ',
      status: 'Status',
      legal_form: 'Rechtsform'
    };
    return filterKeys.flatMap((key) =>
      params.getAll(key).map((value) => ({ key, value, label: labels[key] ?? key }))
    );
  }, [params]);

  function removeFilter(key: string, value: string) {
    const url = new URL(window.location.href);
    const values = url.searchParams.getAll(key).filter((v) => v !== value);
    url.searchParams.delete(key);
    values.forEach((v) => url.searchParams.append(key, v));
    url.searchParams.set('page', '1');
    router.push(url.pathname + '?' + url.searchParams.toString());
  }

  function resetFilters() {
    const url = new URL(window.location.href);
    ['state', 'city', 'postal_code', 'wz', 'status', 'legal_form', 'lat', 'lng', 'radius_km', 'page'].forEach((k) =>
      url.searchParams.delete(k)
    );
    router.push(url.pathname + (url.searchParams.toString() ? '?' + url.searchParams.toString() : ''));
  }

  return (
    <div className="space-y-6">
      <Card className="overflow-hidden border-primary/10 bg-gradient-to-r from-white via-white to-muted/40">
        <CardHeader className="space-y-4 pb-2">
          <div className="flex items-center justify-between gap-4">
            <div className="space-y-2">
              <p className="text-sm font-medium text-primary">Unternehmenssuche</p>
              <CardTitle className="text-3xl">Finde schnell die richtigen Firmen</CardTitle>
              <CardDescription>
                Suche nach Name, Domain, HRB oder Ort und verfeinere die Ergebnisse mit präzisen Filtern.
              </CardDescription>
            </div>
            <Badge variant="outline" className="whitespace-nowrap">Datenstand: –</Badge>
          </div>
          <SearchBar />
        </CardHeader>
        <CardContent className="pt-0">
          <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
            <Info className="h-4 w-4" />
            {stats.isLoading && <span>Index-Statistiken werden geladen…</span>}
            {stats.data && (
              <span>
                Aktuell {stats.data.companies?.toLocaleString() ?? '–'} Unternehmen und{' '}
                {stats.data.events?.toLocaleString() ?? '–'} Events im Index
              </span>
            )}
            {stats.isError && <span>Index-Statistiken konnten nicht geladen werden.</span>}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <FiltersPanel facets={data?.facets ?? {}} />

        <div className="space-y-4">
          {activeFilters.length > 0 && (
            <Card>
              <CardContent className="flex flex-wrap items-center gap-2 py-4">
                <span className="text-sm font-semibold text-muted-foreground">Aktive Filter:</span>
                {activeFilters.map((filter) => (
                  <Badge
                    key={`${filter.key}-${filter.value}`}
                    variant="secondary"
                    className="flex items-center gap-1"
                  >
                    <span className="capitalize">{filter.label}:</span> {filter.value}
                    <button
                      type="button"
                      onClick={() => removeFilter(filter.key, filter.value)}
                      className="ml-1 text-muted-foreground hover:text-foreground"
                    >
                      <FilterX className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
                <Button variant="ghost" size="sm" onClick={resetFilters} className="ml-auto">
                  <RefreshCcw className="mr-2 h-4 w-4" /> Alle Filter zurücksetzen
                </Button>
              </CardContent>
            </Card>
          )}

          {isError && (
            <Card className="border-destructive/40 bg-destructive/5">
              <CardContent className="flex items-center gap-3 py-4 text-destructive">
                <AlertCircle className="h-5 w-5" />
                <div className="flex-1">
                  <p className="font-semibold">Suche fehlgeschlagen</p>
                  <p className="text-sm text-destructive/80">
                    {error instanceof Error ? error.message : 'Die Ergebnisse konnten nicht geladen werden.'}
                  </p>
                </div>
                <Button variant="outline" size="sm" onClick={() => window.location.reload()}>
                  Erneut versuchen
                </Button>
              </CardContent>
            </Card>
          )}

          {isLoading && <ResultsSkeleton />}

          {!isLoading && data && data.total === 0 && (
            <EmptyResults onReset={resetFilters} />
          )}

          {data && data.total > 0 && (
            <>
              <ResultsTable data={data.results} selected={selected} onSelectedChange={setSelected} />
              <div className="flex flex-col items-end gap-2 text-sm text-muted-foreground">
                <span>{data.total.toLocaleString()} Ergebnisse</span>
                <ExportDialog selectedIds={selected} request={queryObj} />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function ResultsSkeleton() {
  return (
    <Card className="overflow-hidden">
      <CardContent className="divide-y p-0">
        {[...Array(5)].map((_, idx) => (
          <div key={idx} className="flex items-start gap-4 px-4 py-3">
            <Skeleton className="h-4 w-4 rounded" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-1/3" />
              <Skeleton className="h-3 w-1/4" />
              <Skeleton className="h-3 w-1/5" />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function EmptyResults({ onReset }: { onReset: () => void }) {
  return (
    <Card className="text-center">
      <CardHeader>
        <CardTitle>Keine Unternehmen gefunden</CardTitle>
        <CardDescription>
          Versuche einen allgemeineren Begriff oder entferne einige Filter.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Button onClick={onReset}>
          <RefreshCcw className="mr-2 h-4 w-4" /> Alle Filter zurücksetzen
        </Button>
      </CardContent>
    </Card>
  );
}
