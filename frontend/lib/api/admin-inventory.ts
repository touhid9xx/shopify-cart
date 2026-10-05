import { api } from "./client";
import type {
  InventoryAlert,
  InventoryStats,
  InventoryWithProduct,
  ListInventoryParams,
  ListReorderSuggestionsParams,
  Page,
  ReorderListResponse,
  ReorderSuggestion,
} from "@/lib/api-types";

export const adminInventoryApi = {
  /** List inventory rows (paginated, filterable) */
  list: (params: ListInventoryParams = {}) => {
    const qs = new URLSearchParams();
    qs.set("page", String(params.page ?? 1));
    qs.set("size", String(params.size ?? 20));
    if (params.low_stock_only) qs.set("low_stock_only", "true");
    if (params.out_of_stock_only) qs.set("out_of_stock_only", "true");
    if (params.search) qs.set("search", params.search);
    if (params.location) qs.set("location", params.location);
    return api.get<Page<InventoryWithProduct>>(
      `/admin/inventory?${qs.toString()}`,
    );
  },

  /** Aggregated KPIs */
  stats: () => api.get<InventoryStats>("/admin/inventory/stats"),

  /** Adjust stock via product_id + location */
  adjust: (payload: {
    product_id: number;
    location: string;
    delta: number;
    reason?: string | null;
  }) =>
    api.post<InventoryWithProduct>("/admin/inventory/adjust", payload),

  /** Unresolved low-stock alerts (paginated) */
  listAlerts: (params: { page?: number; size?: number } = {}) => {
    const qs = new URLSearchParams();
    qs.set("page", String(params.page ?? 1));
    qs.set("size", String(params.size ?? 20));
    qs.set("unresolved_only", "true");
    return api.get<Page<InventoryAlert>>(
      `/admin/inventory/alerts?${qs.toString()}`,
    );
  },

  /** Mark alert resolved (idempotent) */
  resolveAlert: (alertId: number) =>
    api.post<InventoryAlert>(`/admin/inventory/alerts/${alertId}/resolve`),

  /** ML-based reorder suggestions */
  reorderSuggestions: (params: ListReorderSuggestionsParams = {}) => {
    const qs = new URLSearchParams();
    if (params.low_stock_only != null) {
      qs.set("low_stock_only", String(params.low_stock_only));
    }
    if (params.lookback_days) qs.set("lookback_days", String(params.lookback_days));
    if (params.limit) qs.set("limit", String(params.limit));
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return api.get<ReorderListResponse>(
      `/admin/inventory/reorder-suggestions${suffix}`,
    );
  },
};
