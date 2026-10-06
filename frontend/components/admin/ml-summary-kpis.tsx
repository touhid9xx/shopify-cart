"use client";

import { Brain, CheckCircle2, Sparkles, Target } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { MLSummary } from "@/lib/api-types";

interface Props {
  summary: MLSummary | null | undefined;
  isLoading: boolean;
}

function pct(raw: number): string {
  return `${Math.round(raw * 100)}%`;
}

interface KpiCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon: React.ReactNode;
  tone?: "default" | "success" | "warning";
  isLoading: boolean;
}

function KpiCard({
  title,
  value,
  subtitle,
  icon,
  tone = "default",
  isLoading,
}: KpiCardProps) {
  const toneClass = {
    default: "text-primary",
    success: "text-green-600 dark:text-green-400",
    warning: "text-amber-600 dark:text-amber-400",
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

export function MlSummaryKpis({ summary, isLoading }: Props) {
  const avgConf = summary?.avg_confidence ?? 0;
  const avgTone: KpiCardProps["tone"] =
    avgConf >= 0.85 ? "success" : avgConf >= 0.75 ? "default" : "warning";

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <KpiCard
        title="Total Predictions"
        value={summary ? summary.products_with_ml.toLocaleString() : "—"}
        subtitle={
          summary
            ? `${summary.products_without_ml} without ML metadata`
            : undefined
        }
        icon={<Brain className="h-4 w-4" />}
        isLoading={isLoading}
      />
      <KpiCard
        title="Avg Confidence"
        value={summary ? pct(avgConf) : "—"}
        subtitle={
          summary
            ? `${summary.high_confidence_count} high · ${summary.low_confidence_count} low`
            : undefined
        }
        icon={<Sparkles className="h-4 w-4" />}
        tone={avgTone}
        isLoading={isLoading}
      />
      <KpiCard
        title="Approval Rate"
        value={summary ? pct(summary.approval_rate) : "—"}
        subtitle={
          summary
            ? `${summary.approved_count} approved · ${summary.rejected_count} rejected`
            : undefined
        }
        icon={<CheckCircle2 className="h-4 w-4" />}
        tone={
          summary && summary.approval_rate >= 0.9 ? "success" : "default"
        }
        isLoading={isLoading}
      />
      <KpiCard
        title="Pending Review"
        value={summary ? summary.pending_review_count.toLocaleString() : "—"}
        subtitle={
          summary
            ? `${summary.medium_confidence_count} medium-confidence`
            : undefined
        }
        icon={<Target className="h-4 w-4" />}
        tone={
          summary && summary.pending_review_count > 0 ? "warning" : "default"
        }
        isLoading={isLoading}
      />
    </div>
  );
}
