'use client';

import { CompanyDetailCompany } from '@/lib/schemas';

export default function Address({ company }: { company: CompanyDetailCompany }) {
  const { street, postal_code, city, state, country } = company;
  if (!street && !postal_code && !city && !state && !country) {
    return <div>No address</div>;
  }
  return (
    <div className="space-y-1">
      {street && <div>{street}</div>}
      {(postal_code || city) && (
        <div>{[postal_code, city].filter(Boolean).join(' ')}</div>
      )}
      {state && <div>{state}</div>}
      {country && <div>{country}</div>}
    </div>
  );
}
