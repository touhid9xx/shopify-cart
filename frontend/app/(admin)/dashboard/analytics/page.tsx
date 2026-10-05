"use client";

import { RefreshCw } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { AnalyticsKpis } from "@/components/admin/analytics-kpis";
import { RecentAlertsCard } from "@/components/admin/recent-alerts-card";
import { SalesTrendChart } from "@/components/admin/sales-trend-chart";
import { TopProductsChart } from "@/components/admin/top-products-chart";
import {
  analyticsKeys,
  useAnalyticsDashboard,
} from "@/hooks/use-admin-analytics";

export default function AnalyticsPage() {
  const qc = useQueryClient();
  const { summary, timeSeries, topProducts, isLoading } = useAnalyticsDashboard({
    size: 100,
  });

  const handleRefresh = () => {
    qc.invalidateQueries({ queryKey: analyticsKeys.all });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Analytics</h1>
          <p className="text-sm text-muted-foreground">
            Sales performance across products and time.
          </p>
        </div>
        <Button variant="outline" onClick={handleRefresh}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* KPIs */}
      <AnalyticsKpis summary={summary} isLoading={isLoading} />

      {/* Charts */}
      <div className="grid gap-6 lg:grid-cols-2">
        <SalesTrendChart points={timeSeries} isLoading={isLoading} />
        <TopProductsChart products={topProducts} isLoading={isLoading} />
      </div>

      {/* Alerts */}
      <RecentAlertsCard />
    </div>
  );
}
