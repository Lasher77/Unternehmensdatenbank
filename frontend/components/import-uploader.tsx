'use client';

import { useCallback, useRef } from 'react';
import { readFileHeadAsText, isLikelyNdjson } from '@/lib/utils';
import { toast } from './toast';

export default function ImportUploader({ onFiles }: { onFiles: (files: File[]) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(async (files: FileList | null) => {
    if (!files) return;
    const valid: File[] = [];
    for (const file of Array.from(files)) {
      if (!file.name.endsWith('.jsonl')) {
        toast.error(`${file.name} hat keine .jsonl Endung`);
        continue;
      }
      try {
        const sample = await readFileHeadAsText(file, 64 * 1024);
        if (!isLikelyNdjson(sample)) {
          toast.error(`${file.name} scheint kein NDJSON zu sein`);
          continue;
        }
      } catch {
        toast.error(`${file.name} konnte nicht gelesen werden`);
        continue;
      }
      valid.push(file);
    }
    if (valid.length) onFiles(valid);
  }, [onFiles]);

  return (
    <div
      className="border-2 border-dashed rounded p-6 text-center cursor-pointer"
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        handleFiles(e.dataTransfer.files);
      }}
      onClick={() => inputRef.current?.click()}
    >
      <p>Drag & Drop JSONL-Dateien oder klicken zum Auswählen</p>
      <input
        ref={inputRef}
        type="file"
        accept=".jsonl"
        multiple
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
    </div>
  );
}
