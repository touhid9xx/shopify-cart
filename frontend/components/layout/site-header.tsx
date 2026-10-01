"use client";

import Link from "next/link";
import { LogOut, ShoppingBag, User as UserIcon, LayoutDashboard } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { Badge } from "@/components/ui/badge";

import { useAuth } from "@/lib/auth-context";
import { useCart } from "@/hooks/use-cart";

export function SiteHeader() {
  const { user, isAuthenticated, isAdmin, logout } = useAuth();
  const { data: cart } = useCart(isAuthenticated);

  return (
    <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur">
      <div className="container mx-auto flex h-16 items-center justify-between px-4">
        <Link href="/products" className="text-lg font-semibold">
          Shopify Cart
        </Link>

        <nav className="flex items-center gap-2">
          <Button  variant="ghost" size="sm">
            <Link href="/products">Products</Link>
          </Button>

          {isAuthenticated && (
            <Button  variant="ghost" size="sm">
              <Link href="/orders">Orders</Link>
            </Button>
          )}

          {isAdmin && (
            <Button  variant="ghost" size="sm">
              <Link href="/dashboard">
                <LayoutDashboard className="mr-2 h-4 w-4" />
                Admin
              </Link>
            </Button>
          )}

          <Button  variant="ghost" size="icon" className="relative" aria-label="Cart">
            <Link href="/cart">
              <ShoppingBag className="h-5 w-5" />
              {cart && cart.item_count > 0 && (
                <Badge
                  variant="destructive"
                  className="absolute -right-1 -top-1 h-5 min-w-5 justify-center rounded-full px-1 text-xs"
                >
                  {cart.item_count}
                </Badge>
              )}
            </Link>
          </Button>

          <ThemeToggle />

          {isAuthenticated ? (
            <DropdownMenu>
              <DropdownMenuTrigger>
                <Button variant="ghost" size="icon" aria-label="Account">
                  <UserIcon className="h-5 w-5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuLabel className="truncate">
                  {user?.email}
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem>
                  <Link href="/orders">My orders</Link>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={logout}>
                  <LogOut className="mr-2 h-4 w-4" />
                  Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Button size="sm">
              <Link href="/login">Sign in</Link>
            </Button>
          )}
        </nav>
      </div>
    </header>
  );
}
