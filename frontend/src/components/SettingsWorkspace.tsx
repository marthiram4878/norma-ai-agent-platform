import { LogOut, Menu, Settings, Shield } from "lucide-react";

import type { AuthUser, AuthWorkspace } from "../lib/api";

interface SettingsWorkspaceProps {
  user: AuthUser;
  workspace: AuthWorkspace;
  onLogout: () => void;
  onOpenNav?: () => void;
}

export function SettingsWorkspace({
  user,
  workspace,
  onLogout,
  onOpenNav,
}: SettingsWorkspaceProps) {
  return (
    <main className="flex min-w-0 flex-1 flex-col bg-[#0b101a]">
      <header className="flex h-[68px] shrink-0 items-center border-b border-white/7 px-4 sm:px-6">
        {onOpenNav && (
          <button
            type="button"
            className="mr-3 text-slate-500 transition hover:text-slate-300 lg:hidden"
            onClick={onOpenNav}
            aria-label="Open navigation"
          >
            <Menu className="size-5" />
          </button>
        )}
        <div className="flex items-center gap-3">
          <div className="grid size-9 place-items-center rounded-xl border border-white/10 bg-white/[0.04] text-slate-300">
            <Settings className="size-4" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-slate-100">Settings</h1>
            <p className="mt-0.5 text-[10px] text-slate-600">
              Profile and workspace
            </p>
          </div>
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-8 sm:px-8">
        <div className="mx-auto max-w-lg space-y-6">
          <section className="rounded-2xl border border-white/7 bg-white/[0.02] p-5">
            <h2 className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-600">
              Profile
            </h2>
            <dl className="mt-4 space-y-3 text-sm">
              <div>
                <dt className="text-[10px] uppercase tracking-wide text-slate-600">
                  Display name
                </dt>
                <dd className="mt-1 text-slate-200">{user.display_name}</dd>
              </div>
              <div>
                <dt className="text-[10px] uppercase tracking-wide text-slate-600">
                  Email
                </dt>
                <dd className="mt-1 text-slate-200">{user.email}</dd>
              </div>
            </dl>
          </section>

          <section className="rounded-2xl border border-white/7 bg-white/[0.02] p-5">
            <h2 className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-600">
              Workspace
            </h2>
            <dl className="mt-4 space-y-3 text-sm">
              <div>
                <dt className="text-[10px] uppercase tracking-wide text-slate-600">
                  Name
                </dt>
                <dd className="mt-1 text-slate-200">{workspace.name}</dd>
              </div>
              <div>
                <dt className="text-[10px] uppercase tracking-wide text-slate-600">
                  Role
                </dt>
                <dd className="mt-1 capitalize text-slate-200">
                  {workspace.role}
                </dd>
              </div>
            </dl>
            <p className="mt-4 flex items-start gap-2 text-[11px] leading-4 text-slate-600">
              <Shield className="mt-0.5 size-3.5 shrink-0 text-emerald-400/80" />
              Knowledge and conversations stay isolated per project space.
            </p>
          </section>

          <button
            type="button"
            className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-red-400/20 bg-red-400/5 px-4 py-3 text-sm font-medium text-red-200 transition hover:bg-red-400/10"
            onClick={onLogout}
          >
            <LogOut className="size-4" />
            Sign out
          </button>
        </div>
      </div>
    </main>
  );
}
