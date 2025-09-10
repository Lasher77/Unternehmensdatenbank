'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

export default function SearchBar() {
  const router = useRouter();
  const params = useSearchParams();
  const [value, setValue] = useState(params.get('query') ?? '');

  useEffect(() => {
    const t = setTimeout(() => {
      const url = new URL(window.location.href);
      if (value) url.searchParams.set('query', value);
      else url.searchParams.delete('query');
      url.searchParams.set('page', '1');
      router.push(url.pathname + '?' + url.searchParams.toString());
    }, 300);
    return () => clearTimeout(t);
  }, [value, router]);

  return (
    <input
      aria-label="Search companies"
      className="w-full max-w-lg px-3 py-2 border rounded-md"
      placeholder="Search companies..."
      value={value}
      onChange={(e) => setValue(e.target.value)}
    />
  );
}
