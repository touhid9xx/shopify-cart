"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { toast } from "sonner";
import { useRouter } from "next/navigation";

import { ordersApi, type ListOrdersParams } from "@/lib/api/orders";
import { HttpError } from "@/lib/api/client";
import { cartKeys } from "@/hooks/use-cart";
import type {
  CheckoutPayload,
  Order,
  OrderCancelPayload,
} from "@/lib/api-types";

// ──────────────────────────────────────────────────────────────
// Query keys
// ──────────────────────────────────────────────────────────────
export const ordersKeys = {
  all: ["orders"] as const,
  list: (params: ListOrdersParams) => ["orders", "list", params] as const,
  detail: (id: number) => ["orders", "detail", id] as const,
};

// ──────────────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────────────
function extractErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof HttpError) {
    return err.payload?.detail ?? err.message;
  }
  return fallback;
}

// ──────────────────────────────────────────────────────────────
// Queries
// ──────────────────────────────────────────────────────────────
export function useOrders(params: ListOrdersParams = {}, enabled = true) {
  return useQuery({
    queryKey: ordersKeys.list(params),
    queryFn: () => ordersApi.list(params),
    enabled,
    placeholderData: (prev) => prev,
    // Always refetch on mount to avoid stale data after checkout/cancel
    refetchOnMount: "always",
    staleTime: 0,
  });
}

export function useOrder(id: number, enabled = true) {
  return useQuery({
    queryKey: ordersKeys.detail(id),
    queryFn: () => ordersApi.get(id),
    enabled: enabled && Number.isFinite(id) && id > 0,
  });
}

// ──────────────────────────────────────────────────────────────
// Mutations
// ──────────────────────────────────────────────────────────────
export function useCheckout() {
  const qc = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: (payload: CheckoutPayload) => ordersApi.checkout(payload),
    onSuccess: (order: Order) => {
      // ── Cart is now empty on the backend ──
      qc.invalidateQueries({ queryKey: cartKeys.all });

      // ── Orders list changed — force refetch on next mount ──
      qc.invalidateQueries({ queryKey: ordersKeys.all, refetchType: "all" });

      // ── Pre-populate detail cache for the new order ──
      qc.setQueryData(ordersKeys.detail(order.id), order);

      toast.success("Order placed!", {
        description: `Order #${order.id} confirmed.`,
      });

      // Redirect to order detail
      router.push(`/orders/${order.id}`);
    },
    onError: (err) => {
      toast.error(extractErrorMessage(err, "Checkout failed"));
    },
  });
}

export function useCancelOrder() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: number;
      payload?: OrderCancelPayload;
    }) => ordersApi.cancel(id, payload ?? {}),
    onSuccess: (order: Order) => {
      // ── Detail cache — updated order (status = cancelled) ──
      qc.setQueryData(ordersKeys.detail(order.id), order);

      // ── List — refetch all (active or not) ──
      qc.invalidateQueries({ queryKey: ordersKeys.all, refetchType: "all" });

      toast.success("Order cancelled");
    },
    onError: (err) => {
      toast.error(extractErrorMessage(err, "Could not cancel order"));
    },
  });
}
