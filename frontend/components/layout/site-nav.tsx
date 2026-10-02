"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  authOnly?: boolean;
  adminOnly?: boolean;   // ← NEW
}

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Home" },
  { href: "/products", label: "Products" },
  { href: "/orders", label: "Orders", authOnly: true },
  { href: "/dashboard", label: "Dashboard", adminOnly: true },   // ← CHANGED
];

interface Props {
  isAuthenticated?: boolean;
  isAdmin?: boolean;
  className?: string;
  onNavigate?: () => void;
}

export function SiteNav({
  isAuthenticated = false,
  isAdmin = false,
  className,
  onNavigate,
}: Props) {
  const pathname = usePathname();

  // ── Filter by auth + admin rules ──
  const items = NAV_ITEMS.filter((item) => {
    if (item.adminOnly && !isAdmin) return false;
    if (item.authOnly && !isAuthenticated) return false;
    return true;
  });

  return (
    <nav className={cn("flex items-center gap-1", className)}>
      {items.map((item) => {
        const isActive =
          item.href === "/"
            ? pathname === "/"
            : pathname === item.href ||
              pathname.startsWith(`${item.href}/`);

        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            className={cn(
              "rounded-md px-3 py-2 text-sm font-medium transition-colors",
              isActive
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
            )}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
