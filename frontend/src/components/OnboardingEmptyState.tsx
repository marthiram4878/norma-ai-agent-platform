import { FormEvent, useState } from "react";
import { FolderKanban, LoaderCircle, Menu, Plus } from "lucide-react";

interface OnboardingEmptyStateProps {
  hasProject: boolean;
  onCreateProject: (name: string) => Promise<void>;
  onCreateSpace: (name: string) => Promise<void>;
  onOpenNav?: () => void;
}

export function OnboardingEmptyState({
  hasProject,
  onCreateProject,
  onCreateSpace,
  onOpenNav,
}: OnboardingEmptyStateProps) {
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const value = name.trim();
    if (!value || busy) return;
    setBusy(true);
    try {
      if (!hasProject) {
        await onCreateProject(value);
      } else {
        await onCreateSpace(value);
      }
      setName("");
    } finally {
      setBusy(false);
    }
  }

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
        <div>
          <h1 className="text-sm font-semibold text-slate-100">Get started</h1>
          <p className="mt-0.5 text-[10px] text-slate-600">
            Create a project and knowledge space
          </p>
        </div>
      </header>

      <div className="grid flex-1 place-items-center px-4 py-12">
        <div className="w-full max-w-md text-center">
          <div className="mx-auto grid size-14 place-items-center rounded-2xl border border-cyan-400/15 bg-cyan-400/8 text-cyan-300">
            <FolderKanban className="size-6" />
          </div>
          <h2 className="mt-6 text-xl font-semibold text-slate-100">
            {!hasProject ? "Create your first project" : "Create a knowledge space"}
          </h2>
          <p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-slate-500">
            {!hasProject
              ? "Projects group spaces. Each space has its own documents, chats, and workflow runs."
              : "Spaces isolate knowledge. Assistant and workflows use the active space."}
          </p>
          <form
            className="mt-8 flex gap-2 text-left"
            onSubmit={(event) => void submit(event)}
          >
            <input
              className="min-w-0 flex-1 rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2.5 text-sm text-slate-200 outline-none placeholder:text-slate-600 focus:border-cyan-400/40"
              placeholder={!hasProject ? "Project name" : "Space name"}
              value={name}
              onChange={(event) => setName(event.target.value)}
              autoFocus
            />
            <button
              type="submit"
              disabled={!name.trim() || busy}
              className="inline-flex items-center gap-1.5 rounded-xl bg-cyan-400 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-500"
            >
              {busy ? (
                <LoaderCircle className="size-4 animate-spin" />
              ) : (
                <Plus className="size-4" />
              )}
              Create
            </button>
          </form>
        </div>
      </div>
    </main>
  );
}
