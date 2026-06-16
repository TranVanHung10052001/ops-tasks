"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { Playbook, PlaybookList } from "@/lib/types";
import {
  Search, RefreshCw, X, Clock, Repeat, Target as TargetIcon,
  ChevronRight, BookOpen, AlertTriangle, ArrowUpRight,
} from "lucide-react";

const GRADE_COLOR: Record<string, string> = {
  G4: "bg-purple-50 border-purple-200 text-purple-900",
  G3: "bg-blue-50 border-blue-200 text-blue-900",
  "ACT-G3": "bg-blue-50 border-blue-200 text-blue-900",
  G2: "bg-green-50 border-green-200 text-green-900",
  G1: "bg-amber-50 border-amber-200 text-amber-900",
};

const GRADE_DOT: Record<string, string> = {
  G4: "bg-purple-500",
  G3: "bg-blue-500",
  G2: "bg-green-500",
  G1: "bg-amber-500",
};

const CAT_LABEL: Record<string, string> = {
  daily_ops: "Daily Ops",
  planning: "Planning",
  vendor: "Vendor",
  recruitment: "Driver Supply",
  analysis: "Analysis",
  crisis: "Crisis",
  expansion: "Expansion",
};

const CAT_COLOR: Record<string, string> = {
  daily_ops: "bg-gray-100 text-gray-700",
  planning: "bg-blue-50 text-blue-700",
  vendor: "bg-indigo-50 text-indigo-700",
  recruitment: "bg-pink-50 text-pink-700",
  analysis: "bg-cyan-50 text-cyan-700",
  crisis: "bg-red-50 text-red-700",
  expansion: "bg-purple-50 text-purple-700",
};

function GradePill({ grade }: { grade: string }) {
  return (
    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold border ${GRADE_COLOR[grade] ?? "bg-gray-100 text-gray-700 border-gray-200"}`}>
      <span className={`w-1 h-1 rounded-full ${GRADE_DOT[grade] ?? "bg-gray-400"}`} />
      {grade}
    </span>
  );
}

function PlaybookCard({
  pb,
  onClick,
}: {
  pb: Playbook;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="card p-4 text-left hover:border-gray-300 hover:shadow-sm transition w-full group"
    >
      <div className="flex items-start justify-between mb-2">
        <span className="text-[10px] font-mono text-gray-400 tabular-nums">{pb.id}</span>
        <ChevronRight size={14} className="text-gray-300 group-hover:text-gray-600 transition" />
      </div>
      <h2 className="text-sm font-semibold text-gray-900 leading-snug mb-2">{pb.name}</h2>
      <div className="flex items-center gap-1.5 mb-3 flex-wrap">
        <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${CAT_COLOR[pb.category] ?? "bg-gray-100 text-gray-700"}`}>
          {CAT_LABEL[pb.category] ?? pb.category}
        </span>
        <GradePill grade={pb.owner_grade} />
      </div>
      <div className="grid grid-cols-3 gap-2 text-[11px] text-gray-500">
        <div className="flex items-center gap-1">
          <Clock size={11} />
          <span className="tabular-nums">{pb.estimated_minutes}ph</span>
        </div>
        <div className="flex items-center gap-1 truncate">
          <Repeat size={11} />
          <span className="truncate">{pb.frequency.split(",")[0]}</span>
        </div>
        <div className="flex items-center gap-1">
          <TargetIcon size={11} />
          <span className="tabular-nums">{pb.okr_links.length}</span>
        </div>
      </div>
      <p className="text-xs text-gray-500 mt-2 line-clamp-2">
        {pb.steps.length} bước · {pb.outputs.length} outputs
      </p>
    </button>
  );
}

function PlaybookDrawer({ pb, onClose }: { pb: Playbook; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-black/30" onClick={onClose} />
      <div className="w-full max-w-2xl bg-white border-l border-gray-200 flex flex-col h-full shadow-2xl">
        <div className="px-5 py-4 border-b border-gray-100 flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] font-mono text-gray-400">{pb.id}</span>
              <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${CAT_COLOR[pb.category]}`}>
                {CAT_LABEL[pb.category] ?? pb.category}
              </span>
              <GradePill grade={pb.owner_grade} />
              {pb.support_grade && (
                <span className="text-[10px] text-gray-500">+ support <GradePill grade={pb.support_grade} /></span>
              )}
            </div>
            <h2 className="text-lg font-semibold leading-tight">{pb.name}</h2>
            <div className="flex items-center gap-3 mt-1.5 text-xs text-gray-500">
              <span className="flex items-center gap-1"><Clock size={12} /> ~{pb.estimated_minutes}ph</span>
              <span className="flex items-center gap-1"><Repeat size={12} /> {pb.frequency}</span>
            </div>
          </div>
          <button onClick={onClose} className="btn-ghost p-1.5 shrink-0">
            <X size={16} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto scrollbar-thin px-5 py-4 space-y-5">
          {pb.okr_links.length > 0 && (
            <div>
              <h3 className="mb-2 flex items-center gap-1.5">
                <TargetIcon size={13} className="text-gray-400" />
                OKR Links
              </h3>
              <div className="flex gap-1.5 flex-wrap">
                {pb.okr_links.map((okr) => (
                  <span key={okr} className="px-2 py-0.5 rounded bg-gray-100 text-gray-700 text-[11px] font-mono">
                    {okr}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h3 className="mb-2">📥 Inputs</h3>
              <ul className="space-y-1 text-xs text-gray-700">
                {pb.inputs.map((x, i) => (
                  <li key={i} className="flex gap-1.5">
                    <span className="text-gray-400">•</span>
                    <span className="leading-relaxed">{x}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="mb-2">📤 Outputs</h3>
              <ul className="space-y-1 text-xs text-gray-700">
                {pb.outputs.map((x, i) => (
                  <li key={i} className="flex gap-1.5">
                    <span className="text-gray-400">•</span>
                    <span className="leading-relaxed">{x}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div>
            <h3 className="mb-3 flex items-center gap-1.5">
              <BookOpen size={13} className="text-gray-400" />
              Execution Steps ({pb.steps.length})
            </h3>
            <ol className="space-y-3">
              {pb.steps.map((s) => (
                <li key={s.n} className="card p-3 border-l-4 border-l-gray-200">
                  <div className="flex items-start gap-3">
                    <div className="w-7 h-7 rounded-full bg-gray-900 text-white text-xs font-semibold flex items-center justify-center shrink-0">
                      {s.n}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <p className="text-sm font-semibold text-gray-900">{s.title}</p>
                        <GradePill grade={s.owner_grade} />
                      </div>
                      {s.expected_output && (
                        <p className="text-xs text-gray-700 mt-1">
                          <span className="font-medium text-gray-800">→ Output:</span> {s.expected_output}
                        </p>
                      )}
                      {s.watch_out && (
                        <div className="mt-1.5 flex items-start gap-1 bg-amber-50 px-2 py-1.5 rounded text-xs text-amber-800 border border-amber-100">
                          <AlertTriangle size={11} className="shrink-0 mt-0.5" />
                          <span className="leading-relaxed">{s.watch_out}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          </div>

          {pb.escalation && (
            <div className="card p-3 border-red-100 bg-red-50/30">
              <h3 className="mb-1 flex items-center gap-1.5 text-red-700">
                <ArrowUpRight size={13} />
                Escalation
              </h3>
              <p className="text-xs text-gray-700 leading-relaxed">{pb.escalation}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function PlaybooksPage() {
  const [data, setData] = useState<PlaybookList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [gradeFilter, setGradeFilter] = useState<string>("");
  const [categoryFilter, setCategoryFilter] = useState<string>("");
  const [selected, setSelected] = useState<Playbook | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const d = await api.playbooks();
      setData(d);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    if (!data) return [];
    const q = search.trim().toLowerCase();
    return data.playbooks.filter((p) => {
      if (gradeFilter && p.owner_grade !== gradeFilter) return false;
      if (categoryFilter && p.category !== categoryFilter) return false;
      if (q) {
        return (
          p.name.toLowerCase().includes(q)
          || p.id.toLowerCase().includes(q)
          || p.category.toLowerCase().includes(q)
          || p.okr_links.some((o) => o.toLowerCase().includes(q))
        );
      }
      return true;
    });
  }, [data, search, gradeFilter, categoryFilter]);

  return (
    <div className="p-8 max-w-7xl">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h1>Task Playbooks</h1>
          <p className="text-xs text-gray-400 mt-0.5">
            Thư viện SOP — mỗi task lặp lại có execution steps rõ ràng, owner theo grade, escalation path.
            {data && <> · {data.total} playbooks</>}
          </p>
        </div>
        <button onClick={load} disabled={loading} className="btn-ghost text-xs">
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 mt-4 mb-5 flex-wrap">
        <div className="relative">
          <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Tìm playbook (tên / OKR / category)..."
            className="input pl-7 text-xs w-72"
          />
        </div>
        <select
          value={gradeFilter}
          onChange={(e) => setGradeFilter(e.target.value)}
          className="select text-xs w-32"
        >
          <option value="">Mọi grade</option>
          <option value="G3">G3 owns</option>
          <option value="G2">G2 owns</option>
          <option value="G1">G1 owns</option>
        </select>
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="select text-xs w-40"
        >
          <option value="">Mọi category</option>
          {data?.categories.map((c) => (
            <option key={c.id} value={c.id}>{c.label}</option>
          ))}
        </select>
        {(search || gradeFilter || categoryFilter) && (
          <button
            onClick={() => { setSearch(""); setGradeFilter(""); setCategoryFilter(""); }}
            className="btn-ghost text-xs"
          >
            Clear
          </button>
        )}
        <span className="text-xs text-gray-400 ml-auto">{filtered.length} kết quả</span>
      </div>

      {error && (
        <div className="card p-5 border-red-200 mb-4">
          <p className="text-sm text-red-600 font-medium">Cannot connect to API</p>
          <p className="text-xs text-gray-400 mt-0.5">{error}</p>
        </div>
      )}

      {loading && !data ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="card h-44 animate-pulse bg-gray-100" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="card p-10 text-center">
          <BookOpen size={28} className="mx-auto text-gray-300 mb-2" />
          <p className="text-sm text-gray-500">Không có playbook nào khớp filter.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((pb) => (
            <PlaybookCard key={pb.id} pb={pb} onClick={() => setSelected(pb)} />
          ))}
        </div>
      )}

      {selected && (
        <PlaybookDrawer pb={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
