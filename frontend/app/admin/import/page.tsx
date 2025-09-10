'use client';

import { useState } from 'react';
import ImportUploader from '@/components/import-uploader';
import ImportList, { ImportItem } from '@/components/import-list';

export default function ImportPage() {
  const [label, setLabel] = useState('');
  const [items, setItems] = useState<ImportItem[]>([]);

  function handleFiles(files: File[]) {
    const newItems = files.map((file) => ({
      id: Math.random().toString(36).slice(2),
      file,
      name: file.name,
      size: file.size,
      status: 'ready' as const,
      progress: 0
    }));
    setItems((prev) => [...prev, ...newItems]);
  }

  const allDone = items.length > 0 && items.every((i) => i.status === 'done');

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <h1 className="text-2xl font-bold">Import</h1>
      <div className="space-y-2">
        <label className="block text-sm font-medium">Label</label>
        <input
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          className="border px-2 py-1 rounded w-full"
          placeholder="z.B. Q3_2025"
        />
      </div>
      <ImportUploader onFiles={handleFiles} />
      <ImportList label={label} items={items} setItems={setItems} />
      {allDone && <div className="text-green-600">Alle Uploads abgeschlossen</div>}
    </div>
  );
}
