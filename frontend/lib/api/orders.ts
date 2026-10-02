import { api } from "./client";
import type {
  CheckoutPayload,
  Order,
  OrderCancelPayload,
  Page,
} from "@/lib/api-types";

export interface ListOrdersParams {
  page?: number;
  size?: number;
  status?: string;
}

export const ordersApi = {
  checkout: (payload: CheckoutPayload) =>
    api.post<Order>("/orders/checkout", payload),

  list: async (params: ListOrdersParams = {}): Promise<Page<Order>> => {
    const qs = new URLSearchParams();
    if (params.page) qs.set("page", String(params.page));
    if (params.size) qs.set("size", String(params.size));
    if (params.status) qs.set("status", params.status);
    const suffix = qs.toString() ? `?${qs.toString()}` : "";

    const raw = await api.get<unknown>(`/orders${suffix}`);
    return normalizeOrdersPage(raw, params);
  },

  get: (id: number) => api.get<Order>(`/orders/${id}`),

  cancel: (id: number, payload: OrderCancelPayload = {}) =>
    api.post<Order>(`/orders/${id}/cancel`, payload),
};

// ──────────────────────────────────────────────────────────────
// Normalizer — handles all known shapes
// ──────────────────────────────────────────────────────────────
function normalizeOrdersPage(
  raw: unknown,
  params: ListOrdersParams = {},
): Page<Order> {
  const page = params.page ?? 1;
  const size = params.size ?? 20;

  // Shape (a): bare array
  if (Array.isArray(raw)) {
    return {
      items: raw as Order[],
      total: raw.length,
      page,
      size: raw.length,
      pages: 1,
    };
  }

  // Shape (b): paginated object { items, total, page, size, pages }
  if (raw && typeof raw === "object" && "items" in raw) {
    return raw as Page<Order>;
  }

  // Shape (c): .NET / ASP.NET Core style { value, Count }
  if (raw && typeof raw === "object" && "value" in raw) {
    const obj = raw as { value: unknown; Count?: number; count?: number };
    const items = Array.isArray(obj.value) ? (obj.value as Order[]) : [];
    const total = obj.Count ?? obj.count ?? items.length;
    return {
      items,
      total,
      page,
      size,
      pages: size > 0 ? Math.ceil(total / size) : 1,
    };
  }

  // Shape (d): unknown → empty
  return { items: [], total: 0, page, size, pages: 0 };
}
