"use client";

interface Step {
  label: string;
  description: string;
}

const STEPS: Step[] = [
  { label: "Analyzing Profile", description: "Extracting skills and experience..." },
  { label: "Searching Jobs", description: "Scanning job boards across the web..." },
  { label: "AI Matching", description: "Scoring opportunities against your profile..." },
  { label: "Complete", description: "Your opportunities are ready!" },
];

interface Props {
  currentStep: number;
  error?: string | null;
}

export default function ProgressTracker({ currentStep, error }: Props) {
  return (
    <div className="w-full max-w-lg mx-auto py-8">
      <div className="space-y-0">
        {STEPS.map((step, i) => {
          const isActive = i === currentStep;
          const isDone = i < currentStep;
          const isFuture = i > currentStep;
          const isError = error && isActive;

          return (
            <div key={i} className="flex gap-4">
              {/* Vertical line + dot */}
              <div className="flex flex-col items-center">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all duration-500 ${
                    isError
                      ? "border-destructive bg-destructive/10"
                      : isDone
                      ? "border-success bg-success text-white"
                      : isActive
                      ? "border-primary bg-primary/10"
                      : "border-border bg-muted"
                  }`}
                >
                  {isDone ? (
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : isError ? (
                    <svg className="w-5 h-5 text-destructive" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  ) : isActive ? (
                    <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin-slow" />
                  ) : (
                    <span className="text-sm text-muted-foreground font-medium">{i + 1}</span>
                  )}
                </div>
                {i < STEPS.length - 1 && (
                  <div
                    className={`w-0.5 h-12 transition-colors duration-500 ${
                      isDone ? "bg-success" : "bg-border"
                    }`}
                  />
                )}
              </div>

              {/* Text */}
              <div className="pt-1.5 pb-8">
                <p
                  className={`font-semibold text-sm transition-colors ${
                    isError
                      ? "text-destructive"
                      : isDone
                      ? "text-success"
                      : isActive
                      ? "text-foreground"
                      : "text-muted-foreground"
                  }`}
                >
                  {step.label}
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {isError ? error : step.description}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
