'use client';

import Link from 'next/link';
import { ExternalLink } from 'lucide-react';
import { Badge } from './ui/badge';

export interface Company {
  source_id: string;
  name: string;
  status?: string | null;
  city?: string | null;
  postal_code?: string | null;
  country?: string | null;
  state?: string | null;
  domain?: string | null;
  legal_form?: string | null;
  terminated?: boolean | null;
  [key: string]: any;
}

interface ResultsTableProps {
  data: Company[];
  selected: string[];
  onSelectedChange: (ids: string[]) => void;
}

export default function ResultsTable({ data, selected, onSelectedChange }: ResultsTableProps) {
  const allSelected = selected.length === data.length && data.length > 0;

  function toggle(id: string, checked: boolean) {
    const next = checked ? [...selected, id] : selected.filter((s) => s !== id);
    onSelectedChange(next);
  }

  function toggleAll(checked: boolean) {
    if (checked) onSelectedChange(data.map((d) => d.source_id));
    else onSelectedChange([]);
  }

  return (
    <div className="overflow-x-auto rounded-lg border bg-card">
      <table className="min-w-full text-sm">
        <thead className="bg-muted/60 text-muted-foreground">
          <tr className="text-left">
            <th className="p-3">
              <input
                type="checkbox"
                aria-label="Alle auswählen"
                className="h-4 w-4 rounded border-muted-foreground/30 text-primary focus:ring-1 focus:ring-primary"
                checked={allSelected}
                onChange={(e) => toggleAll(e.target.checked)}
              />
            </th>
            <th className="p-3">Unternehmen</th>
            <th className="p-3">Status</th>
            <th className="p-3">Rechtsform</th>
            <th className="p-3">Region</th>
          </tr>
        </thead>
        <tbody>
          {data.map((item) => (
            <tr
              key={item.source_id}
              className="border-t transition-colors hover:bg-muted/60"
            >
              <td className="p-3 align-top">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-muted-foreground/30 text-primary focus:ring-1 focus:ring-primary"
                  checked={selected.includes(item.source_id)}
                  onChange={(e) => toggle(item.source_id, e.target.checked)}
                />
              </td>
              <td className="p-3 align-top">
                <div className="space-y-1">
                  <Link
                    href={`/company/${item.source_id}`}
                    className="text-base font-semibold text-primary hover:underline"
                  >
                    {item.name}
                  </Link>
                  <p className="text-sm text-muted-foreground">
                    {[item.postal_code, item.city, item.country].filter(Boolean).join(' ')}
                  </p>
                  {item.domain && (
                    <a
                      href={item.domain.startsWith('http') ? item.domain : `https://${item.domain}`}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
                    >
                      {item.domain.replace(/^https?:\/\//, '')}
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  )}
                </div>
              </td>
              <td className="p-3 align-top">
                {renderStatusBadge(item.status, item.terminated)}
              </td>
              <td className="p-3 align-top">
                {item.legal_form ? (
                  <Badge variant="secondary" className="capitalize">
                    {item.legal_form}
                  </Badge>
                ) : (
                  <span className="text-xs text-muted-foreground">–</span>
                )}
              </td>
              <td className="p-3 align-top text-sm text-muted-foreground">
                {item.state || item.country || '–'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function renderStatusBadge(status?: string | null, terminated?: boolean | null) {
  if (terminated) {
    return <Badge variant="destructive">Aufgelöst</Badge>;
  }
  if (!status) return <Badge variant="muted">Unbekannt</Badge>;

  const normalized = status.trim().toLowerCase();
  if (normalized === 'active' || normalized === 'aktiv') return <Badge variant="success">Aktiv</Badge>;
  if (normalized === 'processing') return <Badge variant="warning">In Bearbeitung</Badge>;
  return <Badge variant="outline">{status}</Badge>;
}
