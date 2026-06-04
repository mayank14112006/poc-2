"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

interface LogEntry {
  timestamp: string;
  user_id: string;
  decision: "ALLOWED" | "BLOCKED_PII" | "BLOCKED_INTENT" | "BLOCKED_RATE";
  request: string;
  blocked_reason?: string;
  response?: string;
}

export default function AdminPage() {
  const router = useRouter();
  const [user, setUser] = useState<{ id: string; email: string } | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    // Check if session exists
    const userJson = sessionStorage.getItem("user");
    if (!userJson) {
      setError("Access Denied. Redirecting to login portal...");
      setTimeout(() => {
        router.push("/");
      }, 3000);
      return;
    }
    setUser(JSON.parse(userJson));
    fetchLogs();
  }, [router]);

  const fetchLogs = async () => {
    setLoading(true);
    setError("");
    try {
      const token = sessionStorage.getItem("access_token");
      const response = await fetch("/api/logs", {
        headers: {
          "Authorization": `Bearer ${token || ""}`
        }
      });
      let data: any = null;
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        data = await response.json();
      }

      if (response.ok && data) {
        setLogs(data.logs);
      } else {
        const detailMsg = data?.detail || `Server error (${response.status}): ${response.statusText || "Failed to retrieve logs"}`;
        setError(detailMsg);
      }
    } catch (err: any) {
      console.error(err);
      setError(`Network error: ${err?.message || "Could not connect to database"}`);
    } finally {
      setLoading(false);
    }
  };

  if (error && !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 p-6 text-red-200">
        <div className="text-center p-8 bg-slate-900 border border-red-500/20 rounded-2xl max-w-md">
          <p className="text-lg font-bold">⚠️ Access Denied</p>
          <p className="text-slate-400 text-sm mt-2">{error}</p>
        </div>
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-8 font-sans">
      <div className="max-w-7xl mx-auto">
        
        {/* Header */}
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">
              🔍 Security & <span className="bg-gradient-to-r from-amber-500 to-amber-300 bg-clip-text text-transparent">Audit Log Dashboard</span>
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Review the latest 50 citizen interactions, safety decisions, and guardrail logs.
            </p>
          </div>
          <div className="flex gap-4">
            <button
              onClick={fetchLogs}
              disabled={loading}
              className="rounded-lg bg-slate-800 hover:bg-slate-700 active:scale-[0.99] transition-all px-5 py-2 text-sm font-semibold flex items-center gap-2"
            >
              {loading ? (
                <span className="w-4 h-4 rounded-full border-2 border-slate-400 border-t-transparent animate-spin"></span>
              ) : null}
              <span>Refresh Logs</span>
            </button>
            <button
              onClick={() => router.push("/chat")}
              className="rounded-lg bg-amber-500 hover:bg-amber-600 active:scale-[0.99] transition-all px-5 py-2 text-sm font-semibold text-slate-950"
            >
              Back to Chat
            </button>
          </div>
        </header>

        {error && (
          <div className="mb-6 rounded-lg border border-red-500/20 bg-red-950/60 p-4 text-sm text-red-200">
            {error}
          </div>
        )}

        {/* Logs Table */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-sm text-slate-300">
              <thead>
                <tr className="bg-slate-800/50 border-b border-slate-800 text-slate-200 font-semibold">
                  <th className="px-6 py-4">Timestamp</th>
                  <th className="px-6 py-4">User ID</th>
                  <th className="px-6 py-4">Decision</th>
                  <th className="px-6 py-4">Request Prompt</th>
                  <th className="px-6 py-4">Blocked Reason</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {logs.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-12 text-center text-slate-500">
                      {loading ? "Querying database..." : "No interactions logged yet."}
                    </td>
                  </tr>
                ) : (
                  logs.map((log, index) => {
                    // Format timestamp
                    const dateStr = new Date(log.timestamp).toLocaleString();
                    
                    // Match badge colors
                    let badgeClass = "bg-slate-800 text-slate-400";
                    if (log.decision === "ALLOWED") {
                      badgeClass = "bg-emerald-950/60 border border-emerald-500/30 text-emerald-200";
                    } else if (log.decision === "BLOCKED_PII") {
                      badgeClass = "bg-amber-950/60 border border-amber-500/30 text-amber-200";
                    } else if (log.decision === "BLOCKED_INTENT") {
                      badgeClass = "bg-red-950/60 border border-red-500/30 text-red-200";
                    }

                    return (
                      <tr key={index} className="hover:bg-slate-800/20 transition-colors">
                        <td className="px-6 py-4 whitespace-nowrap font-medium text-slate-400">
                          {dateStr}
                        </td>
                        <td className="px-6 py-4 font-mono text-xs text-slate-500 whitespace-nowrap">
                          {log.user_id ? log.user_id.slice(0, 18) + "..." : "System"}
                        </td>
                        <td className="px-6 py-4">
                          <span className={`inline-block px-2.5 py-1 rounded-md text-xs font-bold ${badgeClass}`}>
                            {log.decision}
                          </span>
                        </td>
                        <td className="px-6 py-4 max-w-xs truncate text-slate-400" title={log.request}>
                          {log.request}
                        </td>
                        <td className="px-6 py-4 text-xs text-slate-400 max-w-xs break-words">
                          {log.blocked_reason || "—"}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  );
}
