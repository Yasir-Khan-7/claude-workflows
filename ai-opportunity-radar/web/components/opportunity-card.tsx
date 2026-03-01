"use client";

import type { ScoredOpportunity } from "@/types";

interface Props {
  opportunity: ScoredOpportunity;
  onClose: () => void;
}

export default function OpportunityCard({ opportunity: opp, onClose }: Props) {
  const emails = opp.emails?.length
    ? opp.emails
    : opp.contactEmail
    ? [opp.contactEmail]
    : [];

  const scoreColor =
    opp.matchScore >= 80
      ? "text-emerald-600 dark:text-emerald-400"
      : opp.matchScore >= 60
      ? "text-amber-600 dark:text-amber-400"
      : "text-red-600 dark:text-red-400";

  return (
    <div className="bg-card border border-border rounded-xl p-6 shadow-lg space-y-4 animate-in fade-in slide-in-from-top-2 duration-200">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-bold text-foreground">{opp.jobTitle}</h3>
          <p className="text-sm text-muted-foreground">
            {opp.company} {opp.location ? `\u00B7 ${opp.location}` : ""}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-2xl font-bold ${scoreColor}`}>{opp.matchScore}</span>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {opp.description && (
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
            Description
          </h4>
          <p className="text-sm text-foreground/80">{opp.description}</p>
        </div>
      )}

      {opp.matchExplanation && (
        <div className="bg-primary/5 border border-primary/10 rounded-lg p-3">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-primary mb-1">
            Match Analysis
          </h4>
          <p className="text-sm text-foreground/80">{opp.matchExplanation}</p>
        </div>
      )}

      {opp.applicationTips && (
        <div className="bg-accent/5 border border-accent/10 rounded-lg p-3">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-accent mb-1">
            Application Tips
          </h4>
          <p className="text-sm text-foreground/80">{opp.applicationTips}</p>
        </div>
      )}

      {emails.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
            Contact
          </h4>
          <div className="flex flex-wrap gap-2">
            {emails.map((email, i) => (
              <a
                key={i}
                href={`mailto:${email}`}
                className="inline-flex items-center gap-1 px-3 py-1 text-xs font-medium bg-muted rounded-full text-foreground hover:bg-primary/10 hover:text-primary transition-colors"
              >
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                {email}
              </a>
            ))}
          </div>
        </div>
      )}

      {opp.hiringManager && (
        <p className="text-xs text-muted-foreground">
          Hiring Manager: <span className="font-medium text-foreground">{opp.hiringManager}</span>
        </p>
      )}

      {opp.url && (
        <a
          href={opp.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity"
        >
          Apply / View Posting
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
        </a>
      )}
    </div>
  );
}
