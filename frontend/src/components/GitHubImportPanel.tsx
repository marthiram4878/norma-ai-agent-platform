import { useCallback, useEffect, useState } from "react";
import { FolderGit2, LoaderCircle, Link2, Unlink } from "lucide-react";

import {
  disconnectGitHub,
  getGitHubAuthorizeUrl,
  getGitHubStatus,
  importGitHubRepos,
  listGitHubRepos,
  type GitHubRepo,
  type GitHubStatus,
} from "../lib/api";

interface GitHubImportPanelProps {
  workspaceId: string;
  spaceId: string;
  onImported: () => Promise<void>;
  onError: (message: string) => void;
}

export function GitHubImportPanel({
  workspaceId,
  spaceId,
  onImported,
  onError,
}: GitHubImportPanelProps) {
  const [status, setStatus] = useState<GitHubStatus | null>(null);
  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [importing, setImporting] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const next = await getGitHubStatus(workspaceId);
      setStatus(next);
      if (next.connected) {
        const listed = await listGitHubRepos(workspaceId);
        setRepos(listed);
      } else {
        setRepos([]);
        setSelected(new Set());
      }
    } catch (error) {
      onError(error instanceof Error ? error.message : "GitHub status failed");
    } finally {
      setLoading(false);
    }
  }, [workspaceId, onError]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const github = params.get("github");
    if (!github) return;
    params.delete("github");
    params.delete("detail");
    const next = params.toString();
    window.history.replaceState(
      {},
      "",
      `${window.location.pathname}${next ? `?${next}` : ""}`,
    );
    if (github === "connected") {
      void refresh();
    } else if (github === "error") {
      onError("GitHub connection failed. Try again.");
    }
  }, [refresh, onError]);

  async function handleConnect() {
    setConnecting(true);
    try {
      const { authorize_url } = await getGitHubAuthorizeUrl(
        workspaceId,
        spaceId,
      );
      window.location.href = authorize_url;
    } catch (error) {
      onError(
        error instanceof Error ? error.message : "Failed to start GitHub OAuth",
      );
      setConnecting(false);
    }
  }

  async function handleDisconnect() {
    try {
      await disconnectGitHub(workspaceId);
      await refresh();
    } catch (error) {
      onError(error instanceof Error ? error.message : "Disconnect failed");
    }
  }

  async function handleImport() {
    if (selected.size === 0) return;
    setImporting(true);
    try {
      await importGitHubRepos({
        workspaceId,
        spaceId,
        repoFullNames: [...selected],
      });
      setSelected(new Set());
      await onImported();
    } catch (error) {
      onError(error instanceof Error ? error.message : "Import failed");
    } finally {
      setImporting(false);
    }
  }

  function toggle(fullName: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(fullName)) next.delete(fullName);
      else next.add(fullName);
      return next;
    });
  }

  return (
    <section className="mt-6 rounded-2xl border border-white/7 bg-white/[0.02] p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-sm font-medium text-slate-200">
            <FolderGit2 className="size-3.5 text-slate-400" />
            GitHub
          </h2>
          <p className="mt-1 text-[11px] text-slate-600">
            Connect an account and import README / markdown into this space.
          </p>
        </div>
        {loading ? (
          <LoaderCircle className="size-4 animate-spin text-slate-600" />
        ) : status?.connected ? (
          <button
            type="button"
            className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 px-2.5 py-1.5 text-[11px] text-slate-400 transition hover:border-red-400/30 hover:text-red-300"
            onClick={() => void handleDisconnect()}
          >
            <Unlink className="size-3.5" />
            Disconnect
          </button>
        ) : (
          <button
            type="button"
            disabled={connecting}
            className="inline-flex items-center gap-1.5 rounded-lg bg-[#24292f] px-2.5 py-1.5 text-[11px] font-medium text-white transition hover:bg-[#32383f] disabled:opacity-50"
            onClick={() => void handleConnect()}
          >
            {connecting ? (
              <LoaderCircle className="size-3.5 animate-spin" />
            ) : (
              <Link2 className="size-3.5" />
            )}
            Connect GitHub
          </button>
        )}
      </div>

      {status?.connected && (
        <div className="mt-4">
          <p className="text-[11px] text-slate-500">
            Connected
            {status.login ? ` · @${status.login}` : ""}
          </p>
          {repos.length === 0 ? (
            <p className="mt-3 text-xs text-slate-600">
              No repositories found for this account.
            </p>
          ) : (
            <>
              <ul className="mt-3 max-h-48 space-y-1 overflow-y-auto">
                {repos.map((repo) => (
                  <li key={repo.id}>
                    <label className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-xs text-slate-300 hover:bg-white/[0.04]">
                      <input
                        type="checkbox"
                        checked={selected.has(repo.full_name)}
                        onChange={() => toggle(repo.full_name)}
                        className="accent-cyan-400"
                      />
                      <span className="min-w-0 flex-1 truncate">
                        {repo.full_name}
                      </span>
                      {repo.private && (
                        <span className="shrink-0 text-[9px] uppercase tracking-wide text-slate-600">
                          private
                        </span>
                      )}
                    </label>
                  </li>
                ))}
              </ul>
              <button
                type="button"
                disabled={selected.size === 0 || importing}
                className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-cyan-500/20 px-3 py-1.5 text-[11px] font-medium text-cyan-200 transition hover:bg-cyan-500/30 disabled:opacity-40"
                onClick={() => void handleImport()}
              >
                {importing ? (
                  <LoaderCircle className="size-3.5 animate-spin" />
                ) : null}
                Import {selected.size || ""}{" "}
                {selected.size === 1 ? "repo" : "repos"}
              </button>
            </>
          )}
        </div>
      )}
    </section>
  );
}
