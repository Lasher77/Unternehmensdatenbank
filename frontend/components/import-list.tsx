'use client';

import { useCallback, useEffect, useMemo, useRef } from 'react';
import { useCreateImport, useImportSummary } from '@/lib/queries';
import { env } from '@/lib/env';
import { api } from '@/lib/api';
import { sleep, formatBytes } from '@/lib/utils';
import JobStatusBadge, { JobStatus } from './job-status-badge';
import { toast } from './toast';

type SummaryStatus = 'idle' | 'loading' | 'success' | 'error';

export type ImportItem = {
  id: string;
  file: File;
  name: string;
  size: number;
  status: JobStatus;
  progress: number;
  taskId?: string;
  error?: string;
  runId?: number;
  finishedAt?: string;
  summary?: Record<string, number>;
  summaryStatus: SummaryStatus;
  summaryError?: string;
  label: string;
  createdAt: string;
  startedAt?: string;
};

interface Props {
  label: string;
  items: ImportItem[];
  setItems: (items: ImportItem[] | ((items: ImportItem[]) => ImportItem[])) => void;
}

export default function ImportList({ label, items, setItems }: Props) {
  const createImport = useCreateImport();
  const uploadingRef = useRef(false);

  const pollTask = useCallback(
    async (localId: string, taskId: string) => {
      if (process.env.NODE_ENV !== 'production' && env.fakeTaskPoll) {
        await sleep(2000);
        setItems((arr) =>
          arr.map((i) =>
            i.id === localId
              ? {
                  ...i,
                  status: 'done',
                  summaryStatus: 'success',
                  summary: i.summary ?? {},
                }
              : i
          )
        );
        return;
      }
      for (let i = 0; i < 60; i++) {
        try {
          const { data } = await api.get(`/api/tasks/${taskId}`);
          if (data.state === 'SUCCESS') {
            const info = (data.info || data.meta) as Record<string, any> | undefined;
            const runIdValue = Number(info?.run_id);
            setItems((arr) =>
              arr.map((i) => {
                if (i.id !== localId) return i;
                if (Number.isFinite(runIdValue)) {
                  return {
                    ...i,
                    status: 'done',
                    runId: runIdValue,
                    summary: undefined,
                    summaryStatus: 'loading',
                    summaryError: undefined,
                    finishedAt:
                      typeof info?.finished_at === 'string'
                        ? info.finished_at
                        : i.finishedAt ?? new Date().toISOString(),
                  };
                }
                toast.error('Die Run-ID des Imports konnte nicht ermittelt werden.');
                return {
                  ...i,
                  status: 'done',
                  summaryStatus: 'error',
                  summaryError: 'Run-ID fehlt',
                };
              })
            );
            return;
          }
          if (data.state === 'FAILURE') {
            setItems((arr) =>
              arr.map((i) => (i.id === localId ? { ...i, status: 'error', error: 'Task failed' } : i))
            );
            return;
          }
        } catch (e: any) {
          toast.error(e.message);
        }
        await sleep(2000);
      }
    },
    [setItems]
  );

  useEffect(() => {
    if (uploadingRef.current) return;

    const next = items.find((i) => i.status === 'ready');
    if (!next) return;

    const effectiveLabel = next.label || label;
    if (!effectiveLabel) return;

    uploadingRef.current = true;

    async function process() {
      try {
        const startedAt = new Date().toISOString();

        setItems((arr) =>
          arr.map((i) =>
            i.id === next.id
              ? {
                  ...i,
                  status: 'uploading',
                  progress: 0,
                  runId: undefined,
                  summary: undefined,
                  summaryStatus: 'idle',
                  summaryError: undefined,
                  finishedAt: undefined,
                  startedAt,
                }
              : i
          )
        );
        const res = await createImport.mutateAsync({
          label: effectiveLabel,
          file: next.file,
          onUploadProgress: (e) => {
            const prog = e.total ? Math.round((e.loaded / e.total) * 100) : 0;
            setItems((arr) => arr.map((i) => (i.id === next.id ? { ...i, progress: prog } : i)));
          }
        });
        setItems((arr) =>
          arr.map((i) =>
            i.id === next.id
              ? {
                  ...i,
                  status: 'processing',
                  taskId: res.task_id,
                  progress: 100,
                  summaryStatus: 'idle',
                }
              : i
          )
        );
        await pollTask(next.id, res.task_id);
      } catch (e: any) {
        toast.error(e.message);
        setItems((arr) =>
          arr.map((i) =>
            i.id === next.id
              ? {
                  ...i,
                  status: 'error',
                  error: e.message,
                  summaryStatus: 'error',
                  summaryError: e.message,
                }
              : i
          )
        );
      } finally {
        uploadingRef.current = false;
      }
    }

    process();
  }, [items, label, createImport, pollTask, setItems]);

  function retry(id: string) {
    setItems((arr) =>
      arr.map((i) =>
        i.id === id
          ? {
              ...i,
              status: 'ready',
              progress: 0,
              error: undefined,
              summary: undefined,
              summaryStatus: 'idle',
              summaryError: undefined,
              runId: undefined,
              finishedAt: undefined,
              startedAt: undefined,
            }
          : i
      )
    );
  }

  function remove(id: string) {
    setItems((arr) => arr.filter((i) => i.id !== id));
  }

  return (
    <div className="mt-4 space-y-3">
      {items.map((item) => (
        <ImportListItem key={item.id} item={item} remove={remove} retry={retry} setItems={setItems} />
      ))}
    </div>
  );
}

interface ItemProps {
  item: ImportItem;
  setItems: Props['setItems'];
  remove: (id: string) => void;
  retry: (id: string) => void;
}

function ImportListItem({ item, setItems, remove, retry }: ItemProps) {
  const shouldFetchSummary = useMemo(
    () => item.summaryStatus === 'loading' && !!item.runId,
    [item.summaryStatus, item.runId]
  );
  useImportSummaryFetcher({ item, setItems, enabled: shouldFetchSummary });

  return (
    <div className="p-3 border rounded space-y-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="flex-1">
          <div className="font-medium break-words">{item.name}</div>
          <div className="text-xs text-muted-foreground">{formatBytes(item.size)}</div>
          {item.status === 'uploading' && (
            <div className="w-full bg-secondary h-2 rounded mt-2 overflow-hidden">
              <div className="h-2 bg-primary transition-all" style={{ width: `${item.progress}%` }} />
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <JobStatusBadge status={item.status} />
          {item.status === 'ready' && (
            <button className="px-2 py-1 text-sm border rounded" onClick={() => remove(item.id)}>
              Remove
            </button>
          )}
          {item.status === 'error' && (
            <button className="px-2 py-1 text-sm border rounded" onClick={() => retry(item.id)}>
              Retry
            </button>
          )}
        </div>
      </div>

      {item.status === 'done' && <ImportSummarySection item={item} />}
    </div>
  );
}

function ImportSummarySection({ item }: { item: ImportItem }) {
  if (item.summaryStatus === 'loading') {
    return <div className="text-sm text-muted-foreground">Zusammenfassung wird geladen...</div>;
  }

  if (item.summaryStatus === 'error') {
    return (
      <div className="text-sm text-destructive">
        <span className="inline-flex items-center gap-2 rounded border border-destructive/40 bg-destructive/10 px-2 py-1">
          Fehler beim Laden der Zusammenfassung{item.summaryError ? `: ${item.summaryError}` : ''}
        </span>
      </div>
    );
  }

  const summaryEntries = Object.entries(item.summary ?? {});

  if (summaryEntries.length === 0) {
    return <div className="text-sm text-muted-foreground">Keine Zusammenfassung verfügbar.</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-[240px] text-sm">
        <thead>
          <tr className="text-left text-muted-foreground">
            <th className="py-1 pr-4 font-medium">Tabelle</th>
            <th className="py-1 font-medium">Anzahl</th>
          </tr>
        </thead>
        <tbody>
          {summaryEntries.map(([tableName, count]) => (
            <tr key={tableName} className="border-t">
              <td className="py-1 pr-4 capitalize">{tableName.replace(/_/g, ' ')}</td>
              <td className="py-1 font-mono">{count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface SummaryFetcherProps {
  item: ImportItem;
  setItems: Props['setItems'];
  enabled: boolean;
}

function useImportSummaryFetcher({ item, setItems, enabled }: SummaryFetcherProps) {
  const { data, isError, error } = useImportSummary(item.runId, enabled);

  useEffect(() => {
    if (!enabled || !data) return;

    setItems((arr) =>
      arr.map((i) => {
        if (i.id !== item.id) {
          return i;
        }

        const finishedAt = data.finished_at ?? undefined;
        if (!data.finished) {
          return {
            ...i,
            summary: data.summary,
            finishedAt,
          };
        }

        if (
          i.summaryStatus === 'success' &&
          i.finishedAt === finishedAt &&
          shallowEqualSummaries(i.summary, data.summary)
        ) {
          return i;
        }

        return {
          ...i,
          summary: data.summary,
          finishedAt,
          summaryStatus: 'success',
          summaryError: undefined,
        };
      })
    );
  }, [data, enabled, item.id, setItems]);

  useEffect(() => {
    if (!enabled || !isError) return;

    const message = error instanceof Error ? error.message : 'Unbekannter Fehler';
    toast.error(message);
    setItems((arr) =>
      arr.map((i) =>
        i.id === item.id
          ? {
              ...i,
              summaryStatus: 'error',
              summaryError: message,
            }
          : i
      )
    );
  }, [enabled, error, isError, item.id, setItems]);
}

function shallowEqualSummaries(a?: Record<string, number>, b?: Record<string, number>) {
  if (a === b) return true;
  if (!a || !b) return false;
  const keysA = Object.keys(a);
  const keysB = Object.keys(b);
  if (keysA.length !== keysB.length) return false;
  return keysA.every((key) => a[key] === b[key]);
}
