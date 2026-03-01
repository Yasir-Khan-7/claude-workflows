"use client";

import { useState, useRef, type FormEvent, type DragEvent } from "react";
import type { FormData } from "@/types";

interface Props {
  onSubmit: (data: FormData) => void;
  isLoading: boolean;
}

export default function RadarForm({ onSubmit, isLoading }: Props) {
  const [role, setRole] = useState("");
  const [location, setLocation] = useState("");
  const [tab, setTab] = useState<"url" | "pdf">("url");
  const [portfolioUrl, setPortfolioUrl] = useState("");
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!role.trim() || !location.trim()) return;
    if (tab === "url" && !portfolioUrl.trim()) return;
    if (tab === "pdf" && !pdfFile) return;

    onSubmit({
      role: role.trim(),
      location: location.trim(),
      portfolioUrl: tab === "url" ? portfolioUrl.trim() : undefined,
      pdfFile: tab === "pdf" ? pdfFile! : undefined,
    });
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file?.type === "application/pdf") setPdfFile(file);
  };

  const isValid =
    role.trim() &&
    location.trim() &&
    ((tab === "url" && portfolioUrl.trim()) || (tab === "pdf" && pdfFile));

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto space-y-6">
      {/* Role */}
      <div>
        <label className="block text-sm font-medium text-foreground mb-2">
          Target Role
        </label>
        <input
          type="text"
          placeholder="e.g. Full Stack Developer, Product Manager"
          value={role}
          onChange={(e) => setRole(e.target.value)}
          className="w-full px-4 py-3 rounded-xl border border-border bg-card text-card-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
          disabled={isLoading}
        />
      </div>

      {/* Location */}
      <div>
        <label className="block text-sm font-medium text-foreground mb-2">
          Location
        </label>
        <input
          type="text"
          placeholder="e.g. Islamabad, Remote, New York"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          className="w-full px-4 py-3 rounded-xl border border-border bg-card text-card-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
          disabled={isLoading}
        />
      </div>

      {/* Profile Source Tabs */}
      <div>
        <label className="block text-sm font-medium text-foreground mb-2">
          Your Profile
        </label>
        <div className="flex gap-1 p-1 bg-muted rounded-xl mb-4">
          <button
            type="button"
            onClick={() => setTab("url")}
            className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-medium transition-all ${
              tab === "url"
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Portfolio URL
          </button>
          <button
            type="button"
            onClick={() => setTab("pdf")}
            className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-medium transition-all ${
              tab === "pdf"
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Upload Resume (PDF)
          </button>
        </div>

        {tab === "url" ? (
          <input
            type="url"
            placeholder="https://yourportfolio.com"
            value={portfolioUrl}
            onChange={(e) => setPortfolioUrl(e.target.value)}
            className="w-full px-4 py-3 rounded-xl border border-border bg-card text-card-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
            disabled={isLoading}
          />
        ) : (
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileRef.current?.click()}
            className={`relative flex flex-col items-center justify-center gap-3 p-8 rounded-xl border-2 border-dashed cursor-pointer transition-all ${
              dragOver
                ? "border-primary bg-primary/5"
                : pdfFile
                ? "border-success bg-success/5"
                : "border-border hover:border-primary/50 hover:bg-muted/50"
            }`}
          >
            <input
              ref={fileRef}
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f?.type === "application/pdf") setPdfFile(f);
              }}
            />
            {pdfFile ? (
              <>
                <svg className="w-8 h-8 text-success" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-sm font-medium text-success">{pdfFile.name}</span>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); setPdfFile(null); }}
                  className="text-xs text-muted-foreground hover:text-destructive transition-colors"
                >
                  Remove
                </button>
              </>
            ) : (
              <>
                <svg className="w-10 h-10 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <span className="text-sm text-muted-foreground">
                  Drop your PDF resume here, or <span className="text-primary font-medium">click to browse</span>
                </span>
              </>
            )}
          </div>
        )}
      </div>

      {/* Submit */}
      <button
        type="submit"
        disabled={!isValid || isLoading}
        className="w-full py-3.5 px-6 rounded-xl font-semibold text-white bg-gradient-to-r from-primary to-accent hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-lg shadow-primary/25 hover:shadow-primary/40"
      >
        {isLoading ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="w-5 h-5 animate-spin-slow" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            Processing...
          </span>
        ) : (
          "Find Opportunities"
        )}
      </button>
    </form>
  );
}
