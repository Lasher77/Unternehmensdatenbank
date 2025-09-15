'use client';

import { Person } from '@/lib/schemas';

export default function PersonList({ persons }: { persons: Person[] }) {
  if (!persons || persons.length === 0) {
    return <div>No persons</div>;
  }
  return (
    <ul className="list-disc pl-5 space-y-1">
      {persons.map((p) => (
        <li key={p.source_person_id}>
          {[p.first_name, p.last_name].filter(Boolean).join(' ')}
          {p.roles && p.roles.length > 0 && (
            <ul className="ml-4 list-disc space-y-1">
              {p.roles.map((r, idx) => (
                <li key={idx}>
                  {[r.role_name, r.role_type, r.role_date].filter(Boolean).join(' - ')}
                </li>
              ))}
            </ul>
          )}
        </li>
      ))}
    </ul>
  );
}
