"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { adminAnalyticsApi } from "@/lib/api/admin-analytics";
import {
  computeSummary,
  computeTimeSeries,
  computeTopProducts,
} from "@/lib/analytics-utils";
import type { ListDailySalesParams } from "@/lib/api-types";

// ══════════════════════════════════════════════════════════════
// Query keys
// ══════════════════════════════════════════════════════════════
export const analyticsKeys = {
  all: ["admin", "analytics"] as const,
  sales: (params: ListDailySalesParams) =>
    [...analyticsKeys.all, "sales", params] as const,
  alerts: (page: number) => [...analyticsKeys.all, "alerts", page] as const,
};

// ══════════════════════════════════════════════════════════════
// Queries
// ══════════════════════════════════════════════════════════════
export function useDailySales(params: ListDailySalesParams = {}) {
  return useQuery({
    queryKey: analyticsKeys.sales(params),
    queryFn: () => adminAnalyticsApi.listSales(params),
    staleTime: 60_000,
  });
}

export function useAnalyticsAlerts(page = 1, size = 20) {
  return useQuery({
    queryKey: analyticsKeys.alerts(page),
    queryFn: () => adminAnalyticsApi.listAlerts({ page, size }),
    staleTime: 60_000,
  });
}

// ══════════════════════════════════════════════════════════════
// Derived: aggregated dashboard data
// ══════════════════════════════════════════════════════════════
export function useAnalyticsDashboard(params: ListDailySalesParams = {}) {
  const query = useDailySales(params);

  const summary = query.data ? computeSummary(query.data.items) : null;
  const timeSeries = query.data ? computeTimeSeries(query.data.items, 30) : [];
  const topProducts = query.data ? computeTopProducts(query.data.items, 10) : [];

  return {
    ...query,
    summary,
    timeSeries,
    topProducts,
  };
}

// ══════════════════════════════════════════════════════════════
// Mutations
// ══════════════════════════════════════════════════════════════
export function useResolveAnalyticsAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: adminAnalyticsApi.resolveAlert,
    onSuccess: () => {
      toast.success("Alert resolved");
      qc.invalidateQueries({ queryKey: analyticsKeys.all });
      // Also invalidate inventory alerts (same underlying data)
      qc.invalidateQueries({ queryKey: ["admin", "inventory"] });
    },
    onError: (error: unknown) => {
      const message =
        error instanceof Error ? error.message : "Failed to resolve alert";
      toast.error(message);
    },
  });
}
