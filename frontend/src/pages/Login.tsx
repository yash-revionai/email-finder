import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { RiLockPasswordLine, RiShieldKeyholeLine } from "@remixicon/react";
import { useLocation, useNavigate } from "react-router-dom";

import { login } from "../lib/api";
import { setAccessToken } from "../lib/auth";

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const [password, setPassword] = useState("");
  const nextPath = resolveNextPath(new URLSearchParams(location.search).get("next"));

  const loginMutation = useMutation({
    mutationFn: (currentPassword: string) => login(currentPassword),
    onSuccess: (response) => {
      setAccessToken(response.access_token);
      navigate(nextPath, { replace: true });
    },
  });

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    loginMutation.mutate(password);
  }

  return (
    <section className="mx-auto max-w-5xl">
      <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="page-card rounded-[36px] bg-gradient-to-br from-stone-950 via-stone-900 to-ember-900 px-6 py-10 text-stone-50 shadow-[0_36px_90px_-36px_rgba(120,53,15,0.5)] sm:px-8">
          <div className="inline-flex items-center gap-3 rounded-full border border-white/10 bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-amber-100">
            <RiShieldKeyholeLine size={16} />
            JWT access gate
          </div>
          <h1 className="section-title mt-6 max-w-3xl text-5xl leading-[0.95] text-white sm:text-6xl">
            One operator. One password. One internal console.
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-stone-200">
            Phase 6 adds the single-user auth wall, container wiring, and reverse proxy setup for
            a simple VPS deployment without changing the operational flow of the tool itself.
          </p>
        </div>

        <div className="glass-panel page-card rounded-[32px] border border-stone-200/80 p-6 sm:p-8">
          <div className="flex h-14 w-14 items-center justify-center rounded-3xl bg-ember-100 text-ember-700">
            <RiLockPasswordLine size={24} />
          </div>
          <p className="mt-6 text-xs font-semibold uppercase tracking-[0.22em] text-ember-700">
            Sign in
          </p>
          <h2 className="section-title mt-3 text-4xl text-stone-900">Unlock the dashboard.</h2>
          <p className="mt-3 text-sm leading-6 text-stone-600">
            Enter the password from the server environment to receive a JWT and continue.
          </p>

          <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
            <label className="block">
              <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-stone-500">
                Password
              </span>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                placeholder="Enter the app password"
                className="block w-full rounded-2xl border border-stone-200 bg-white px-4 py-3 text-sm text-stone-900 focus:border-ember-500 focus:ring-2 focus:ring-ember-200"
              />
            </label>

            {loginMutation.error ? (
              <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                {loginMutation.error.message}
              </div>
            ) : null}

            <button
              type="submit"
              disabled={loginMutation.isPending || password.length === 0}
              className="inline-flex w-full items-center justify-center rounded-full bg-stone-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-ember-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loginMutation.isPending ? "Signing in..." : "Sign in"}
            </button>
          </form>
        </div>
      </div>
    </section>
  );
}

function resolveNextPath(value: string | null): string {
  if (!value || !value.startsWith("/") || value.startsWith("//")) {
    return "/";
  }

  return value;
}
