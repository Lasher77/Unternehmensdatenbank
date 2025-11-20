'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Search } from 'lucide-react';
import { Input } from './ui/input';

interface SearchBarProps {
  size?: 'md' | 'lg';
}

export default function SearchBar({ size = 'lg' }: SearchBarProps) {
  const router = useRouter();
  const params = useSearchParams();
  const [value, setValue] = useState(params.get('query') ?? '');

  useEffect(() => {
    setValue(params.get('query') ?? '');
  }, [params]);

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

  const inputClasses = size === 'lg' ? 'h-12 text-base' : 'h-10 text-sm';

  return (
    <div className="relative w-full max-w-2xl">
      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        aria-label="Search companies"
        className={`${inputClasses} pl-10 shadow-sm`}
        placeholder="Name, Domain, HRB oder Ort…"
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />
    </div>
  );
}
