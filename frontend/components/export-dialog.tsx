'use client';

import { useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useCreateExport } from '@/lib/queries';
import { toast } from './toast';

export default function ExportDialog({ selectedIds }: { selectedIds: string[] }) {
  const [open, setOpen] = useState(false);
  const [format, setFormat] = useState('csv');
  const [preset, setPreset] = useState('core');
  const createExport = useCreateExport();
  const params = useSearchParams();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const body: any = {
      format,
      preset,
      ids: selectedIds.length > 0 ? selectedIds : undefined,
      filters: Object.fromEntries(params.entries())
    };
    try {
      await createExport.mutateAsync(body);
      toast.success('Export gestartet');
      setOpen(false);
    } catch {
      // error toast handled globally
    }
  }

  return (
    <>
      <button className="px-3 py-1 border rounded" onClick={() => setOpen(true)} disabled={createExport.isPending}>
        Export
      </button>
      {open && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <form onSubmit={onSubmit} className="bg-white p-4 rounded space-y-4 w-80">
            <h2 className="text-lg font-medium">Export</h2>
            <div className="space-y-2">
              <label className="block text-sm">Format</label>
              <select value={format} onChange={(e) => setFormat(e.target.value)} className="w-full border px-2 py-1 rounded">
                <option value="csv">CSV</option>
                <option value="xlsx">XLSX</option>
                <option value="parquet">Parquet</option>
              </select>
            </div>
            <div className="space-y-2">
              <label className="block text-sm">Preset</label>
              <select value={preset} onChange={(e) => setPreset(e.target.value)} className="w-full border px-2 py-1 rounded">
                <option value="core">Core</option>
                <option value="sales">Sales</option>
                <option value="full">Full</option>
              </select>
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setOpen(false)} className="px-3 py-1 border rounded">
                Cancel
              </button>
              <button type="submit" className="px-3 py-1 bg-primary text-primary-foreground rounded" disabled={createExport.isPending}>
                Start
              </button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}
