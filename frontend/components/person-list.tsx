'use client';

import { Person } from '@/lib/schemas';
import { Badge } from './ui/badge';

export default function PersonList({ persons }: { persons: Person[] }) {
  if (!persons || persons.length === 0) {
    return <div className="text-sm text-muted-foreground">Keine Personen vorhanden.</div>;
  }
  return (
    <div className="space-y-3">
      {persons.map((p) => (
        <div key={p.source_person_id} className="rounded-md border border-muted bg-card p-3 shadow-sm">
          <div className="flex flex-wrap items-center gap-2 text-sm font-semibold">
            {[p.first_name, p.last_name].filter(Boolean).join(' ') || 'Unbekannte Person'}
          </div>
          {p.roles && p.roles.length > 0 ? (
            <div className="mt-2 flex flex-wrap gap-2">
              {p.roles.map((r, idx) => (
                <Badge key={idx} variant="secondary" className="text-xs">
                  {[r.role_name, r.role_type, r.role_date].filter(Boolean).join(' • ') || 'Rolle' }
                </Badge>
              ))}
            </div>
          ) : (
            <p className="mt-1 text-xs text-muted-foreground">Keine Rollen hinterlegt.</p>
          )}
        </div>
      ))}
    </div>
  );
}
