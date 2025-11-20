"use client";

import { useTableCounts } from "@/lib/queries";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

export default function SettingsPage() {
  const { data, isLoading, isError, error, refetch } = useTableCounts();

  const coreTables = ["companies", "events", "persons", "company_person_roles", "company_industries"];
  const stagingTables = data?.counts.filter((c) => c.table.startsWith("staging_")) ?? [];
  const otherTables = data?.counts.filter((c) => !coreTables.includes(c.table) && !c.table.startsWith("staging_")) ?? [];

  return (
    <div className="space-y-6">
      <section className="space-y-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-semibold">Settings</h1>
          <p className="text-sm text-muted-foreground">
            Übersicht der verfügbaren Datenbanktabellen und ihrer Datensätze.
          </p>
        </div>

        {isLoading && <Skeleton className="h-24 w-full" />}

        {isError && (
          <div className="space-y-2 rounded-md border border-destructive/40 bg-destructive/10 p-4 text-destructive">
            <p>{error instanceof Error ? error.message : "Failed to load table statistics."}</p>
            <Button type="button" variant="outline" onClick={() => refetch()}>
              Retry
            </Button>
          </div>
        )}

        {!isLoading && !isError && data && (
          <div className="space-y-6">
            <TableGroup title="Kern-Tabellen" description="Produktive Kerndaten" tables={coreTables} counts={data.counts} />
            <TableGroup
              title="Staging-Tabellen"
              description="Import- und Zwischenschritte"
              tables={stagingTables.map((c) => c.table)}
              counts={data.counts}
            />
            {otherTables.length > 0 && (
              <TableGroup
                title="Weitere Tabellen"
                description="Sonstige Strukturen"
                tables={otherTables.map((c) => c.table)}
                counts={data.counts}
              />
            )}
          </div>
        )}
      </section>
    </div>
  );
}

interface GroupProps {
  title: string;
  description: string;
  tables: string[];
  counts: { table: string; rows: number }[];
}

function TableGroup({ title, description, tables, counts }: GroupProps) {
  const entries = tables
    .map((table) => counts.find((c) => c.table === table))
    .filter((c): c is { table: string; rows: number } => Boolean(c));

  if (entries.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      <div className="space-y-1">
        <h2 className="text-xl font-semibold">{title}</h2>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {entries.map((entry) => (
          <Card key={entry.table} className="shadow-sm">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between gap-2">
                <CardTitle className="text-lg lowercase">{entry.table}</CardTitle>
                <Badge variant="outline" className="text-[11px] uppercase">Tabelle</Badge>
              </div>
              <CardDescription>Anzahl Datensätze</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{entry.rows.toLocaleString()}</div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
