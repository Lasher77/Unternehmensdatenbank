'use client';

import { useMemo, useState } from 'react';
import ImportUploader from '@/components/import-uploader';
import ImportList, { ImportItem } from '@/components/import-list';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { formatBytes } from '@/lib/utils';

export default function ImportPage() {
  const [label, setLabel] = useState('');
  const [items, setItems] = useState<ImportItem[]>([]);

  const summary = useMemo(() => {
    const completed = items.filter((i) => i.finishedAt);
    const lastSuccess = completed
      .filter((i) => i.status === 'done')
      .sort((a, b) => new Date(b.finishedAt ?? 0).getTime() - new Date(a.finishedAt ?? 0).getTime())[0];
    const durations = completed
      .map((i) => {
        if (!i.startedAt || !i.finishedAt) return null;
        return new Date(i.finishedAt).getTime() - new Date(i.startedAt).getTime();
      })
      .filter((v): v is number => Number.isFinite(v));
    const averageDuration = durations.length
      ? Math.round(durations.reduce((a, b) => a + b, 0) / durations.length / 1000)
      : null;

    return { lastSuccess, averageDuration };
  }, [items]);

  function handleFiles(files: File[]) {
    const newItems = files.map((file) => ({
      id: Math.random().toString(36).slice(2),
      file,
      name: file.name,
      size: file.size,
      status: 'ready' as const,
      progress: 0,
      summaryStatus: 'idle' as const,
      label,
      createdAt: new Date().toISOString()
    }));
    setItems((prev) => [...prev, ...newItems]);
  }

  const allDone = items.length > 0 && items.every((i) => i.status === 'done');

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="space-y-1">
          <h1 className="text-3xl font-semibold">Import</h1>
          <p className="text-sm text-muted-foreground">
            Lade neue Datenstände hoch und verfolge den Fortschritt deiner Importläufe.
          </p>
        </div>
        <Card className="w-full md:w-auto">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Health</CardTitle>
            <CardDescription>Zuletzt aktualisiert</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            <div className="text-sm">
              <span className="text-muted-foreground">Letzter erfolgreicher Import:</span>{' '}
              {summary.lastSuccess?.finishedAt
                ? new Date(summary.lastSuccess.finishedAt).toLocaleString()
                : '–'}
            </div>
            <div className="text-sm">
              <span className="text-muted-foreground">Ø Dauer (letzte Läufe):</span>{' '}
              {summary.averageDuration ? `${summary.averageDuration} Sekunden` : '–'}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Neuen Import starten</CardTitle>
          <CardDescription>Vergib einen sprechenden Namen und lade deine Dateien hoch.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="import-label">Label</Label>
            <Input
              id="import-label"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="z.B. North Data Q3 2025"
            />
          </div>
          <ImportUploader onFiles={handleFiles} />
          {allDone && <div className="text-sm text-green-600">Alle Uploads abgeschlossen</div>}
        </CardContent>
      </Card>

      <ImportList label={label} items={items} setItems={setItems} />

      <ImportHistory items={items} />
    </div>
  );
}

function ImportHistory({ items }: { items: ImportItem[] }) {
  const runs = useMemo(
    () =>
      [...items].sort(
        (a, b) => new Date(b.finishedAt ?? b.createdAt).getTime() - new Date(a.finishedAt ?? a.createdAt).getTime()
      ),
    [items]
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>Import-Historie</CardTitle>
        <CardDescription>Nachverfolgung der letzten Uploads und Ergebnisse.</CardDescription>
      </CardHeader>
      <CardContent>
        {runs.length === 0 ? (
          <p className="text-sm text-muted-foreground">Bisher wurden keine Imports ausgeführt.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-muted/60 text-muted-foreground">
                <tr>
                  <th className="px-3 py-2 text-left">Datum</th>
                  <th className="px-3 py-2 text-left">Label</th>
                  <th className="px-3 py-2 text-left">Status</th>
                  <th className="px-3 py-2 text-left">Datei</th>
                  <th className="px-3 py-2 text-left">Summen</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.id} className="border-t">
                    <td className="px-3 py-2 text-muted-foreground">
                      {new Date(run.finishedAt ?? run.createdAt).toLocaleString()}
                    </td>
                    <td className="px-3 py-2 font-medium">{run.label || 'Ohne Label'}</td>
                    <td className="px-3 py-2">
                      <Badge variant={run.status === 'done' ? 'success' : run.status === 'error' ? 'destructive' : 'warning'}>
                        {run.status}
                      </Badge>
                    </td>
                    <td className="px-3 py-2 text-muted-foreground">
                      {run.name} ({formatBytes(run.size)})
                    </td>
                    <td className="px-3 py-2 text-muted-foreground">
                      {run.summary && Object.keys(run.summary).length > 0
                        ? Object.entries(run.summary)
                            .map(([table, count]) => `${table}: ${count}`)
                            .join(', ')
                        : '–'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
