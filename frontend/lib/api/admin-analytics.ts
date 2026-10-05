import { api } from "./client";
import type {
  AnalyticsAlertRead,
  DailySalesRead,
  ListDailySalesParams,
  Page,
} from "@/lib/api-types";

export const adminAnalyticsApi = {
  /**
   * List daily sales rows (paginated).
   *
   * Default `size=100` — the dashboard needs a wider window than the
   * standard page size. Client-side aggregation groups by date.
   */
  listSales: (params: ListDailySalesParams = {}) => {
    const qs = new URLSearchParams();
    qs.set("page", String(params.page ?? 1));
    qs.set("size", String(params.size ?? 100));
    if (params.day) qs.set("day", params.day);
    return api.get<Page<DailySalesRead>>(`/admin/analytics/sales?${qs}`);
  },

  /** Unresolved alerts (paginated) */
  listAlerts: (params: { page?: number; size?: number } = {}) => {
    const qs = new URLSearchParams();
    qs.set("page", String(params.page ?? 1));
    qs.set("size", String(params.size ?? 20));
    qs.set("unresolved_only", "true");
    return api.get<Page<AnalyticsAlertRead>>(
      `/admin/analytics/alerts?${qs.toString()}`,
    );
  },

  /** Resolve alert (reuses backend idempotent endpoint) */
  resolveAlert: (alertId: number) =>
    api.post<AnalyticsAlertRead>(
      `/admin/analytics/alerts/${alertId}/resolve`,
    ),
};
