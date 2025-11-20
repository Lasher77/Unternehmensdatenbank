'use client';

import { IndustryCode } from '@/lib/schemas';
import { Badge } from './ui/badge';

export default function IndustryCodes({ codes }: { codes: IndustryCode[] }) {
  if (!codes || codes.length === 0) {
    return <div className="text-sm text-muted-foreground">Keine Branchen hinterlegt.</div>;
  }
  return (
    <div className="flex flex-wrap gap-2">
      {codes.map((c) => (
        <Badge key={`${c.scheme}-${c.code}`} variant="outline" className="text-xs">
          {c.scheme}: {c.code}
        </Badge>
      ))}
    </div>
  );
}
