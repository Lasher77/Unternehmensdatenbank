'use client';

export interface Company {
  source_id: string;
  name: string;
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
          <th className="p-2">Name</th>
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
              <a href={`/company/${item.source_id}`} className="text-primary hover:underline">
                {item.name}
              </a>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
