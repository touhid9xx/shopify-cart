"use client";

import Link from "next/link";
import { ArrowRight, ShoppingBag } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

import { CartEmpty } from "./cart-empty";
import { CartLine } from "./cart-line";
import { CartSummary } from "./cart-summary";

import { useCart } from "@/hooks/use-cart";
import { useAuth } from "@/lib/auth-context";

export function CartFullView() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { data: cart, isLoading } = useCart(isAuthenticated);
  if (!cart || cart.item_count === 0) {
    return null;
  }
  // ── Loading ──
  if (authLoading || isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Skeleton className="mb-6 h-9 w-48" />
        <div className="grid gap-8 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex gap-4">
                <Skeleton className="h-24 w-24 rounded" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-5 w-3/4" />
                  <Skeleton className="h-4 w-1/3" />
                  <Skeleton className="h-8 w-32" />
                </div>
              </div>
            ))}
          </div>
          <Skeleton className="h-64 rounded" />
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
            <ShoppingBag className="h-8 w-8 text-muted-foreground" />
          </div>
          <h1 className="text-2xl font-bold">Sign in to view your cart</h1>
          <p className="mt-2 text-muted-foreground">
            Your cart is saved to your account.
          </p>
          <Link
            href="/login?next=/cart"
            className={cn(buttonVariants({ size: "lg" }), "mt-6")}
          >
            Sign in
          </Link>
        </div>
      </div>
    );
  }

  // ── Empty cart ──
  const items = cart?.items ?? [];
  if (items.length === 0) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="mb-8 text-3xl font-bold">Your cart</h1>
        <CartEmpty />
      </div>
    );
  }

  // ── Cart with items ──
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Your cart</h1>
        <p className="text-muted-foreground">
          {cart.item_count} item{cart.item_count === 1 ? "" : "s"} in your cart
        </p>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* ── Cart items ── */}
        <div className="lg:col-span-2">
          <div className="rounded-lg border p-4 md:p-6">
            <div className="space-y-6">
              {items.map((item) => (
                <CartLine key={item.id} item={item} />
              ))}
            </div>
          </div>

          <div className="mt-4">
            <Link
              href="/products"
              className={cn(buttonVariants({ variant: "ghost" }))}
            >
              ← Continue shopping
            </Link>
          </div>
        </div>

        {/* ── Summary sidebar ── */}
        <div className="lg:col-span-1">
          <div className="sticky top-24 rounded-lg border p-6">
            <h2 className="text-lg font-semibold">Order summary</h2>
            <Separator className="my-4" />
            <CartSummary cart={cart} showShipping={true} />

            <Link
              href="/checkout"
              className={cn(buttonVariants({ size: "lg" }), "mt-4 w-full")}
            >
              Proceed to checkout
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
