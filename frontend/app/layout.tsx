import '../styles/globals.css';
import type { Metadata } from 'next';
import SearchBar from '@/components/search-bar';
import { ToastProvider } from '@/components/toast';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Link from 'next/link';
import { useState } from 'react';

export const metadata: Metadata = {
  title: 'Unternehmensdatenbank',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());

  return (
    <html lang="en">
      <body className="min-h-screen flex">
        <QueryClientProvider client={queryClient}>
          <ToastProvider>
            <aside className="w-48 border-r p-4 space-y-2">
              <div className="font-bold">Menu</div>
              <nav className="flex flex-col gap-2">
                <Link href="/search" className="hover:underline">Search</Link>
                <Link href="/admin/import" className="hover:underline">Import</Link>
                <Link href="#" className="hover:underline">Settings</Link>
              </nav>
            </aside>
            <div className="flex-1 flex flex-col">
              <header className="p-4 border-b">
                <SearchBar />
              </header>
              <main className="p-4 flex-1 overflow-auto">{children}</main>
            </div>
          </ToastProvider>
        </QueryClientProvider>
      </body>
    </html>
  );
}
