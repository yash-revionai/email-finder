import { startTransition, useDeferredValue, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Badge } from "@tremor/react";

import HistoryTable, { type SortDirection, type SortKey } from "../components/HistoryTable";
import { getHistory, type LookupRecord } from "../lib/api";

const PAGE_SIZE = 25;

export default function History() {
  const [page, setPage] = useState(1);
  const [domainFilter, setDomainFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("date");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const deferredDomainFilter = useDeferredValue(domainFilter);

  const historyQuery = useQuery({
    queryKey: ["history", page, PAGE_SIZE, deferredDomainFilter, statusFilter],
    queryFn: () =>
      getHistory({
        page,
        limit: PAGE_SIZE,
        domain: deferredDomainFilter,
        status: statusFilter,
      }),
  });

  const sortedItems = sortItems(historyQuery.data?.items ?? [], sortKey, sortDirection);

  function handleSortChange(key: SortKey) {
    if (sortKey === key) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }

    setSortKey(key);
    setSortDirection(key === "date" ? "desc" : "asc");
  }

  function exportCsv() {
    const rows = [
      ["Name", "Domain", "Email", "Confidence", "Reason", "Status", "Created At"],
      ...sortedItems.map((item) => [
        `${item.first_name} ${item.last_name}`,
        item.domain,
        item.email ?? "",
        `${Math.round(item.confidence * 100)}%`,
        item.reason_code,
        item.status,
        item.created_at,
      ]),
    ];

    const csv = rows
      .map((row) => row.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(","))
      .join("\n");

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `email-finder-history-page-${page}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="space-y-6">
      <div className="page-card glass-panel rounded-[32px] border border-stone-200/80 p-6 sm:p-8">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-ember-700">
              History
            </p>
            <h1 className="section-title mt-3 text-4xl text-stone-900">Filter, sort, and export the lookup trail.</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-stone-600">
              This page reads directly from the backend history endpoint and keeps the operator in
              control of pagination, sorting, and CSV export.
            </p>
          </div>
          <button
            type="button"
            onClick={exportCsv}
            className="inline-flex items-center justify-center rounded-full bg-stone-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-ember-700"
          >
            Export current page
          </button>
        </div>

        <div className="mt-8 grid gap-4 md:grid-cols-[1fr_240px_auto]">
          <label className="block">
            <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-stone-500">
              Filter by domain
            </span>
            <input
              value={domainFilter}
              onChange={(event) => {
                const value = event.target.value;
                setDomainFilter(value);
                startTransition(() => setPage(1));
              }}
              placeholder="example.com"
              className="block w-full rounded-2xl border border-stone-200 bg-white px-4 py-3 text-sm text-stone-900 focus:border-ember-500 focus:ring-2 focus:ring-ember-200"
            />
          </label>

          <label className="block">
            <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-stone-500">
              Filter by status
            </span>
            <select
              value={statusFilter}
              onChange={(event) => {
                setStatusFilter(event.target.value);
                startTransition(() => setPage(1));
              }}
              className="block w-full rounded-2xl border border-stone-200 bg-white px-4 py-3 text-sm text-stone-900 focus:border-ember-500 focus:ring-2 focus:ring-ember-200"
            >
              <option value="">All statuses</option>
              <option value="pending">Pending</option>
              <option value="processing">Processing</option>
              <option value="done">Done</option>
              <option value="failed">Failed</option>
            </select>
          </label>

          <div className="flex items-end">
            <Badge color="orange" className="!rounded-full !px-4 !py-2 !text-xs !font-semibold !uppercase">
              {historyQuery.data?.total ?? 0} total rows
            </Badge>
          </div>
        </div>
      </div>

      <div className="page-card glass-panel rounded-[32px] border border-stone-200/80 p-4 sm:p-6">
        <HistoryTable
          items={sortedItems}
          isLoading={historyQuery.isLoading}
          sortKey={sortKey}
          sortDirection={sortDirection}
          onSortChange={handleSortChange}
        />

        <div className="mt-6 flex flex-col gap-4 border-t border-stone-200 pt-5 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-stone-500">
            Page {page} of {Math.max(1, Math.ceil((historyQuery.data?.total ?? 0) / PAGE_SIZE))}
          </p>
          <div className="flex gap-3">
            <button
              type="button"
              disabled={page === 1}
              onClick={() => setPage((current) => Math.max(1, current - 1))}
              className="rounded-full border border-stone-300 px-4 py-2 text-sm font-semibold text-stone-700 transition hover:border-ember-500 hover:text-ember-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Previous
            </button>
            <button
              type="button"
              disabled={page >= Math.ceil((historyQuery.data?.total ?? 0) / PAGE_SIZE)}
              onClick={() => setPage((current) => current + 1)}
              className="rounded-full border border-stone-300 px-4 py-2 text-sm font-semibold text-stone-700 transition hover:border-ember-500 hover:text-ember-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

function sortItems(items: LookupRecord[], sortKey: SortKey, sortDirection: SortDirection) {
  const sorted = [...items].sort((left, right) => {
    const direction = sortDirection === "asc" ? 1 : -1;

    switch (sortKey) {
      case "name":
        return `${left.first_name} ${left.last_name}`.localeCompare(
          `${right.first_name} ${right.last_name}`,
        ) * direction;
      case "domain":
        return left.domain.localeCompare(right.domain) * direction;
      case "email":
        return (left.email ?? "").localeCompare(right.email ?? "") * direction;
      case "confidence":
        return (left.confidence - right.confidence) * direction;
      case "reason":
        return left.reason_code.localeCompare(right.reason_code) * direction;
      case "date":
      default:
        return (new Date(left.created_at).getTime() - new Date(right.created_at).getTime()) * direction;
    }
  });

  return sorted;
}
