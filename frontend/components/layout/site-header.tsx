"use client";

import Link from "next/link";

import { SiteNav } from "./site-nav";
import { ThemeToggle } from "./theme-toggle";
import { CartButton } from "./cart-button";
import { UserMenu } from "./user-menu";

import { useAuth } from "@/lib/auth-context";

export function SiteHeader() {
  const { isAuthenticated, isAdmin } = useAuth();

  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur">
      <div className="container mx-auto flex h-16 items-center gap-4 px-4">
        {/* Brand */}
        <Link
          href="/"
          className="shrink-0 text-lg font-semibold tracking-tight"
        >
          Shopify Cart
        </Link>

        {/* Center navigation — hidden on mobile */}
        <SiteNav
          isAuthenticated={isAuthenticated}
          isAdmin={isAdmin}
          className="hidden flex-1 justify-center md:flex"
        />

        {/* Right-side actions */}
        <div className="ml-auto flex items-center gap-1">
          <CartButton />
          <ThemeToggle />
          <UserMenu />
        </div>
      </div>

      {/* Mobile navigation — horizontal scroll */}
      <div className="border-t md:hidden">
        <div className="container mx-auto overflow-x-auto px-4">
          <SiteNav
            isAuthenticated={isAuthenticated}
            isAdmin={isAdmin}
            className="flex min-w-max py-2"
          />
        </div>
      </div>
    </header>
  );
}
