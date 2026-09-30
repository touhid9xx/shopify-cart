import { api } from "./client";
import type {
  Cart,
  CartItemAddPayload,
  CartItemUpdatePayload,
} from "@/lib/api-types";

export const cartApi = {
  get: () => api.get<Cart>("/cart"),

  addItem: (payload: CartItemAddPayload) =>
    api.post<Cart>("/cart/items", payload),

  updateItem: (itemId: number, payload: CartItemUpdatePayload) =>
    api.patch<Cart>(`/cart/items/${itemId}`, payload),

  removeItem: (itemId: number) =>
    api.delete<Cart>(`/cart/items/${itemId}`),

  clear: () => api.delete<Cart>("/cart"),
};
