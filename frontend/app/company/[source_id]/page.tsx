'use client';

import { useCompanyDetail } from '@/lib/queries';

export default function CompanyPage({ params }: { params: { source_id: string } }) {
  const { data, isLoading } = useCompanyDetail(params.source_id);

  if (isLoading) return <div>Loading...</div>;
  if (!data) return <div>Not found</div>;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">{data.name}</h1>
      <div>
        <h2 className="font-medium">Coordinates</h2>
        <div className="h-48 bg-muted flex items-center justify-center">
          {data.lat && data.lng ? `${data.lat}, ${data.lng}` : 'No coordinates'}
        </div>
      </div>
      <div>
        <h2 className="font-medium">Events</h2>
        <ul className="list-disc pl-5">
          {data.events?.map((e: any, idx: number) => (
            <li key={idx}>{e}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
