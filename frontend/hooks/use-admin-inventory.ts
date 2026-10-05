"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { adminInventoryApi } from "@/lib/api/admin-inventory";
import type {
  ListInventoryParams,
  ListReorderSuggestionsParams,
} from "@/lib/api-types";

// ══════════════════════════════════════════════════════════════
// Query keys (hierarchical — invalidate any prefix works)
// ══════════════════════════════════════════════════════════════
export const inventoryKeys = {
  all: ["admin", "inventory"] as const,
  list: (params: ListInventoryParams) =>
    [...inventoryKeys.all, "list", params] as const,
  stats: () => [...inventoryKeys.all, "stats"] as const,
  alerts: (page: number) => [...inventoryKeys.all, "alerts", page] as const,
  reorder: (params: ListReorderSuggestionsParams) =>
    [...inventoryKeys.all, "reorder", params] as const,
};

// ══════════════════════════════════════════════════════════════
// Queries
// ══════════════════════════════════════════════════════════════
export function useAdminInventory(params: ListInventoryParams) {
  return useQuery({
    queryKey: inventoryKeys.list(params),
    queryFn: () => adminInventoryApi.list(params),
    staleTime: 15_000,
  });
}

export function useInventoryStats() {
  return useQuery({
    queryKey: inventoryKeys.stats(),
    queryFn: () => adminInventoryApi.stats(),
    staleTime: 30_000,
  });
}

export function useInventoryAlerts(page = 1, size = 20) {
  return useQuery({
    queryKey: inventoryKeys.alerts(page),
    queryFn: () => adminInventoryApi.listAlerts({ page, size }),
    staleTime: 30_000,
  });
}

export function useReorderSuggestions(params: ListReorderSuggestionsParams = {}) {
  return useQuery({
    queryKey: inventoryKeys.reorder(params),
    queryFn: () => adminInventoryApi.reorderSuggestions(params),
    staleTime: 60_000,
  });
}

// ══════════════════════════════════════════════════════════════
// Mutations
// ══════════════════════════════════════════════════════════════
export function useAdjustInventory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: adminInventoryApi.adjust,
    onSuccess: (data) => {
      toast.success(
        `Stock updated: ${data.product.name} → ${data.quantity} units`,
      );
      // Invalidate all inventory-related queries
      qc.invalidateQueries({ queryKey: inventoryKeys.all });
    },
    onError: (error: unknown) => {
      const message =
        error instanceof Error ? error.message : "Failed to adjust stock";
      toast.error(message);
    },
  });
}

export function useResolveAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: adminInventoryApi.resolveAlert,
    onSuccess: () => {
      toast.success("Alert resolved");
      qc.invalidateQueries({ queryKey: inventoryKeys.all });
    },
    onError: (error: unknown) => {
      const message =
        error instanceof Error ? error.message : "Failed to resolve alert";
      toast.error(message);
    },
  });
}
