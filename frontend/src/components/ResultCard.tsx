import { Badge, Card, ProgressBar, Text, Title } from "@tremor/react";

import type { LookupRecord } from "../lib/api";

interface ResultCardProps {
  lookup: LookupRecord | null | undefined;
  isLoading: boolean;
  requestLabel?: string;
}

const reasonTone: Record<string, "orange" | "emerald" | "rose" | "sky" | "stone"> = {
  valid: "emerald",
  exa_found: "sky",
  scraped: "orange",
  pattern_derived: "stone",
  catch_all: "orange",
  invalid: "rose",
  not_found: "rose",
};

export default function ResultCard({ lookup, isLoading, requestLabel }: ResultCardProps) {
  const confidencePercent = lookup ? Math.round(lookup.confidence * 100) : 0;
  const tone = reasonTone[lookup?.reason_code ?? "pattern_derived"] ?? "stone";

  return (
    <Card className="glass-panel rounded-[28px] border border-stone-200/80 p-0 shadow-tremor-card">
      <div className="rounded-[28px] bg-gradient-to-br from-stone-950 via-stone-900 to-ember-900 px-6 py-6 text-stone-50 sm:px-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-amber-200">
              Lookup Output
            </p>
            <Title className="mt-3 !font-display !text-3xl !text-white">
              {lookup?.email ?? (isLoading ? "Searching..." : "Awaiting a lookup")}
            </Title>
          </div>
          <Badge color={tone} className="!rounded-full !px-4 !py-2 !text-xs !font-semibold !uppercase">
            {formatReason(lookup?.reason_code)}
          </Badge>
        </div>

        <p className="mt-4 text-sm leading-6 text-stone-200">
          {requestLabel
            ? `Tracking ${requestLabel}. The client polls every 1.5 seconds until the backend settles the job.`
            : "Submit a name and domain to watch the lookup resolve in place."}
        </p>
      </div>

      <div className="grid gap-6 p-6 sm:grid-cols-3 sm:p-8">
        <MetricBlock
          label="Confidence"
          value={lookup ? `${confidencePercent}%` : isLoading ? "..." : "0%"}
          accent="The backend boosts verified candidates into the 90-100% band."
        />
        <MetricBlock
          label="Verifier calls"
          value={lookup ? String(lookup.verifier_calls_used) : isLoading ? "..." : "0"}
          accent="The backend never exceeds three sequential verifier calls."
        />
        <MetricBlock
          label="Status"
          value={lookup?.status ?? (isLoading ? "processing" : "idle")}
          accent="Pending and processing states stay live while polling is active."
        />
      </div>

      <div className="border-t border-stone-200/80 px-6 py-6 sm:px-8">
        <div className="flex items-center justify-between gap-4">
          <Text>Confidence ladder</Text>
          <Text>{confidencePercent}%</Text>
        </div>
        <ProgressBar
          value={confidencePercent}
          showAnimation
          color={tone === "rose" ? "red" : tone === "emerald" ? "emerald" : "amber"}
          className="mt-4"
        />
      </div>
    </Card>
  );
}

interface MetricBlockProps {
  label: string;
  value: string;
  accent: string;
}

function MetricBlock({ label, value, accent }: MetricBlockProps) {
  return (
    <div className="rounded-3xl border border-stone-200/80 bg-white/80 p-5">
      <Text>{label}</Text>
      <p className="mt-3 text-2xl font-semibold tracking-tight text-stone-900">{value}</p>
      <p className="mt-3 text-sm leading-6 text-stone-500">{accent}</p>
    </div>
  );
}

function formatReason(reasonCode: string | undefined) {
  if (!reasonCode) {
    return "No result";
  }

  return reasonCode.replaceAll("_", " ");
}
