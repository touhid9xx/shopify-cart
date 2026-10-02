"use client";

import Link from "next/link";
import { ShoppingBag } from "lucide-react";

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

import { CartEmpty } from "./cart-empty";
import { CartLine } from "./cart-line";
import { CartSummary } from "./cart-summary";
import { useCartDrawer } from "@/lib/cart-drawer-context";
import { useCart } from "@/hooks/use-cart";
import { useAuth } from "@/lib/auth-context";

export function CartDrawer() {
  const { isOpen, close } = useCartDrawer();
  const { isAuthenticated } = useAuth();
  const { data: cart, isLoading } = useCart(isAuthenticated);

  const items = cart?.items ?? [];
  const isEmpty = !isLoading && items.length === 0;

  return (
    <Sheet open={isOpen} onOpenChange={(open) => !open && close()}>
      <SheetContent className="flex w-full flex-col sm:max-w-md">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <ShoppingBag className="h-5 w-5" />
            Your cart
            {cart && cart.item_count > 0 && (
              <span className="text-sm font-normal text-muted-foreground">
                ({cart.item_count} item{cart.item_count === 1 ? "" : "s"})
              </span>
            )}
          </SheetTitle>
          <SheetDescription className="sr-only">
            Items currently in your cart
          </SheetDescription>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto py-4">
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2].map((i) => (
                <div key={i} className="flex gap-4">
                  <div className="h-20 w-20 animate-pulse rounded bg-muted" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-3/4 animate-pulse rounded bg-muted" />
                    <div className="h-3 w-1/3 animate-pulse rounded bg-muted" />
                  </div>
                </div>
              ))}
            </div>
          ) : isEmpty ? (
            <CartEmpty />
          ) : (
            <div className="space-y-6">
              {items.map((item) => (
                <CartLine key={item.id} item={item} />
              ))}
            </div>
          )}
        </div>

        {!isEmpty && cart && (
          <>
            <Separator />
            <CartSummary cart={cart} />
            <SheetFooter className="flex-col gap-2 sm:flex-col">
              <Button size="lg" className="w-full">
                <Link href="/checkout" onClick={close}>
                  Checkout
                </Link>
              </Button>
              <Button

                variant="outline"
                className="w-full"
                onClick={close}
              >
                <Link href="/cart">View full cart</Link>
              </Button>
            </SheetFooter>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
