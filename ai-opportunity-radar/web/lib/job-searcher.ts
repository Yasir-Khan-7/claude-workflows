import type { Opportunity } from "@/types";
import { searchWeb, scrapeUrl } from "./firecrawl";

const EMAIL_RE = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g;
const EMAIL_EXCLUDE = [
  "noreply",
  "no-reply",
  "example.com",
  "sentry.io",
  "github.com",
  "linkedin.com",
  "glassdoor",
  "indeed.com",
  "gravatar",
  "wix.com",
];

function buildQueries(role: string, location: string, skills: string[]): string[] {
  const queries = [
    `${role} jobs in ${location}`,
    `${role} ${location} hiring`,
    `${role} remote ${location} opportunities`,
    `site:linkedin.com/jobs ${role} ${location}`,
    `site:indeed.com ${role} ${location}`,
  ];
  if (skills.length > 0) {
    queries.push(`${role} ${skills.slice(0, 3).join(" ")} ${location}`);
  }
  return queries;
}

function parseResult(item: {
  url: string;
  title: string;
  description: string;
}): Opportunity {
  let { title } = item;
  let company = "";

  if (title.includes(" - ")) {
    const parts = title.split(" - ", 2);
    company = parts[0].trim();
    title = parts[1]?.trim() || title;
  } else if (item.url) {
    try {
      const domain = new URL(item.url).hostname.replace("www.", "");
      company = domain.split(".")[0] || "";
    } catch {
      /* ignore */
    }
  }

  return {
    jobTitle: title || "Unknown",
    company: company || "Unknown",
    location: "",
    url: item.url,
    description: (item.description || "").slice(0, 500),
    postedDate: "",
    emails: [],
  };
}

function extractEmails(text: string): string[] {
  const found = text.match(EMAIL_RE) || [];
  return [
    ...new Set(
      found.filter(
        (e) => !EMAIL_EXCLUDE.some((ex) => e.toLowerCase().includes(ex))
      )
    ),
  ];
}

function deduplicateByUrl(opps: Opportunity[]): Opportunity[] {
  const seen = new Set<string>();
  return opps.filter((o) => {
    const url = o.url.replace(/\/$/, "");
    if (!url || seen.has(url)) return false;
    seen.add(url);
    return true;
  });
}

export async function searchOpportunities(
  role: string,
  location: string,
  skills: string[]
): Promise<Opportunity[]> {
  const queries = buildQueries(role, location, skills);
  const allResults: Opportunity[] = [];

  for (const query of queries) {
    try {
      const results = await searchWeb(query, 5);
      for (const r of results) {
        if (r.url) allResults.push(parseResult(r));
      }
    } catch {
      continue;
    }
    await new Promise((r) => setTimeout(r, 1500));
  }

  const unique = deduplicateByUrl(allResults);

  const toScrape = unique.slice(0, 8);
  for (const opp of toScrape) {
    try {
      const content = await scrapeUrl(opp.url);
      if (content) {
        const emails = extractEmails(content);
        if (emails.length > 0) opp.emails = emails;
      }
    } catch {
      /* continue */
    }
    await new Promise((r) => setTimeout(r, 1500));
  }

  return unique;
}
