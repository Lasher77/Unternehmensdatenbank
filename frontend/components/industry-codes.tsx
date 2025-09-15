'use client';

import { IndustryCode } from '@/lib/schemas';

export default function IndustryCodes({ codes }: { codes: IndustryCode[] }) {
  if (!codes || codes.length === 0) {
    return <div>No industry codes</div>;
  }
  return (
    <ul className="list-disc pl-5 space-y-1">
      {codes.map((c) => (
        <li key={`${c.scheme}-${c.code}`}>
          {c.scheme}: {c.code}
        </li>
      ))}
    </ul>
  );
}
