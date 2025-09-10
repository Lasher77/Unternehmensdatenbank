'use client';

import { useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useSearchCompanies } from '@/lib/queries';
import FiltersPanel from '@/components/filters-panel';
import ResultsTable from '@/components/results-table';
import ExportDialog from '@/components/export-dialog';

export default function SearchPage() {
  const params = useSearchParams();
  const queryObj = useMemo(() => {
    const obj: any = {
      query: params.get('query') ?? undefined,
      page: Number(params.get('page') ?? '1'),
      per_page: Number(params.get('per_page') ?? '20'),
      sort: params.get('sort') ?? undefined,
      filters: {} as Record<string, string[]>
    };
    params.forEach((v, k) => {
      if (!['query', 'page', 'per_page', 'sort'].includes(k)) {
        obj.filters[k] = obj.filters[k] ? [...obj.filters[k], v] : [v];
      }
    });
    return obj;
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
              <ExportDialog selectedIds={selected} />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
