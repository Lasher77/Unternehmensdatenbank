'use client';

import { useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useSearchCompanies } from '@/lib/queries';
import { SearchRequest } from '@/lib/schemas';
import FiltersPanel from '@/components/filters-panel';
import ResultsTable from '@/components/results-table';
import ExportDialog from '@/components/export-dialog';

export default function SearchPage() {
  const params = useSearchParams();
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

  const { data, isLoading } = useSearchCompanies(queryObj);
  const [selected, setSelected] = useState<string[]>([]);

  return (
    <div className="grid md:grid-cols-[250px_1fr] gap-4">
      <FiltersPanel facets={data?.facets ?? {}} />
      <div className="space-y-4">
        {isLoading && <div>Loading...</div>}
        {data && (
          <>
            <ResultsTable data={data.results} selected={selected} onSelectedChange={setSelected} />
            <div className="flex justify-end">
              <ExportDialog selectedIds={selected} request={queryObj} />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
