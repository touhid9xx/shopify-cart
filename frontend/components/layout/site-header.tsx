"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  LogOut,
  ShoppingBag,
  User as UserIcon,
  LayoutDashboard,
} from "lucide-react";

import { Button, buttonVariants } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

import { useAuth } from "@/lib/auth-context";
import { useCart } from "@/hooks/use-cart";
import { useCartDrawer } from "@/lib/cart-drawer-context";

export function SiteHeader() {
  const router = useRouter();
  const { user, isAuthenticated, isAdmin, logout } = useAuth();
  const { data: cart } = useCart(isAuthenticated);
  const { open: openCartDrawer } = useCartDrawer();

  return (
    <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur">
      <div className="container mx-auto flex h-16 items-center justify-between px-4">
        <Link href="/products" className="text-lg font-semibold">
          Shopify Cart
        </Link>

        <nav className="flex items-center gap-2">
          {/* Products — no Button wrapper */}
          <Link
            href="/products"
            className={cn(buttonVariants({ variant: "ghost", size: "sm" }))}
          >
            Products
          </Link>

          {isAuthenticated && (
            <Link
              href="/orders"
              className={cn(buttonVariants({ variant: "ghost", size: "sm" }))}
            >
              Orders
            </Link>
          )}

          {isAdmin && (
            <Link
              href="/dashboard"
              className={cn(buttonVariants({ variant: "ghost", size: "sm" }))}
            >
              <LayoutDashboard className="mr-2 h-4 w-4" />
              Admin
            </Link>
          )}

          {/* Cart drawer trigger — a real Button, not a Link */}
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

          <ThemeToggle />

          {isAuthenticated ? (
            <DropdownMenu>
              {/* Base UI: Trigger is already a button — no asChild */}
              <DropdownMenuTrigger
                className={cn(
                  buttonVariants({ variant: "ghost", size: "icon" }),
                )}
                aria-label="Account"
              >
                <UserIcon className="h-5 w-5" />
              </DropdownMenuTrigger>

              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuGroup>
                  <DropdownMenuLabel className="truncate">
                    {user?.email}
                  </DropdownMenuLabel>
                </DropdownMenuGroup>
                <DropdownMenuSeparator />

                {/* Use onClick — safest across Base UI versions */}
                <DropdownMenuItem onClick={() => router.push("/orders")}>
                  My orders
                </DropdownMenuItem>
                <DropdownMenuItem onClick={logout}>
                  <LogOut className="mr-2 h-4 w-4" />
                  Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Link
              href="/login"
              className={cn(buttonVariants({ size: "sm" }))}
            >
              Sign in
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
