import {
  Bot,
  Boxes,
  FileText,
  FolderKanban,
  LayoutDashboard,
  LogOut,
  Settings,
  Sparkles,
} from "lucide-react";

import type { AuthUser, AuthWorkspace, Project } from "../lib/api";

export type AppView = "assistant" | "workflows" | "knowledge";

const navigation: {
  id: AppView;
  label: string;
  icon: typeof Bot;
}[] = [
  { id: "assistant", label: "Assistant", icon: Bot },
  { id: "workflows", label: "Workflows", icon: Boxes },
  { id: "knowledge", label: "Knowledge", icon: FileText },
];

interface SidebarProps {
  user: AuthUser;
  workspace: AuthWorkspace;
  projects: Project[];
  projectId: string | null;
  spaceId: string | null;
  activeView: AppView;
  onNavigate: (view: AppView) => void;
  onSelectProject: (projectId: string) => void;
  onSelectSpace: (spaceId: string) => void;
  onLogout: () => void;
}

export function Sidebar({
  user,
  workspace,
  projects,
  projectId,
  spaceId,
  activeView,
  onNavigate,
  onSelectProject,
  onSelectSpace,
  onLogout,
}: SidebarProps) {
  const activeProject =
    projects.find((item) => item.id === projectId) ?? projects[0] ?? null;

  return (
    <aside className="hidden h-screen w-64 shrink-0 flex-col border-r border-white/7 bg-[#090d16] px-3 py-4 lg:flex">
      <div className="flex items-center gap-3 px-3 py-2">
        <div className="grid size-9 place-items-center rounded-xl bg-gradient-to-br from-cyan-400 to-blue-600 shadow-lg shadow-cyan-950">
          <Sparkles className="size-4 text-white" />
        </div>
        <div>
          <p className="text-[15px] font-semibold tracking-tight text-white">
            Norma AI
          </p>
          <p className="text-[11px] text-slate-500">Knowledge OS</p>
        </div>
      </div>

      <div className="mt-5 flex items-center gap-3 rounded-xl border border-white/8 bg-white/[0.035] px-3 py-2.5 text-left">
        <div className="grid size-8 place-items-center rounded-lg bg-indigo-500/15 text-indigo-300">
          <LayoutDashboard className="size-4" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs font-medium text-slate-200">
            {workspace.name}
          </p>
          <p className="truncate text-[10px] text-slate-500">{user.email}</p>
        </div>
      </div>

      <div className="mt-4 space-y-2 px-1">
        <div className="flex items-center gap-2 px-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-600">
          <FolderKanban className="size-3" />
          Project / Space
        </div>
        <label className="block px-1">
          <span className="sr-only">Project</span>
          <select
            className="w-full rounded-lg border border-white/8 bg-[#0f1522] px-2.5 py-2 text-xs text-slate-200 outline-none focus:border-cyan-400/40"
            value={activeProject?.id ?? ""}
            onChange={(event) => onSelectProject(event.target.value)}
            disabled={projects.length === 0}
          >
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
        </label>
        <label className="block px-1">
          <span className="sr-only">Knowledge space</span>
          <select
            className="w-full rounded-lg border border-white/8 bg-[#0f1522] px-2.5 py-2 text-xs text-slate-200 outline-none focus:border-cyan-400/40"
            value={spaceId ?? ""}
            onChange={(event) => onSelectSpace(event.target.value)}
            disabled={!activeProject?.spaces.length}
          >
            {(activeProject?.spaces ?? []).map((space) => (
              <option key={space.id} value={space.id}>
                {space.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      <nav className="mt-6 space-y-1">
        <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-600">
          Workspace
        </p>
        {navigation.map(({ id, label, icon: Icon }) => {
          const active = activeView === id;
          return (
            <button
              className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition ${
                active
                  ? "bg-cyan-400/8 text-cyan-200"
                  : "text-slate-500 hover:bg-white/[0.04] hover:text-slate-300"
              }`}
              key={id}
              type="button"
              onClick={() => onNavigate(id)}
            >
              <Icon className="size-4" />
              <span>{label}</span>
            </button>
          );
        })}
      </nav>

      <div className="mt-auto">
        <div className="mx-2 mb-3 rounded-xl border border-cyan-400/10 bg-cyan-400/[0.035] p-3">
          <div className="flex items-center gap-2 text-xs font-medium text-cyan-200">
            <span className="size-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]" />
            Signed in as {user.display_name}
          </div>
          <p className="mt-1.5 text-[10px] leading-4 text-slate-600">
            Knowledge is isolated per project space.
          </p>
        </div>
        <button
          type="button"
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-500 transition hover:bg-white/[0.04] hover:text-slate-300"
        >
          <Settings className="size-4" />
          Settings
        </button>
        <button
          type="button"
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-500 transition hover:bg-white/[0.04] hover:text-red-300"
          onClick={onLogout}
        >
          <LogOut className="size-4" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
