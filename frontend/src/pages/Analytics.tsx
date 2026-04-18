import { useQuery } from "@tanstack/react-query";
import { AreaChart, BarChart, Card, Metric, Text, Title } from "@tremor/react";

import {
  getAnalyticsCredits,
  getAnalyticsDomains,
  getAnalyticsSummary,
  getAnalyticsVolume,
} from "../lib/api";

const wholeNumber = new Intl.NumberFormat("en-US");
const percentFormatter = (value: number) => `${value.toFixed(1)}%`;

export default function Analytics() {
  const summaryQuery = useQuery({
    queryKey: ["analytics", "summary"],
    queryFn: getAnalyticsSummary,
  });
  const volumeQuery = useQuery({
    queryKey: ["analytics", "volume"],
    queryFn: getAnalyticsVolume,
  });
  const domainsQuery = useQuery({
    queryKey: ["analytics", "domains"],
    queryFn: getAnalyticsDomains,
  });
  const creditsQuery = useQuery({
    queryKey: ["analytics", "credits"],
    queryFn: getAnalyticsCredits,
  });

  const summary = summaryQuery.data;
  const volumeData = (volumeQuery.data ?? []).map((point) => ({
    week: formatWeek(point.week_start),
    Lookups: point.lookups,
  }));
  const domainsData = (domainsQuery.data ?? []).map((point) => ({
    domain: point.domain,
    "Hit rate": Number((point.hit_rate * 100).toFixed(1)),
  }));
  const creditsData = (creditsQuery.data ?? []).map((point) => ({
    week: formatWeek(point.week_start),
    Credits: point.credits_used,
  }));

  return (
    <section className="space-y-6">
      <div className="page-card glass-panel rounded-[32px] border border-stone-200/80 p-6 sm:p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-ember-700">
          Analytics
        </p>
        <h1 className="section-title mt-3 text-4xl text-stone-900">
          A dashboard skin for lookup volume, hit rate, and verifier spend.
        </h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-stone-600">
          These charts map directly to the Phase 4 analytics endpoints and keep the visual system
          closer to an internal trading desk than a generic admin page.
        </p>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        <StatCard
          label="Total lookups"
          value={summary ? wholeNumber.format(summary.total_lookups) : "—"}
          detail="All lookup records tracked by the backend."
          accent="from-amber-100 via-white to-white"
        />
        <StatCard
          label="Overall hit rate"
          value={summary ? percentFormatter(summary.overall_hit_rate * 100) : "—"}
          detail="Valid, scraped, Exa-found, pattern-derived, and catch-all outcomes."
          accent="from-orange-100 via-white to-white"
        />
        <StatCard
          label="Credits this month"
          value={summary ? wholeNumber.format(summary.credits_used_this_month) : "—"}
          detail="Verifier credits consumed during the current month."
          accent="from-rose-100 via-white to-white"
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card className="glass-panel rounded-[28px] border border-stone-200/80 p-6 shadow-tremor-card">
          <Title className="!font-display !text-2xl !text-stone-900">Weekly lookup volume</Title>
          <Text className="mt-2">Last 12 weeks of lookup activity.</Text>
          <BarChart
            className="mt-6 h-80"
            data={volumeData}
            index="week"
            categories={["Lookups"]}
            colors={["amber"]}
            showLegend={false}
            yAxisWidth={42}
            valueFormatter={(value) => wholeNumber.format(value)}
            noDataText="No lookup volume yet"
          />
        </Card>

        <Card className="glass-panel rounded-[28px] border border-stone-200/80 p-6 shadow-tremor-card">
          <Title className="!font-display !text-2xl !text-stone-900">Top domains by hit rate</Title>
          <Text className="mt-2">Best-performing domains from the current lookup history.</Text>
          <BarChart
            className="mt-6 h-80"
            data={domainsData}
            index="domain"
            categories={["Hit rate"]}
            colors={["rose"]}
            layout="vertical"
            showLegend={false}
            yAxisWidth={108}
            valueFormatter={(value) => `${value.toFixed(1)}%`}
            noDataText="No domains yet"
          />
        </Card>
      </div>

      <Card className="page-card glass-panel rounded-[28px] border border-stone-200/80 p-6 shadow-tremor-card">
        <Title className="!font-display !text-2xl !text-stone-900">Verifier credits over time</Title>
        <Text className="mt-2">Credits consumed per week across the last twelve weeks.</Text>
        <AreaChart
          className="mt-6 h-80"
          data={creditsData}
          index="week"
          categories={["Credits"]}
          colors={["orange"]}
          showLegend={false}
          valueFormatter={(value) => wholeNumber.format(value)}
          noDataText="No verifier credits yet"
        />
      </Card>
    </section>
  );
}

interface StatCardProps {
  label: string;
  value: string;
  detail: string;
  accent: string;
}

function StatCard({ label, value, detail, accent }: StatCardProps) {
  return (
    <Card className={`page-card glass-panel rounded-[28px] border border-stone-200/80 bg-gradient-to-br ${accent} p-6 shadow-tremor-card`}>
      <Text>{label}</Text>
      <Metric className="mt-3 !font-display !text-4xl !tracking-tight !text-stone-900">{value}</Metric>
      <p className="mt-4 text-sm leading-6 text-stone-600">{detail}</p>
    </Card>
  );
}

function formatWeek(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
  }).format(new Date(value));
}
