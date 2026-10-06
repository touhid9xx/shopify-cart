"use client";

import { Brain, RefreshCw } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { MlAnomaliesTable } from "@/components/admin/ml-anomalies-table";
import { MlCategoryBars } from "@/components/admin/ml-category-bars";
import { MlConfidenceChart } from "@/components/admin/ml-confidence-chart";
import { MlDemandForecastTable } from "@/components/admin/ml-demand-forecast-table";
import { MlSummaryKpis } from "@/components/admin/ml-summary-kpis";
import { mlKeys, useMlSummary } from "@/hooks/use-admin-ml";

export default function MlInsightsPage() {
  const qc = useQueryClient();
  const { data: summary, isLoading } = useMlSummary();

  const handleRefresh = () => {
    qc.invalidateQueries({ queryKey: mlKeys.all });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold">
            <Brain className="h-6 w-6 text-primary" />
            ML Insights
          </h1>
          <p className="text-sm text-muted-foreground">
            Model health, demand forecasting, and anomaly detection.
          </p>
        </div>
        <Button variant="outline" onClick={handleRefresh}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Section 1 — Summary */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Insights Summary</h2>
        <MlSummaryKpis summary={summary} isLoading={isLoading} />
        <div className="grid gap-6 lg:grid-cols-2">
          <MlConfidenceChart
            buckets={summary?.confidence_buckets ?? []}
            isLoading={isLoading}
          />
          <MlCategoryBars
            categories={summary?.category_distribution ?? []}
            isLoading={isLoading}
          />
        </div>
      </section>

      {/* Section 2 — Demand Forecast */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Demand Forecasting</h2>
        <MlDemandForecastTable />
      </section>

      {/* Section 3 — Anomalies */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Anomaly Detection</h2>
        <MlAnomaliesTable />
      </section>
    </div>
  );
}
