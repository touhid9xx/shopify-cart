"use client";

import { AlertTriangle, DollarSign, Package, XCircle } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useInventoryStats } from "@/hooks/use-admin-inventory";
import { cn } from "@/lib/utils";

function fmtNumber(n: number): string {
  return new Intl.NumberFormat().format(n);
}

function fmtMoney(raw: string): string {
  const n = Number(raw);
  if (Number.isNaN(n)) return "$0.00";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(n);
}

interface KpiCardProps {
  title: string;
  value: string;
  icon: React.ReactNode;
  tone?: "default" | "warning" | "danger";
  isLoading?: boolean;
}

function KpiCard({ title, value, icon, tone = "default", isLoading }: KpiCardProps) {
  const toneClass = {
    default: "text-primary",
    warning: "text-amber-600 dark:text-amber-400",
    danger: "text-red-600 dark:text-red-400",
  }[tone];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <div className={cn("h-4 w-4", toneClass)}>{icon}</div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-8 w-24" />
        ) : (
          <p className="text-2xl font-bold tabular-nums">{value}</p>
        )}
      </CardContent>
    </Card>
  );
}

export function InventoryKpis() {
  const { data, isLoading } = useInventoryStats();

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <KpiCard
        title="Total SKUs"
        value={data ? fmtNumber(data.total_skus) : "—"}
        icon={<Package className="h-4 w-4" />}
        isLoading={isLoading}
      />
      <KpiCard
        title="Total Units"
        value={data ? fmtNumber(data.total_units) : "—"}
        icon={<Package className="h-4 w-4" />}
        isLoading={isLoading}
      />
      <KpiCard
        title="Low Stock"
        value={data ? fmtNumber(data.low_stock_count) : "—"}
        icon={<AlertTriangle className="h-4 w-4" />}
        tone={data && data.low_stock_count > 0 ? "warning" : "default"}
        isLoading={isLoading}
      />
      <KpiCard
        title="Out of Stock"
        value={data ? fmtNumber(data.out_of_stock_count) : "—"}
        icon={<XCircle className="h-4 w-4" />}
        tone={data && data.out_of_stock_count > 0 ? "danger" : "default"}
        isLoading={isLoading}
      />
      {/* Optional 5th card — full width on mobile, part of grid on desktop */}
      <Card className="sm:col-span-2 lg:col-span-4">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Total Inventory Value
          </CardTitle>
          <DollarSign className="h-4 w-4 text-primary" />
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-8 w-40" />
          ) : (
            <p className="text-2xl font-bold tabular-nums">
              {data ? fmtMoney(data.total_inventory_value) : "—"}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
