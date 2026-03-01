"use client";

import { useState, useCallback } from "react";
import type {
  Profile,
  Opportunity,
  ScoredOpportunity,
  FormData,
} from "@/types";
import RadarForm from "@/components/radar-form";
import ProgressTracker from "@/components/progress-tracker";
import ResultsTable from "@/components/results-table";

type AppState = "form" | "loading" | "results";

export default function Home() {
  const [appState, setAppState] = useState<AppState>("form");
  const [currentStep, setCurrentStep] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const [profile, setProfile] = useState<Profile | null>(null);
  const [scored, setScored] = useState<ScoredOpportunity[]>([]);
  const [formValues, setFormValues] = useState<{ role: string; location: string }>({
    role: "",
    location: "",
  });

  const fileToBase64 = (file: File): Promise<string> =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result as string;
        resolve(result.split(",")[1]);
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });

  const runPipeline = useCallback(async (data: FormData) => {
    setAppState("loading");
    setCurrentStep(0);
    setError(null);
    setFormValues({ role: data.role, location: data.location });

    try {
      // Step 1: Extract profile
      setCurrentStep(0);
      const profileBody: Record<string, string> = {};
      if (data.portfolioUrl) {
        profileBody.portfolioUrl = data.portfolioUrl;
      } else if (data.pdfFile) {
        profileBody.pdfBase64 = await fileToBase64(data.pdfFile);
      }

      const profileResp = await fetch("/api/extract-profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(profileBody),
      });
      const profileData = await profileResp.json();
      if (!profileResp.ok) throw new Error(profileData.error || "Profile extraction failed");
      const extractedProfile: Profile = profileData.profile;
      setProfile(extractedProfile);

      // Step 2: Search jobs
      setCurrentStep(1);
      const searchResp = await fetch("/api/search-jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          role: data.role,
          location: data.location,
          skills: extractedProfile.skills.slice(0, 10),
        }),
      });
      const searchData = await searchResp.json();
      if (!searchResp.ok) throw new Error(searchData.error || "Job search failed");
      const opportunities: Opportunity[] = searchData.opportunities;

      if (opportunities.length === 0) {
        throw new Error("No opportunities found. Try broadening your search terms or location.");
      }

      // Step 3: AI matching
      setCurrentStep(2);
      const matchResp = await fetch("/api/analyze-match", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          profile: extractedProfile,
          opportunities,
        }),
      });
      const matchData = await matchResp.json();
      if (!matchResp.ok) throw new Error(matchData.error || "AI matching failed");

      setScored(matchData.scored);
      setCurrentStep(3);

      await new Promise((r) => setTimeout(r, 800));
      setAppState("results");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    }
  }, []);

  const handleReset = () => {
    setAppState("form");
    setCurrentStep(0);
    setError(null);
    setProfile(null);
    setScored([]);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div>
              <h1 className="text-base font-bold text-foreground leading-tight">
                AI Opportunity Radar
              </h1>
              <p className="text-xs text-muted-foreground">
                Powered by Firecrawl + Groq
              </p>
            </div>
          </div>
          {appState !== "form" && (
            <button
              onClick={handleReset}
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Start Over
            </button>
          )}
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {appState === "form" && (
          <div className="flex flex-col items-center pt-8">
            {/* Hero */}
            <div className="text-center mb-10">
              <div className="inline-flex items-center gap-2 px-3 py-1 mb-4 text-xs font-medium bg-primary/10 text-primary rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse-slow" />
                AI-Powered Job Matching
              </div>
              <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-3 tracking-tight">
                Find Your Next Opportunity
              </h2>
              <p className="text-muted-foreground max-w-lg mx-auto">
                Enter your target role, location, and share your portfolio or resume.
                We&apos;ll scan the web and match you with the best opportunities.
              </p>
            </div>

            <RadarForm onSubmit={runPipeline} isLoading={false} />

            {/* Features */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-16 w-full max-w-2xl">
              {[
                {
                  icon: "M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z",
                  title: "Smart Search",
                  desc: "Scans multiple job boards simultaneously",
                },
                {
                  icon: "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z",
                  title: "AI Scoring",
                  desc: "Each opportunity scored 0-100 against your profile",
                },
                {
                  icon: "M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
                  title: "Excel Export",
                  desc: "Download a styled spreadsheet of all matches",
                },
              ].map((f, i) => (
                <div
                  key={i}
                  className="flex flex-col items-center text-center p-4 rounded-xl bg-card border border-border"
                >
                  <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center mb-3">
                    <svg className="w-5 h-5 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={f.icon} />
                    </svg>
                  </div>
                  <h3 className="text-sm font-semibold text-foreground mb-1">{f.title}</h3>
                  <p className="text-xs text-muted-foreground">{f.desc}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {appState === "loading" && (
          <div className="flex flex-col items-center pt-16">
            <h2 className="text-xl font-semibold text-foreground mb-2">
              Scanning the market...
            </h2>
            <p className="text-sm text-muted-foreground mb-8">
              This typically takes 1-3 minutes
            </p>
            <ProgressTracker currentStep={currentStep} error={error} />
            {error && (
              <button
                onClick={handleReset}
                className="mt-6 px-6 py-2.5 text-sm font-medium rounded-lg bg-muted text-foreground hover:bg-muted/80 transition-colors"
              >
                Try Again
              </button>
            )}
          </div>
        )}

        {appState === "results" && profile && (
          <ResultsTable
            opportunities={scored}
            profile={profile}
            role={formValues.role}
            location={formValues.location}
            onReset={handleReset}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-border mt-16 py-6">
        <p className="text-center text-xs text-muted-foreground">
          AI Opportunity Radar &middot; WAT Framework &middot; Built with Next.js, Firecrawl & Groq
        </p>
      </footer>
    </div>
  );
}
