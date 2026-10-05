"use client";

import { AlertTriangle, CheckCircle2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useAnalyticsAlerts,
  useResolveAnalyticsAlert,
} from "@/hooks/use-admin-analytics";

export function RecentAlertsCard() {
  const { data, isLoading } = useAnalyticsAlerts(1, 10);
  const resolve = useResolveAnalyticsAlert();
  const alerts = data?.items ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <AlertTriangle className="h-5 w-5 text-amber-500" />
          Recent Alerts
        </CardTitle>
        <CardDescription>
          Unresolved inventory alerts from the last period.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-14 w-full" />
            ))}
          </div>
        ) : alerts.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-6 text-center">
            <CheckCircle2 className="h-8 w-8 text-green-500" />
            <p className="text-sm text-muted-foreground">
              No unresolved alerts. System healthy ✨
            </p>
          </div>
        ) : (
          <ul className="space-y-2">
            {alerts.map((alert) => (
              <li
                key={alert.id}
                className="flex items-center justify-between gap-3 rounded-md border p-3"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">
                    Product #{alert.product_id}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    qty {alert.quantity} ≤ {alert.threshold} · {alert.location}
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-7 shrink-0 text-xs"
                  onClick={() => resolve.mutate(alert.id)}
                  disabled={resolve.isPending}
                >
                  Resolve
                </Button>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
