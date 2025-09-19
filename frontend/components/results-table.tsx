'use client';

export interface Company {
  source_id: string;
  name: string;
  status?: string | null;
  [key: string]: any;
}

export default function ResultsTable({
  data,
  selected,
  onSelectedChange
}: {
  data: Company[];
  selected: string[];
  onSelectedChange: (ids: string[]) => void;
}) {
  const allSelected = selected.length === data.length && data.length > 0;

  function toggle(id: string, checked: boolean) {
    const next = checked ? [...selected, id] : selected.filter((s) => s !== id);
    onSelectedChange(next);
  }

  function toggleAll(checked: boolean) {
    if (checked) onSelectedChange(data.map((d) => d.source_id));
    else onSelectedChange([]);
  }

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left border-b">
          <th className="p-2">
            <input
              type="checkbox"
              aria-label="Select all"
              checked={allSelected}
              onChange={(e) => toggleAll(e.target.checked)}
            />
          </th>
          <th className="p-2">Company</th>
        </tr>
      </thead>
      <tbody>
        {data.map((item) => (
          <tr key={item.source_id} className="border-b">
            <td className="p-2">
              <input
                type="checkbox"
                checked={selected.includes(item.source_id)}
                onChange={(e) => toggle(item.source_id, e.target.checked)}
              />
            </td>
            <td className="p-2">
              <div className="flex items-center gap-2">
                <a href={`/company/${item.source_id}`} className="text-primary hover:underline">
                  {item.name}
                </a>
                {item.status && (
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                      item.status.toLowerCase() === 'active'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-gray-200 text-gray-800'
                    }`}
                  >
                    {item.status.toLowerCase() === 'active' ? 'Active' : 'Inactive'}
                  </span>
                )}
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
