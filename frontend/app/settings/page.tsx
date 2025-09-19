"use client";

import { useTableCounts } from "@/lib/queries";

export default function SettingsPage() {
  const { data, isLoading, isError, error, refetch } = useTableCounts();

  return (
    <div className="space-y-6">
      <section className="space-y-4">
        <div>
          <h1 className="text-2xl font-semibold">Settings</h1>
          <p className="text-sm text-muted-foreground">
            Übersicht der verfügbaren Datenbanktabellen und ihrer Datensätze.
          </p>
        </div>
        {isLoading && <p>Loading table statistics...</p>}
        {isError && (
          <div className="space-y-2">
            <p className="text-red-600">
              {error instanceof Error ? error.message : "Failed to load table statistics."}
            </p>
            <button
              type="button"
              onClick={() => refetch()}
              className="px-3 py-1 rounded border hover:bg-muted"
            >
              Retry
            </button>
          </div>
        )}
        {!isLoading && !isError && (
          <div className="overflow-x-auto">
            <table className="min-w-full border border-border text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-3 py-2 text-left">Table</th>
                  <th className="px-3 py-2 text-right">Rows</th>
                </tr>
              </thead>
              <tbody>
                {data?.counts.map((item) => (
                  <tr key={item.table} className="border-t border-border">
                    <td className="px-3 py-2 font-medium">{item.table}</td>
                    <td className="px-3 py-2 text-right">
                      {item.rows.toLocaleString()}
                    </td>
                  </tr>
                ))}
                {data && data.counts.length === 0 && (
                  <tr>
                    <td colSpan={2} className="px-3 py-4 text-center text-muted-foreground">
                      No tables found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
