import { api } from "./client";
import type {
  InventoryAlert,
  InventoryAdjustPayload,
  InventoryItem,
  Page,
  ReorderListResponse,
} from "@/lib/api-types";

export const adminInventoryApi = {
  // alerts
  listAlerts: (params?: { page?: number; size?: number; unresolved_only?: boolean }) => {
    const qs = new URLSearchParams();
    if (params?.page) qs.set("page", String(params.page));
    if (params?.size) qs.set("size", String(params.size));
    if (params?.unresolved_only !== undefined)
      qs.set("unresolved_only", String(params.unresolved_only));
    return api.get<Page<InventoryAlert>>(`/admin/inventory/alerts?${qs}`);
  },

  resolveAlert: (id: number) =>
    api.post<InventoryAlert>(`/admin/inventory/alerts/${id}/resolve`),

  // reorder
  reorderSuggestions: (params?: {
    low_stock_only?: boolean;
    lookback_days?: number;
    limit?: number;
  }) => {
    const qs = new URLSearchParams();
    if (params?.low_stock_only !== undefined)
      qs.set("low_stock_only", String(params.low_stock_only));
    if (params?.lookback_days) qs.set("lookback_days", String(params.lookback_days));
    if (params?.limit) qs.set("limit", String(params.limit));
    return api.get<ReorderListResponse>(
      `/admin/inventory/reorder-suggestions?${qs}`
    );
  },

  // inventory read / adjust (non-admin read endpoint, admin write)
  listForProduct: (productId: number) =>
    api.get<InventoryItem[]>(`/inventory/product/${productId}`),

  adjust: (inventoryId: number, payload: InventoryAdjustPayload) =>
    api.patch<InventoryItem>(`/inventory/${inventoryId}/adjust`, payload),
};
