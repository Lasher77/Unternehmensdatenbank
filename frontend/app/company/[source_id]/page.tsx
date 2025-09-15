'use client';

import { useCompanyDetail } from '@/lib/queries';
import Address from '@/components/address';
import IndustryCodes from '@/components/industry-codes';
import PersonList from '@/components/person-list';

export default function CompanyPage({ params }: { params: { source_id: string } }) {
  const { data, isLoading } = useCompanyDetail(params.source_id);

  if (isLoading) return <div>Loading...</div>;
  if (!data) return <div>Not found</div>;

  const { company, events, persons, industry_codes } = data;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">{company.name}</h1>
      <div>
        <h2 className="font-medium">Address</h2>
        <Address company={company} />
      </div>
      <div>
        <h2 className="font-medium">Industry</h2>
        <IndustryCodes codes={industry_codes} />
      </div>
      <div>
        <h2 className="font-medium">Persons</h2>
        <PersonList persons={persons} />
      </div>
      <div>
        <h2 className="font-medium">Coordinates</h2>
        <div className="h-48 bg-muted flex items-center justify-center">
          {company.lat && company.lng ? `${company.lat}, ${company.lng}` : 'No coordinates'}
        </div>
      </div>
      <div>
        <h2 className="font-medium">Events</h2>
        <ul className="list-disc pl-5 space-y-1">
          {events?.map((e, idx) => (
            <li key={e.event_id ?? idx}>
              {e.event_date ? `${e.event_date}: ` : ''}
              {e.event_type}
              {e.description ? ` - ${e.description}` : ''}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
