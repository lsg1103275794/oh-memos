/**
 * MemOS MCP Server API Client Module
 *
 * HTTP fetch wrapper with timeout, retry, and health check.
 */

import { MEMOS_URL, MEMOS_API_WAIT_MAX, MEMOS_TIMEOUT_HEALTH, MEMOS_TIMEOUT_TOOL, logger, registeredCubes } from "./config.js";

// ============================================================================
// Fetch with Timeout
// ============================================================================

export async function fetchWithTimeout(
  url: string,
  options: RequestInit & { timeoutMs?: number } = {}
): Promise<Response> {
  const timeoutMs = (options.timeoutMs ?? MEMOS_TIMEOUT_TOOL) * 1000;
  const { timeoutMs: _, ...fetchOptions } = options;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      signal: controller.signal,
    });
    return response;
  } finally {
    clearTimeout(timer);
  }
}

// ============================================================================
// API Readiness Check
// ============================================================================

export async function waitForApiReady(
  maxWait?: number,
  interval = 2.0
): Promise<boolean> {
  const maxWaitMs = (maxWait ?? MEMOS_API_WAIT_MAX) * 1000;
  const intervalMs = interval * 1000;
  const start = Date.now();

  while (Date.now() - start < maxWaitMs) {
    try {
      const response = await fetchWithTimeout(`${MEMOS_URL}/users`, {
        timeoutMs: MEMOS_TIMEOUT_HEALTH,
      });
      if (response.ok) {
        logger.debug("MemOS API is ready");
        return true;
      }
    } catch {
      // Not ready yet
    }
    await sleep(intervalMs);
  }

  logger.warning(`MemOS API not ready after ${maxWait ?? MEMOS_API_WAIT_MAX}s`);
  return false;
}

// ============================================================================
// API Call with Retry
// ============================================================================

export type HttpMethod = "GET" | "POST" | "DELETE";

export interface ApiCallOptions {
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined>;
  headers?: Record<string, string>;
}

export interface ApiCallResult {
  success: boolean;
  data: Record<string, unknown> | null;
  status: number;
}

function buildUrl(base: string, params?: Record<string, string | number | boolean | undefined>): string {
  if (!params) return base;
  const urlParams = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined) urlParams.append(k, String(v));
  }
  const qs = urlParams.toString();
  return qs ? `${base}?${qs}` : base;
}

async function doFetch(
  method: HttpMethod,
  url: string,
  options: ApiCallOptions
): Promise<{ status: number; data: Record<string, unknown> | null }> {
  const finalUrl = buildUrl(url, options.params);
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  const fetchOptions: RequestInit = {
    method,
    headers,
  };

  if (options.body !== undefined && method !== "GET") {
    fetchOptions.body = JSON.stringify(options.body);
  }

  const response = await fetchWithTimeout(finalUrl, fetchOptions as RequestInit & { timeoutMs?: number });

  if (!response.ok && response.status !== 400) {
    return { status: response.status, data: null };
  }

  try {
    const data = await response.json() as Record<string, unknown>;
    return { status: response.status, data };
  } catch {
    return { status: response.status, data: null };
  }
}

export async function apiCallWithRetry(
  method: HttpMethod,
  url: string,
  cubeId: string,
  options: ApiCallOptions = {},
  ensureCubeRegistered?: (cubeId: string, force?: boolean) => Promise<[boolean, string | null]>
): Promise<ApiCallResult> {
  const { status, data } = await doFetch(method, url, options);

  if (status === 200 && data) {
    if ((data as Record<string, unknown>).code === 200) {
      return { success: true, data, status: 200 };
    }

    // API returned error code - try re-registration if available
    if (ensureCubeRegistered) {
      registeredCubes.delete(cubeId);
      const [regSuccess] = await ensureCubeRegistered(cubeId, true);
      if (regSuccess) {
        const retry = await doFetch(method, url, options);
        if (retry.status === 200 && retry.data && (retry.data as Record<string, unknown>).code === 200) {
          return { success: true, data: retry.data, status: 200 };
        }
        return { success: false, data: retry.data, status: 200 };
      }
    }

    return { success: false, data, status: 200 };
  }

  if (status === 400 && ensureCubeRegistered) {
    // 400 often means cube not loaded
    registeredCubes.delete(cubeId);
    const [regSuccess] = await ensureCubeRegistered(cubeId, true);
    if (regSuccess) {
      const retry = await doFetch(method, url, options);
      if (retry.status === 200 && retry.data && (retry.data as Record<string, unknown>).code === 200) {
        return { success: true, data: retry.data, status: 200 };
      }
    }
    return { success: false, data: null, status: 400 };
  }

  return { success: false, data, status };
}

// ============================================================================
// Helper
// ============================================================================

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
