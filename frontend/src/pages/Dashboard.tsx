import { useEffect, startTransition, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Badge } from "@tremor/react";
import { RiRadarLine, RiSparkling2Line, RiTimerFlashLine } from "@remixicon/react";

import LookupForm from "../components/LookupForm";
import ResultCard from "../components/ResultCard";
import { createLookup, getLookup, type LookupCreatePayload } from "../lib/api";

export default function Dashboard() {
  const queryClient = useQueryClient();
  const [formValues, setFormValues] = useState({
    firstName: "",
    lastName: "",
    domain: "",
  });
  const [activeLookupId, setActiveLookupId] = useState<string | null>(null);
  const [requestLabel, setRequestLabel] = useState<string>("");

  const createLookupMutation = useMutation({
    mutationFn: (payload: LookupCreatePayload) => createLookup(payload),
    onSuccess: (response, variables) => {
      startTransition(() => {
        setActiveLookupId(response.id);
        setRequestLabel(`${variables.first_name} ${variables.last_name} @ ${variables.domain}`);
      });
      queryClient.invalidateQueries({ queryKey: ["history"] });
    },
  });

  const lookupQuery = useQuery({
    queryKey: ["lookup", activeLookupId],
    queryFn: () => getLookup(activeLookupId as string),
    enabled: Boolean(activeLookupId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "done" || status === "failed" ? false : 1500;
    },
  });

  useEffect(() => {
    if (lookupQuery.data?.status === "done") {
      queryClient.invalidateQueries({ queryKey: ["history"] });
      queryClient.invalidateQueries({ queryKey: ["analytics"] });
    }
  }, [lookupQuery.data?.status, queryClient]);

  function handleSubmit() {
    createLookupMutation.mutate({
      first_name: formValues.firstName.trim(),
      last_name: formValues.lastName.trim(),
      domain: formValues.domain.trim(),
    });
  }

  return (
    <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
      <div className="space-y-6">
        <div className="page-card rounded-[32px] bg-gradient-to-br from-stone-950 via-stone-900 to-ember-900 px-6 py-10 text-stone-50 shadow-[0_32px_80px_-32px_rgba(120,53,15,0.5)] sm:px-8">
          <div className="flex flex-wrap items-center gap-3">
            <Badge color="orange" className="!rounded-full !px-4 !py-2 !text-xs !font-semibold !uppercase">
              Phase 5 dashboard
            </Badge>
            <Badge color="stone" className="!rounded-full !px-4 !py-2 !text-xs !font-semibold !uppercase">
              React + Tremor
            </Badge>
          </div>
          <h1 className="section-title mt-6 max-w-3xl text-5xl leading-[0.95] text-white sm:text-6xl">
            A sharp internal console for high-signal email hunts.
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-stone-200">
            The frontend leans into the operational feel of the product: live queue feedback,
            reason-code visibility, and analytics surfaces that stay useful even before auth and
            infrastructure arrive in Phase 6.
          </p>
        </div>

        <LookupForm
          values={formValues}
          isSubmitting={createLookupMutation.isPending}
          onChange={(field, value) =>
            setFormValues((current) => ({
              ...current,
              [field]: value,
            }))
          }
          onSubmit={handleSubmit}
        />

        {createLookupMutation.error ? (
          <div className="rounded-3xl border border-rose-200 bg-rose-50 px-5 py-4 text-sm text-rose-700">
            {createLookupMutation.error.message}
          </div>
        ) : null}
      </div>

      <div className="space-y-6">
        <ResultCard
          lookup={lookupQuery.data}
          isLoading={lookupQuery.isFetching || createLookupMutation.isPending}
          requestLabel={requestLabel}
        />

        <div className="page-card glass-panel rounded-[28px] border border-stone-200/80 p-6 sm:p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-ember-700">
            Workflow notes
          </p>
          <div className="mt-6 space-y-4">
            <Insight
              icon={<RiRadarLine size={18} />}
              title="Polled result loop"
              body="The dashboard watches the active lookup until the backend marks it done or failed."
            />
            <Insight
              icon={<RiSparkling2Line size={18} />}
              title="Reason-first presentation"
              body="Exa hits, scraped results, pattern-derived results, and catch-all domains all stay visible."
            />
            <Insight
              icon={<RiTimerFlashLine size={18} />}
              title="Hard verifier ceiling"
              body="Verifier usage is surfaced directly so the three-call cap remains obvious to the operator."
            />
          </div>
        </div>
      </div>
    </section>
  );
}

interface InsightProps {
  icon: React.ReactNode;
  title: string;
  body: string;
}

function Insight({ icon, title, body }: InsightProps) {
  return (
    <div className="flex gap-4 rounded-3xl border border-stone-200/70 bg-white/80 p-4">
      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-ember-100 text-ember-700">
        {icon}
      </div>
      <div>
        <h3 className="text-base font-semibold text-stone-900">{title}</h3>
        <p className="mt-1 text-sm leading-6 text-stone-600">{body}</p>
      </div>
    </div>
  );
}
