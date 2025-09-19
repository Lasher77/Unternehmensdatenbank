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

  const normalizedStatus = company.status ? company.status.trim().toLowerCase() : undefined;
  const statusTranslations: Record<string, { label: string; classes: string }> = {
    active: { label: 'Aktiv', classes: 'bg-green-100 text-green-800' },
    terminated: { label: 'Inaktiv', classes: 'bg-gray-200 text-gray-800' },
    inactive: { label: 'Inaktiv', classes: 'bg-gray-200 text-gray-800' }
  };

  let statusLabel: string | null = null;
  let statusClasses = 'rounded-full px-2 py-0.5 text-xs font-semibold ';

  if (company.terminated === true) {
    statusLabel = 'Inaktiv';
    statusClasses += 'bg-gray-200 text-gray-800';
  } else if (normalizedStatus && statusTranslations[normalizedStatus]) {
    const { label, classes } = statusTranslations[normalizedStatus];
    statusLabel = label;
    statusClasses += classes;
  } else if (normalizedStatus) {
    statusLabel = normalizedStatus.charAt(0).toUpperCase() + normalizedStatus.slice(1);
    statusClasses += 'bg-muted text-muted-foreground';
  } else if (company.terminated === false) {
    statusLabel = 'Aktiv';
    statusClasses += 'bg-green-100 text-green-800';
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <h1 className="text-2xl font-bold">{company.name}</h1>
        {statusLabel && <span className={statusClasses}>{statusLabel}</span>}
      </div>
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
