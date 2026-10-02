"use client";

import { ShoppingBag } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

import { useAuth } from "@/lib/auth-context";
import { useCart } from "@/hooks/use-cart";
import { useCartDrawer } from "@/lib/cart-drawer-context";

export function CartButton() {
  const { isAuthenticated } = useAuth();
  const { data: cart } = useCart(isAuthenticated);
  const { open: openCartDrawer } = useCartDrawer();

  return (
    <Button
      variant="ghost"
      size="icon"
      className="relative"
      aria-label="Open cart"
      onClick={openCartDrawer}
    >
      <ShoppingBag className="h-5 w-5" />
      {cart && cart.item_count > 0 && (
        <Badge
          variant="destructive"
          className="absolute -right-1 -top-1 h-5 min-w-5 justify-center rounded-full px-1 text-xs"
        >
          {cart.item_count}
        </Badge>
      )}
    </Button>
  );
}
