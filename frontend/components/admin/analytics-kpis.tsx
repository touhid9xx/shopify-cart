"use client";

import {
  DollarSign,
  Package,
  ShoppingCart,
  TrendingUp,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { fmtCurrency, fmtNumber } from "@/lib/analytics-utils";
import type { AnalyticsSummary } from "@/lib/api-types";
import { cn } from "@/lib/utils";

interface Props {
  summary: AnalyticsSummary | null;
  isLoading: boolean;
}

interface KpiCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon: React.ReactNode;
  isLoading: boolean;
}

function KpiCard({ title, value, subtitle, icon, isLoading }: KpiCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <div className="h-4 w-4 text-primary">{icon}</div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-8 w-24" />
        ) : (
          <>
            <p className="text-2xl font-bold tabular-nums">{value}</p>
            {subtitle && (
              <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

export function AnalyticsKpis({ summary, isLoading }: Props) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <KpiCard
        title="Total Revenue"
        value={summary ? fmtCurrency(summary.total_revenue) : "—"}
        subtitle={summary ? `across ${summary.day_count} day(s)` : undefined}
        icon={<DollarSign className="h-4 w-4" />}
        isLoading={isLoading}
      />
      <KpiCard
        title="Total Orders"
        value={summary ? fmtNumber(summary.total_orders) : "—"}
        subtitle={
          summary ? `from ${summary.distinct_products} product(s)` : undefined
        }
        icon={<ShoppingCart className="h-4 w-4" />}
        isLoading={isLoading}
      />
      <KpiCard
        title="Units Sold"
        value={summary ? fmtNumber(summary.total_units) : "—"}
        icon={<Package className="h-4 w-4" />}
        isLoading={isLoading}
      />
      <KpiCard
        title="Avg Order Value"
        value={summary ? fmtCurrency(summary.avg_order_value) : "—"}
        subtitle="revenue / orders"
        icon={<TrendingUp className="h-4 w-4" />}
        isLoading={isLoading}
      />
    </div>
  );
}
