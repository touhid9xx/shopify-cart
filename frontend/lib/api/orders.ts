import { api } from "./client";
import type {
  CheckoutPayload,
  Order,
  OrderCancelPayload,
} from "@/lib/api-types";

export const ordersApi = {
  checkout: (payload: CheckoutPayload) =>
    api.post<Order>("/orders/checkout", payload),

  list: () => api.get<Order[]>("/orders"),

  get: (id: number) => api.get<Order>(`/orders/${id}`),

  cancel: (id: number, payload: OrderCancelPayload) =>
    api.post<Order>(`/orders/${id}/cancel`, payload),
};
