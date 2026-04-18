import type { LookupRecord } from "../lib/api";

export type SortKey = "name" | "domain" | "email" | "confidence" | "reason" | "date";
export type SortDirection = "asc" | "desc";

interface HistoryTableProps {
  items: LookupRecord[];
  isLoading: boolean;
  sortKey: SortKey;
  sortDirection: SortDirection;
  onSortChange: (key: SortKey) => void;
}

const columns: Array<{ key: SortKey; label: string }> = [
  { key: "name", label: "Name" },
  { key: "domain", label: "Domain" },
  { key: "email", label: "Email" },
  { key: "confidence", label: "Confidence" },
  { key: "reason", label: "Reason" },
  { key: "date", label: "Date" },
];

export default function HistoryTable({
  items,
  isLoading,
  sortKey,
  sortDirection,
  onSortChange,
}: HistoryTableProps) {
  return (
    <div className="table-scroll overflow-x-auto">
      <table className="min-w-full border-separate border-spacing-0">
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                className="border-b border-stone-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.18em] text-stone-500"
              >
                <button
                  type="button"
                  onClick={() => onSortChange(column.key)}
                  className="inline-flex items-center gap-2 rounded-full px-2 py-1 transition hover:bg-stone-100"
                >
                  {column.label}
                  <span className="text-stone-400">
                    {sortKey === column.key ? (sortDirection === "asc" ? "↑" : "↓") : "·"}
                  </span>
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {isLoading ? (
            Array.from({ length: 6 }).map((_, index) => (
              <tr key={index}>
                <td colSpan={6} className="border-b border-stone-100 px-4 py-4">
                  <div className="stat-shimmer h-12 animate-shimmer rounded-2xl" />
                </td>
              </tr>
            ))
          ) : items.length === 0 ? (
            <tr>
              <td
                colSpan={6}
                className="border-b border-stone-100 px-4 py-12 text-center text-sm text-stone-500"
              >
                No lookups match the current filters.
              </td>
            </tr>
          ) : (
            items.map((item) => (
              <tr key={item.id} className="transition hover:bg-white/70">
                <td className="border-b border-stone-100 px-4 py-4 align-top">
                  <div className="font-semibold text-stone-900">
                    {item.first_name} {item.last_name}
                  </div>
                  <div className="mt-1 text-xs uppercase tracking-[0.18em] text-stone-400">
                    {item.status}
                  </div>
                </td>
                <td className="border-b border-stone-100 px-4 py-4 align-top text-sm text-stone-700">
                  {item.domain}
                </td>
                <td className="border-b border-stone-100 px-4 py-4 align-top text-sm text-stone-700">
                  {item.email ?? "—"}
                </td>
                <td className="border-b border-stone-100 px-4 py-4 align-top text-sm text-stone-700">
                  {Math.round(item.confidence * 100)}%
                </td>
                <td className="border-b border-stone-100 px-4 py-4 align-top text-sm capitalize text-stone-700">
                  {item.reason_code.replaceAll("_", " ")}
                </td>
                <td className="border-b border-stone-100 px-4 py-4 align-top text-sm text-stone-700">
                  {new Intl.DateTimeFormat("en-US", {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                  }).format(new Date(item.created_at))}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
