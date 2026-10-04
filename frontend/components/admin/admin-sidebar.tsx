"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  CheckCircle2,
  LayoutDashboard,
  Package,
  ShoppingCart,
  Sparkles,
  TrendingUp,
  Upload,
} from "lucide-react";

import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
  badge?: "review";
}

const NAV_ITEMS: NavItem[] = [
  {
    href: "/dashboard",
    label: "Dashboard",
    icon: <LayoutDashboard className="h-4 w-4" />,
  },
  {
    href: "/dashboard/products/review",
    label: "Review Queue",
    icon: <CheckCircle2 className="h-4 w-4" />,
    badge: "review",
  },
  {
    href: "/dashboard/products",
    label: "Products",
    icon: <Package className="h-4 w-4" />,
  },
  {
    href: "/dashboard/products/new",
    label: "Upload product",
    icon: <Upload className="h-4 w-4" />,
  },
  {
    href: "/dashboard/inventory",
    label: "Inventory",
    icon: <TrendingUp className="h-4 w-4" />,
  },
  {
    href: "/dashboard/orders",
    label: "Orders",
    icon: <ShoppingCart className="h-4 w-4" />,
  },
  {
    href: "/dashboard/analytics",
    label: "Analytics",
    icon: <BarChart3 className="h-4 w-4" />,
  },
  {
    href: "/dashboard/ml",
    label: "ML insights",
    icon: <Sparkles className="h-4 w-4" />,
  },
];

export function AdminSidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-56 shrink-0 border-r bg-muted/20 md:block">
      <div className="sticky top-16 flex flex-col gap-1 p-4">
        <div className="mb-2 px-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Admin
        </div>
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname === item.href ||
                pathname.startsWith(`${item.href}/`);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
              )}
            >
              {item.icon}
              {item.label}
            </Link>
          );
        })}
      </div>
    </aside>
  );
}
