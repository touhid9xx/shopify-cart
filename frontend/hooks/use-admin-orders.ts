"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { toast } from "sonner";

import { adminOrdersApi } from "@/lib/api/admin-orders";
import { HttpError } from "@/lib/api/client";
import type {
  ListAdminOrdersParams,
  OrderAcceptPayload,
  OrderRejectPayload,
} from "@/lib/api-types";

// ══════════════════════════════════════════════════════════════
// Query keys
// ══════════════════════════════════════════════════════════════
export const adminOrdersKeys = {
  all: ["admin", "orders"] as const,
  list: (params: ListAdminOrdersParams) =>
    ["admin", "orders", "list", params] as const,
  detail: (id: number) => ["admin", "orders", "detail", id] as const,
};

// ══════════════════════════════════════════════════════════════
// Helpers
// ══════════════════════════════════════════════════════════════
function errMsg(err: unknown, fallback: string): string {
  if (err instanceof HttpError) return err.payload?.detail ?? err.message;
  return fallback;
}

// ══════════════════════════════════════════════════════════════
// Queries
// ══════════════════════════════════════════════════════════════
export function useAdminOrders(params: ListAdminOrdersParams = {}) {
  return useQuery({
    queryKey: adminOrdersKeys.list(params),
    queryFn: () => adminOrdersApi.list(params),
    placeholderData: (prev) => prev,
    refetchOnMount: "always",
  });
}

// ══════════════════════════════════════════════════════════════
// Mutations
// ══════════════════════════════════════════════════════════════
function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: adminOrdersKeys.all });
}

export function useAcceptOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      orderId,
      payload,
    }: {
      orderId: number;
      payload?: OrderAcceptPayload;
    }) => adminOrdersApi.accept(orderId, payload ?? {}),
    onSuccess: () => {
      invalidateAll(qc);
      toast.success("Order accepted", {
        description: "The customer will be notified.",
      });
    },
    onError: (err) => toast.error(errMsg(err, "Could not accept order")),
  });
}

export function useRejectOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      orderId,
      payload,
    }: {
      orderId: number;
      payload: OrderRejectPayload;
    }) => adminOrdersApi.reject(orderId, payload),
    onSuccess: () => {
      invalidateAll(qc);
      toast.success("Order rejected", {
        description: "The customer will see your reason.",
      });
    },
    onError: (err) => toast.error(errMsg(err, "Could not reject order")),
  });
}

export function useShipOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (orderId: number) => adminOrdersApi.ship(orderId),
    onSuccess: () => {
      invalidateAll(qc);
      toast.success("Order marked as shipped");
    },
    onError: (err) => toast.error(errMsg(err, "Could not ship order")),
  });
}
