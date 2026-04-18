import type { FormEvent } from "react";

interface LookupFormValues {
  firstName: string;
  lastName: string;
  domain: string;
}

interface LookupFormProps {
  values: LookupFormValues;
  isSubmitting: boolean;
  onChange: (field: keyof LookupFormValues, value: string) => void;
  onSubmit: () => void;
}

export default function LookupForm({
  values,
  isSubmitting,
  onChange,
  onSubmit,
}: LookupFormProps) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="glass-panel grain-accent rounded-[28px] border border-ember-200/80 p-6 shadow-tremor-card sm:p-8"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-ember-700">
            Live Lookup
          </p>
          <h2 className="section-title mt-3 text-3xl text-stone-900">
            Search by person, not by guesswork.
          </h2>
          <p className="mt-3 max-w-xl text-sm leading-6 text-stone-600">
            Phase 5 is wired to the backend lookup queue and will keep polling until the
            job finishes. The backend still respects the three-verifier hard cap.
          </p>
        </div>
        <div className="rounded-full border border-ember-200 bg-white/80 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-ember-700">
          Single-user lane
        </div>
      </div>

      <div className="mt-8 grid gap-5 md:grid-cols-3">
        <Field
          label="First name"
          placeholder="Jane"
          value={values.firstName}
          onChange={(value) => onChange("firstName", value)}
        />
        <Field
          label="Last name"
          placeholder="Doe"
          value={values.lastName}
          onChange={(value) => onChange("lastName", value)}
        />
        <Field
          label="Company domain"
          placeholder="example.com"
          value={values.domain}
          onChange={(value) => onChange("domain", value)}
        />
      </div>

      <div className="mt-8 flex flex-col gap-4 border-t border-ember-100 pt-6 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-stone-500">
          Tip: plain domains like <span className="font-semibold text-stone-700">acme.com</span>{" "}
          work best.
        </p>
        <button
          type="submit"
          disabled={isSubmitting}
          className="inline-flex items-center justify-center rounded-full bg-stone-950 px-6 py-3 text-sm font-semibold text-stone-50 transition hover:bg-ember-700 disabled:cursor-not-allowed disabled:bg-stone-400"
        >
          {isSubmitting ? "Queueing lookup..." : "Start lookup"}
        </button>
      </div>
    </form>
  );
}

interface FieldProps {
  label: string;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
}

function Field({ label, placeholder, value, onChange }: FieldProps) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.2em] text-stone-500">
        {label}
      </span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="block w-full rounded-2xl border border-ember-200 bg-white/90 px-4 py-3 text-base text-stone-900 shadow-sm shadow-ember-100 transition placeholder:text-stone-400 focus:border-ember-500 focus:ring-2 focus:ring-ember-200"
      />
    </label>
  );
}
