'use client';

import { CompanyDetailCompany } from '@/lib/schemas';
import { MapPin } from 'lucide-react';

export default function Address({ company }: { company: CompanyDetailCompany }) {
  const { street, postal_code, city, state, country } = company;
  if (!street && !postal_code && !city && !state && !country) {
    return <div className="text-sm text-muted-foreground">Keine Adresse hinterlegt.</div>;
  }
  return (
    <div className="space-y-1 text-sm">
      <div className="inline-flex items-center gap-2 rounded-md bg-muted px-2 py-1 text-muted-foreground">
        <MapPin className="h-4 w-4" />
        <span>Standort</span>
      </div>
      {street && <div className="text-foreground">{street}</div>}
      {(postal_code || city) && <div>{[postal_code, city].filter(Boolean).join(' ')}</div>}
      {state && <div>{state}</div>}
      {country && <div>{country}</div>}
    </div>
  );
}
