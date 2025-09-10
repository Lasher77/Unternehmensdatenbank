'use client';

import { useEffect, useRef } from 'react';
import { useCreateImport } from '@/lib/queries';
import { env } from '@/lib/env';
import { api } from '@/lib/api';
import { sleep, formatBytes } from '@/lib/utils';
import JobStatusBadge, { JobStatus } from './job-status-badge';
import { toast } from './toast';

export type ImportItem = {
  id: string;
  file: File;
  name: string;
  size: number;
  status: JobStatus;
  progress: number;
  taskId?: string;
  error?: string;
};

interface Props {
  label: string;
  items: ImportItem[];
  setItems: (items: ImportItem[] | ((items: ImportItem[]) => ImportItem[])) => void;
}

export default function ImportList({ label, items, setItems }: Props) {
  const createImport = useCreateImport();
  const uploadingRef = useRef(false);

  useEffect(() => {
    async function process() {
      if (uploadingRef.current) return;
      const next = items.find((i) => i.status === 'ready');
      if (!next || !label) return;
      uploadingRef.current = true;
      try {
        setItems((arr) => arr.map((i) => (i.id === next.id ? { ...i, status: 'uploading', progress: 0 } : i)));
        const res = await createImport.mutateAsync({
          label,
          file: next.file,
          onUploadProgress: (e) => {
            const prog = e.total ? Math.round((e.loaded / e.total) * 100) : 0;
            setItems((arr) => arr.map((i) => (i.id === next.id ? { ...i, progress: prog } : i)));
          }
        });
        setItems((arr) => arr.map((i) => (i.id === next.id ? { ...i, status: 'processing', taskId: res.task_id, progress: 100 } : i)));
        await pollTask(next.id, res.task_id);
      } catch (e: any) {
        toast.error(e.message);
        setItems((arr) => arr.map((i) => (i.id === next.id ? { ...i, status: 'error', error: e.message } : i)));
      } finally {
        uploadingRef.current = false;
        process();
      }
    }
    process();
  }, [items, label, createImport, setItems]);

  async function pollTask(localId: string, taskId: string) {
    if (env.fakeTaskPoll) {
      await sleep(2000);
      setItems((arr) => arr.map((i) => (i.id === localId ? { ...i, status: 'done' } : i)));
      return;
    }
    for (let i = 0; i < 60; i++) {
      try {
        const { data } = await api.get(`/api/tasks/${taskId}`);
        if (data.state === 'SUCCESS') {
          setItems((arr) => arr.map((i) => (i.id === localId ? { ...i, status: 'done' } : i)));
          return;
        }
        if (data.state === 'FAILURE') {
          setItems((arr) => arr.map((i) => (i.id === localId ? { ...i, status: 'error', error: 'Task failed' } : i)));
          return;
        }
      } catch (e: any) {
        toast.error(e.message);
      }
      await sleep(2000);
    }
  }

  function retry(id: string) {
    setItems((arr) => arr.map((i) => (i.id === id ? { ...i, status: 'ready', progress: 0, error: undefined } : i)));
  }

  function remove(id: string) {
    setItems((arr) => arr.filter((i) => i.id !== id));
  }

  return (
    <div className="mt-4 space-y-2">
      {items.map((item) => (
        <div key={item.id} className="p-2 border rounded flex items-center gap-4">
          <div className="flex-1">
            <div className="font-medium">{item.name}</div>
            <div className="text-xs text-muted-foreground">{formatBytes(item.size)}</div>
            {item.status === 'uploading' && (
              <div className="w-full bg-secondary h-2 rounded mt-1">
                <div className="h-2 bg-primary rounded" style={{ width: `${item.progress}%` }} />
              </div>
            )}
          </div>
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
      ))}
    </div>
  );
}
