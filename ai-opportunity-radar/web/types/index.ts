export interface Profile {
  name: string;
  headline: string;
  currentRole: string;
  company: string;
  location: string;
  skills: string[];
  experience: string[];
  education: string[];
  certifications: string[];
  source: "portfolio" | "pdf" | "manual";
}

export interface Opportunity {
  jobTitle: string;
  company: string;
  location: string;
  url: string;
  description: string;
  postedDate: string;
  emails: string[];
}

export interface ScoredOpportunity extends Opportunity {
  matchScore: number;
  matchExplanation: string;
  applicationTips: string;
  contactEmail: string;
  hiringManager: string;
}

export interface PipelineState {
  status: "idle" | "extracting" | "searching" | "matching" | "done" | "error";
  profile: Profile | null;
  opportunities: Opportunity[];
  scored: ScoredOpportunity[];
  error: string | null;
  currentStep: number;
}

export interface FormData {
  role: string;
  location: string;
  portfolioUrl?: string;
  pdfFile?: File;
}
