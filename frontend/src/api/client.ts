const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "https://sentinelai.work";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function getAccessToken(): string | null {
  try {
    return localStorage.getItem("sentinel_access_token");
  } catch {
    return null;
  }
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getAccessToken();
  const method = options.method ?? "GET";
  const url = `${BASE_URL}${path}`;

  console.log(`[api] ${method} ${url}`);

  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers ?? {}),
    },
  });

  console.log(`[api] ${method} ${url} → ${res.status}`);

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    console.error(`[api] ${method} ${url} failed: ${res.status}`, text);

    // Auth or payment gate — both resolve by going through login
    if (res.status === 401 || res.status === 402 || res.status === 403) {
      try { localStorage.removeItem("sentinel_access_token"); } catch {}
      window.location.replace("/login");
      return new Promise<never>(() => {});
    }

    throw new ApiError(res.status, text || `API error ${res.status}`);
  }

  const contentType = res.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    return undefined as T;
  }

  return (await res.json()) as T;
}