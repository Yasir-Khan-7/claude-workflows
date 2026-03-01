const FIRECRAWL_SCRAPE_URL = "https://api.firecrawl.dev/v1/scrape";
const FIRECRAWL_SEARCH_URL = "https://api.firecrawl.dev/v1/search";
const MAX_RETRIES = 3;

function getApiKey(): string {
  const key = process.env.FIRECRAWL_API_KEY;
  if (!key) throw new Error("FIRECRAWL_API_KEY not set");
  return key;
}

function headers(apiKey: string) {
  return {
    Authorization: `Bearer ${apiKey}`,
    "Content-Type": "application/json",
  };
}

async function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

export async function scrapeUrl(url: string): Promise<string | null> {
  const apiKey = getApiKey();
  for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
    try {
      const resp = await fetch(FIRECRAWL_SCRAPE_URL, {
        method: "POST",
        headers: headers(apiKey),
        body: JSON.stringify({
          url,
          formats: ["markdown"],
          onlyMainContent: true,
        }),
      });

      if (resp.status === 429) {
        await sleep(2000 * (attempt + 1));
        continue;
      }

      const data = await resp.json();
      if (data.success && data.data?.markdown) {
        return data.data.markdown;
      }
    } catch {
      if (attempt < MAX_RETRIES - 1) await sleep(1000 * (attempt + 1));
    }
  }
  return null;
}

export async function searchWeb(
  query: string,
  limit = 5
): Promise<Array<{ url: string; title: string; description: string; markdown?: string }>> {
  const apiKey = getApiKey();
  for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
    try {
      const resp = await fetch(FIRECRAWL_SEARCH_URL, {
        method: "POST",
        headers: headers(apiKey),
        body: JSON.stringify({
          query,
          limit,
          scrapeOptions: { formats: ["markdown"], onlyMainContent: true },
        }),
      });

      if (resp.status === 429) {
        await sleep(2000 * (attempt + 1));
        continue;
      }

      const data = await resp.json();
      if (data.success && Array.isArray(data.data)) {
        return data.data.map((r: Record<string, unknown>) => ({
          url: (r.url as string) || "",
          title: (r.title as string) || "",
          description: (r.description as string) || "",
          markdown: (r.markdown as string) || "",
        }));
      }
      return [];
    } catch {
      if (attempt < MAX_RETRIES - 1) await sleep(1000 * (attempt + 1));
    }
  }
  return [];
}
