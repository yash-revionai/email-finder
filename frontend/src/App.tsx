import { useSyncExternalStore } from "react";
import {
  BrowserRouter,
  Navigate,
  NavLink,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";
import {
  RiBarChartBoxLine,
  RiBookShelfLine,
  RiLogoutBoxRLine,
  RiSearchEyeLine,
} from "@remixicon/react";

import Dashboard from "./pages/Dashboard";
import History from "./pages/History";
import Analytics from "./pages/Analytics";
import Login from "./pages/Login";
import { clearAccessToken, getAccessToken, subscribeToAuthChanges } from "./lib/auth";

const navigation = [
  { to: "/", label: "Dashboard", icon: RiSearchEyeLine },
  { to: "/history", label: "History", icon: RiBookShelfLine },
  { to: "/analytics", label: "Analytics", icon: RiBarChartBoxLine },
];

export default function App() {
  return (
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  );
}

function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const accessToken = useSyncExternalStore(subscribeToAuthChanges, getAccessToken, () => null);
  const isLoginRoute = location.pathname === "/login";

  return (
    <div className="app-shell">
      <div className="page-frame">
        {!isLoginRoute && accessToken ? (
          <div className="page-card glass-panel rounded-[36px] border border-ember-200/70 px-5 py-5 sm:px-8 sm:py-6">
            <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.26em] text-ember-700">
                  Email Finder
                </p>
                <h1 className="section-title mt-2 text-3xl text-stone-900">
                  Internal operator console
                </h1>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <nav className="flex flex-wrap gap-2 rounded-full border border-stone-200 bg-white/80 p-2">
                  {navigation.map(({ to, label, icon: Icon }) => (
                    <NavLink
                      key={to}
                      to={to}
                      end={to === "/"}
                      className={({ isActive }) =>
                        [
                          "inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition",
                          isActive
                            ? "bg-stone-950 text-white shadow-sm"
                            : "text-stone-600 hover:bg-ember-50 hover:text-ember-700",
                        ].join(" ")
                      }
                    >
                      <Icon size={18} />
                      {label}
                    </NavLink>
                  ))}
                </nav>

                <button
                  type="button"
                  onClick={() => {
                    clearAccessToken();
                    navigate("/login", { replace: true });
                  }}
                  className="inline-flex items-center gap-2 rounded-full border border-stone-200 bg-white/80 px-4 py-3 text-sm font-semibold text-stone-700 transition hover:border-ember-400 hover:text-ember-700"
                >
                  <RiLogoutBoxRLine size={18} />
                  Logout
                </button>
              </div>
            </div>
          </div>
        ) : null}

        <main className={!isLoginRoute && accessToken ? "mt-6" : ""}>
          <Routes>
            <Route
              path="/login"
              element={accessToken ? <Navigate to={readNextPath(location.search)} replace /> : <Login />}
            />
            <Route
              path="/"
              element={
                <RequireAuth accessToken={accessToken}>
                  <Dashboard />
                </RequireAuth>
              }
            />
            <Route
              path="/history"
              element={
                <RequireAuth accessToken={accessToken}>
                  <History />
                </RequireAuth>
              }
            />
            <Route
              path="/analytics"
              element={
                <RequireAuth accessToken={accessToken}>
                  <Analytics />
                </RequireAuth>
              }
            />
            <Route path="*" element={<Navigate to={accessToken ? "/" : "/login"} replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

function RequireAuth({
  accessToken,
  children,
}: {
  accessToken: string | null;
  children: React.ReactNode;
}) {
  const location = useLocation();

  if (!accessToken) {
    const search = new URLSearchParams();
    const nextPath = `${location.pathname}${location.search}`;
    if (nextPath && nextPath !== "/") {
      search.set("next", nextPath);
    }

    const loginPath = search.size > 0 ? `/login?${search.toString()}` : "/login";
    return <Navigate to={loginPath} replace />;
  }

  return <>{children}</>;
}

function readNextPath(search: string): string {
  const next = new URLSearchParams(search).get("next");
  if (!next || !next.startsWith("/") || next.startsWith("//")) {
    return "/";
  }

  return next;
}
