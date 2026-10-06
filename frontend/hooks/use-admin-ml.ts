"use client";

import { useQuery } from "@tanstack/react-query";

import { adminMlApi } from "@/lib/api/admin-ml";
import type {
  ListAnomaliesParams,
  ListDemandForecastParams,
} from "@/lib/api-types";

// ══════════════════════════════════════════════════════════════
// Query keys
// ══════════════════════════════════════════════════════════════
export const mlKeys = {
  all: ["admin", "ml"] as const,
  summary: () => [...mlKeys.all, "summary"] as const,
  forecast: (params: ListDemandForecastParams) =>
    [...mlKeys.all, "forecast", params] as const,
  anomalies: (params: ListAnomaliesParams) =>
    [...mlKeys.all, "anomalies", params] as const,
};

// ══════════════════════════════════════════════════════════════
// Queries
// ══════════════════════════════════════════════════════════════
export function useMlSummary() {
  return useQuery({
    queryKey: mlKeys.summary(),
    queryFn: () => adminMlApi.summary(),
    staleTime: 60_000,
  });
}

export function useDemandForecast(params: ListDemandForecastParams = {}) {
  return useQuery({
    queryKey: mlKeys.forecast(params),
    queryFn: () => adminMlApi.demandForecast(params),
    staleTime: 60_000,
  });
}

export function useAnomalies(params: ListAnomaliesParams = {}) {
  return useQuery({
    queryKey: mlKeys.anomalies(params),
    queryFn: () => adminMlApi.anomalies(params),
    staleTime: 60_000,
  });
}
