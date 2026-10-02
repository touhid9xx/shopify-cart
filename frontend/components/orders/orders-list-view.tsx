"use client";

import Link from "next/link";
import { Package } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

import { OrderCard } from "./order-card";

import { useOrders } from "@/hooks/use-orders";
import { useAuth } from "@/lib/auth-context";
import { cn } from "@/lib/utils";

export function OrdersListView() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { data, isLoading } = useOrders({ page: 1, size: 20 }, isAuthenticated);

  // ── Loading ──
  if (authLoading || isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Skeleton className="mb-6 h-9 w-40" />
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-28 w-full rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  // ── Not logged in ──
  if (!isAuthenticated) {
    return (
      <div className="container mx-auto px-4 py-16 text-center">
        <div className="mx-auto max-w-md">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-muted">
            <Package className="h-8 w-8 text-muted-foreground" />
          </div>
          <h1 className="text-2xl font-bold">Sign in to see your orders</h1>
          <p className="mt-2 text-muted-foreground">
            Your order history is tied to your account.
          </p>
          <Link
            href="/login?next=/orders"
            className={cn(buttonVariants({ size: "lg" }), "mt-6")}
          >
            Sign in
          </Link>
        </div>
      </div>
    );
  }

  const orders = data?.items ?? [];
  const total = data?.total ?? 0;

  // ── Empty ──
  if (orders.length === 0) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="mb-8 text-3xl font-bold">Your orders</h1>
        <div className="rounded-lg border border-dashed p-12 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-muted">
            <Package className="h-7 w-7 text-muted-foreground" />
          </div>
          <h2 className="text-lg font-semibold">No orders yet</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            When you place your first order, it will show up here.
          </p>
          <Link
            href="/products"
            className={cn(buttonVariants({ size: "lg" }), "mt-6")}
          >
            Start shopping
          </Link>
        </div>
      </div>
    );
  }

  // ── List ──
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Your orders</h1>
        <p className="mt-2 text-muted-foreground">
          {total} order{total === 1 ? "" : "s"} total
        </p>
      </div>

      <div className="space-y-4">
        {orders.map((order) => (
          <OrderCard key={order.id} order={order} />
        ))}
      </div>
    </div>
  );
}
