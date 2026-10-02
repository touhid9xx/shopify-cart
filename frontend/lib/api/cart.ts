import { api } from "./client";
import type {
  CartItemAddPayload,
  CartItemUpdatePayload,
  CartWithProducts,
} from "@/lib/api-types";

export const cartApi = {
  get: () => api.get<CartWithProducts>("/cart"),

  addItem: (payload: CartItemAddPayload) =>
    api.post<CartWithProducts>("/cart/items", payload),

  updateItem: (itemId: number, payload: CartItemUpdatePayload) =>
    api.patch<CartWithProducts>(`/cart/items/${itemId}`, payload),

  removeItem: (itemId: number) =>
    api.delete<CartWithProducts>(`/cart/items/${itemId}`),

  clear: () => api.delete<CartWithProducts>("/cart"),
};
