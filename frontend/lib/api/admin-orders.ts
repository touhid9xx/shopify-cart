import { api } from "./client";
import type {
  ListAdminOrdersParams,
  OrderAcceptPayload,
  OrderReadAdmin,
  OrderRejectPayload,
  Page,
} from "@/lib/api-types";

export const adminOrdersApi = {
  /**
   * List ALL orders (admin view) — optional status filter.
   * Includes admin_message, reviewed_by, reviewed_at fields.
   */
  list: (params: ListAdminOrdersParams = {}) => {
    const qs = new URLSearchParams();
    if (params.page) qs.set("page", String(params.page));
    if (params.size) qs.set("size", String(params.size));
    if (params.status) qs.set("status", params.status);
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return api.get<Page<OrderReadAdmin>>(`/admin/orders${suffix}`);
  },

  /**
   * Accept a PENDING order → CONFIRMED.
   * Optional notes stored in admin_message.
   */
  accept: (orderId: number, payload: OrderAcceptPayload = {}) =>
    api.post<OrderReadAdmin>(`/admin/orders/${orderId}/accept`, payload),

  /**
   * Reject a PENDING or CONFIRMED order → REJECTED.
   * Required reason stored in admin_message.
   */
  reject: (orderId: number, payload: OrderRejectPayload) =>
    api.post<OrderReadAdmin>(`/admin/orders/${orderId}/reject`, payload),

  /**
   * Mark a CONFIRMED order as SHIPPED.
   */
  ship: (orderId: number) =>
    api.post<OrderReadAdmin>(`/admin/orders/${orderId}/ship`, {}),

  /**
   * Generic status update (low-level — prefer accept/reject/ship).
   */
  updateStatus: (orderId: number, payload: { status: string; reason?: string }) =>
    api.patch<OrderReadAdmin>(`/admin/orders/${orderId}/status`, payload),
};
