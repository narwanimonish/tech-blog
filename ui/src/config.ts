import type { AppConfig } from "./types";

let cachedConfig: AppConfig | null = null;

export async function loadConfig(): Promise<AppConfig> {
  if (cachedConfig) {
    return cachedConfig;
  }

  if (import.meta.env.VITE_API_URL) {
    cachedConfig = { apiUrl: String(import.meta.env.VITE_API_URL) };
    return cachedConfig;
  }

  const response = await fetch("/config.json");
  if (!response.ok) {
    throw new Error("Failed to load config.json");
  }

  cachedConfig = (await response.json()) as AppConfig;
  return cachedConfig;
}

export async function getApiBaseUrl(): Promise<string> {
  const config = await loadConfig();
  return config.apiUrl.replace(/\/$/, "");
}
