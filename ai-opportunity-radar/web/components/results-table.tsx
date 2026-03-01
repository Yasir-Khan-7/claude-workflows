"use client";

import { useState } from "react";
import type { ScoredOpportunity, Profile } from "@/types";
import OpportunityCard from "./opportunity-card";

interface Props {
  opportunities: ScoredOpportunity[];
  profile: Profile;
  role: string;
  location: string;
  onReset: () => void;
}

type SortKey = "matchScore" | "jobTitle" | "company";

export default function ResultsTable({
  opportunities,
  profile,
  role,
  location,
  onReset,
}: Props) {
  const [sortBy, setSortBy] = useState<SortKey>("matchScore");
  const [sortAsc, setSortAsc] = useState(false);
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const [downloading, setDownloading] = useState(false);

  const sorted = [...opportunities].sort((a, b) => {
    const mult = sortAsc ? 1 : -1;
    if (sortBy === "matchScore") return mult * (a.matchScore - b.matchScore);
    return mult * (a[sortBy] || "").localeCompare(b[sortBy] || "");
  });

  const avgScore =
    opportunities.length > 0
      ? Math.round(
          opportunities.reduce((s, o) => s + o.matchScore, 0) / opportunities.length
        )
      : 0;
  const highMatches = opportunities.filter((o) => o.matchScore >= 70).length;

  const handleSort = (key: SortKey) => {
    if (sortBy === key) setSortAsc(!sortAsc);
    else {
      setSortBy(key);
      setSortAsc(key !== "matchScore");
    }
  };

  const handleExcel = async () => {
    setDownloading(true);
    try {
      const resp = await fetch("/api/export-excel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile, opportunities, role, location }),
      });
      if (!resp.ok) throw new Error("Download failed");
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "opportunity_report.xlsx";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert("Failed to download Excel file");
    } finally {
      setDownloading(false);
    }
  };

  const scoreColor = (score: number) =>
    score >= 80
      ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400"
      : score >= 60
      ? "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400"
      : "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400";

  const SortIcon = ({ active, asc }: { active: boolean; asc: boolean }) => (
    <svg
      className={`w-3.5 h-3.5 inline ml-1 transition-transform ${active ? "text-primary" : "text-muted-foreground/40"} ${active && asc ? "rotate-180" : ""}`}
      fill="none" viewBox="0 0 24 24" stroke="currentColor"
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
    </svg>
  );

  return (
    <div className="w-full max-w-6xl mx-auto space-y-6">
      {/* Stats Bar */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-card border border-border rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-foreground">{opportunities.length}</p>
          <p className="text-xs text-muted-foreground mt-1">Opportunities Found</p>
        </div>
        <div className="bg-card border border-border rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-primary">{avgScore}</p>
          <p className="text-xs text-muted-foreground mt-1">Avg Match Score</p>
        </div>
        <div className="bg-card border border-border rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-success">{highMatches}</p>
          <p className="text-xs text-muted-foreground mt-1">High Matches (70+)</p>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-foreground">Results</h2>
        <div className="flex gap-3">
          <button
            onClick={handleExcel}
            disabled={downloading}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-success/10 text-success hover:bg-success/20 border border-success/20 transition-colors disabled:opacity-50"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            {downloading ? "Generating..." : "Download Excel"}
          </button>
          <button
            onClick={onReset}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-muted text-muted-foreground hover:text-foreground hover:bg-muted/80 transition-colors"
          >
            New Search
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="bg-card border border-border rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/50">
                <th className="px-4 py-3 text-left font-medium text-muted-foreground w-12">#</th>
                <th
                  className="px-4 py-3 text-left font-medium text-muted-foreground cursor-pointer hover:text-foreground"
                  onClick={() => handleSort("jobTitle")}
                >
                  Job Title <SortIcon active={sortBy === "jobTitle"} asc={sortAsc} />
                </th>
                <th
                  className="px-4 py-3 text-left font-medium text-muted-foreground cursor-pointer hover:text-foreground"
                  onClick={() => handleSort("company")}
                >
                  Company <SortIcon active={sortBy === "company"} asc={sortAsc} />
                </th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Location</th>
                <th
                  className="px-4 py-3 text-center font-medium text-muted-foreground cursor-pointer hover:text-foreground"
                  onClick={() => handleSort("matchScore")}
                >
                  Score <SortIcon active={sortBy === "matchScore"} asc={sortAsc} />
                </th>
                <th className="px-4 py-3 text-center font-medium text-muted-foreground">Link</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((opp, i) => (
                <tr
                  key={i}
                  className="border-b border-border last:border-0 hover:bg-muted/30 cursor-pointer transition-colors"
                  onClick={() => setExpandedIdx(expandedIdx === i ? null : i)}
                >
                  <td className="px-4 py-3 text-muted-foreground">{i + 1}</td>
                  <td className="px-4 py-3 font-medium text-foreground">{opp.jobTitle}</td>
                  <td className="px-4 py-3 text-foreground">{opp.company}</td>
                  <td className="px-4 py-3 text-muted-foreground">{opp.location || "—"}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`inline-block px-2.5 py-1 rounded-full text-xs font-semibold ${scoreColor(opp.matchScore)}`}>
                      {opp.matchScore}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {opp.url ? (
                      <a
                        href={opp.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="text-primary hover:underline text-xs font-medium"
                      >
                        View
                      </a>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Expanded Card */}
      {expandedIdx !== null && sorted[expandedIdx] && (
        <OpportunityCard
          opportunity={sorted[expandedIdx]}
          onClose={() => setExpandedIdx(null)}
        />
      )}
    </div>
  );
}
