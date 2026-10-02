"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { cartApi } from "@/lib/api/cart";
import { HttpError } from "@/lib/api/client";
import type { CartWithProducts } from "@/lib/api-types";

export const cartKeys = {
  all: ["cart"] as const,
};

// ──────────────────────────────────────────────────────────────
// Queries
// ──────────────────────────────────────────────────────────────
export function useCart(enabled = true) {
  return useQuery({
    queryKey: cartKeys.all,
    queryFn: () => cartApi.get(),
    enabled,
  });
}

// ──────────────────────────────────────────────────────────────
// Mutations
// ──────────────────────────────────────────────────────────────
export function useAddToCart() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: cartApi.addItem,
    onSuccess: (cart: CartWithProducts) => {
      qc.setQueryData(cartKeys.all, cart);
      toast.success("Added to cart");
    },
    onError: (err) => {
      const msg =
        err instanceof HttpError
          ? err.payload?.detail ?? err.message
          : "Could not add to cart";
      toast.error(msg);
    },
  });
}

export function useUpdateCartItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, quantity }: { id: number; quantity: number }) =>
      cartApi.updateItem(id, { quantity }),
    onSuccess: (cart: CartWithProducts) => {
      qc.setQueryData(cartKeys.all, cart);
    },
    onError: (err) => {
      const msg =
        err instanceof HttpError
          ? err.payload?.detail ?? err.message
          : "Could not update item";
      toast.error(msg);
    },
  });
}

export function useRemoveCartItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => cartApi.removeItem(id),
    onSuccess: (cart: CartWithProducts) => {
      qc.setQueryData(cartKeys.all, cart);
      toast.success("Removed");
    },
    onError: (err) => {
      const msg =
        err instanceof HttpError
          ? err.payload?.detail ?? err.message
          : "Could not remove item";
      toast.error(msg);
    },
  });
}

export function useClearCart() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => cartApi.clear(),
    onSuccess: (cart: CartWithProducts) => {
      qc.setQueryData(cartKeys.all, cart);
      toast.success("Cart cleared");
    },
    onError: (err) => {
      const msg =
        err instanceof HttpError
          ? err.payload?.detail ?? err.message
          : "Could not clear cart";
      toast.error(msg);
    },
  });
}
