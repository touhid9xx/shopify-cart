import { api } from "./client";
import type {
  Order,
  OrderStatus,
  OrderStatusUpdatePayload,
  Page,
} from "@/lib/api-types";

export const adminOrdersApi = {
  list: (params?: { page?: number; size?: number; status?: OrderStatus }) => {
    const qs = new URLSearchParams();
    if (params?.page) qs.set("page", String(params.page));
    if (params?.size) qs.set("size", String(params.size));
    if (params?.status) qs.set("status", params.status);
    return api.get<Page<Order>>(`/admin/orders?${qs}`);
  },

  changeStatus: (id: number, payload: OrderStatusUpdatePayload) =>
    api.patch<Order>(`/admin/orders/${id}/status`, payload),
};
