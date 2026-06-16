const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export function resolveApiBaseUrl(value: string | undefined): string {
  return (value?.replace(/\/$/, "") || DEFAULT_API_BASE_URL);
}
