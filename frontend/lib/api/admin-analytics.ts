import { api } from "./client";
import type { DailySales, Page } from "@/lib/api-types";

export const adminAnalyticsApi = {
  sales: (params?: { page?: number; size?: number; day?: string }) => {
    const qs = new URLSearchParams();
    if (params?.page) qs.set("page", String(params.page));
    if (params?.size) qs.set("size", String(params.size));
    if (params?.day) qs.set("day", params.day);
    return api.get<Page<DailySales>>(`/admin/analytics/sales?${qs}`);
  },
};
