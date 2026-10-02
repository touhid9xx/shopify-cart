"use client";

import { ImageOff } from "lucide-react";

import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";

import type { CartWithProducts } from "@/lib/api-types";
import { formatMoney } from "@/lib/formatters";
import { resolveImageUrl } from "@/lib/utils";
import { useCart } from "@/hooks/use-cart";
import { useAuth } from "@/lib/auth-context";

/**
 * Read-only cart summary for the checkout page.
 * Shows items, subtotal, shipping, tax, total.
 */
export function OrderSummary() {
  const { isAuthenticated } = useAuth();
  const { data: cart, isLoading } = useCart(isAuthenticated);

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2].map((i) => (
          <div key={i} className="flex gap-3">
            <Skeleton className="h-16 w-16 rounded" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-1/3" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!cart || cart.items.length === 0) {
    return (
      <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
        Your cart is empty.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* ── Items ── */}
      <ul className="space-y-4">
        {cart.items.map((item) => {
          const imageUrl = resolveImageUrl(item.product.image_url);
          return (
            <li key={item.id} className="flex gap-3">
              <div className="relative h-16 w-16 flex-shrink-0 overflow-hidden rounded bg-muted">
                {imageUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={imageUrl}
                    alt={item.product.name}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <div className="flex h-full items-center justify-center">
                    <ImageOff className="h-5 w-5 text-muted-foreground" />
                  </div>
                )}
                <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1 text-xs font-semibold text-primary-foreground">
                  {item.quantity}
                </span>
              </div>
              <div className="flex flex-1 flex-col justify-center">
                <p className="line-clamp-1 text-sm font-medium">
                  {item.product.name}
                </p>
                <p className="text-xs text-muted-foreground">
                  {formatMoney(item.unit_price)} each
                </p>
              </div>
              <div className="flex items-center text-sm font-medium tabular-nums">
                {formatMoney(item.subtotal)}
              </div>
            </li>
          );
        })}
      </ul>

      <Separator />

      {/* ── Totals ── */}
      <div className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-muted-foreground">
            Subtotal ({cart.total_quantity} item
            {cart.total_quantity === 1 ? "" : "s"})
          </span>
          <span>{formatMoney(cart.total_amount)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Shipping</span>
          <span>Free</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Tax</span>
          <span>{formatMoney("0.00")}</span>
        </div>
      </div>

      <Separator />

      <div className="flex justify-between text-base font-semibold">
        <span>Total</span>
        <span className="tabular-nums">{formatMoney(cart.total_amount)}</span>
      </div>
    </div>
  );
}
