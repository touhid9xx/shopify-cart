"use client";

import { AlertTriangle, CheckCircle2, ExternalLink } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { buttonVariants } from "@/components/ui/button";
import {
  useInventoryAlerts,
  useResolveAlert,
} from "@/hooks/use-admin-inventory";
import { cn } from "@/lib/utils";

export function InventoryAlertsCard() {
  const { data, isLoading } = useInventoryAlerts(1, 5);
  const resolve = useResolveAlert();
  const alerts = data?.items ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <AlertTriangle className="h-5 w-5 text-amber-500" />
          Low-Stock Alerts
        </CardTitle>
        <CardDescription>
          Unresolved alerts triggered when stock crossed the threshold.
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
              No unresolved alerts. All clear! ✨
            </p>
          </div>
        ) : (
          <ul className="space-y-3">
            {alerts.map((alert) => (
              <li
                key={alert.id}
                className="flex items-start justify-between gap-3 rounded-md border p-3"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">
                    Product #{alert.product_id} at{" "}
                    <span className="font-mono">{alert.location}</span>
                  </p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Qty <strong>{alert.quantity}</strong> ≤ threshold{" "}
                    <strong>{alert.threshold}</strong>
                  </p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {new Date(alert.created_at).toLocaleString()}
                  </p>
                </div>
                <div className="flex shrink-0 flex-col gap-1">
                  <Link
                    href={`/dashboard/products/${alert.product_id}/edit`}
                    className={cn(
                      buttonVariants({ variant: "outline", size: "sm" }),
                      "h-7 text-xs",
                    )}
                  >
                    <ExternalLink className="mr-1 h-3 w-3" />
                    View
                  </Link>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-7 text-xs"
                    onClick={() => resolve.mutate(alert.id)}
                    disabled={resolve.isPending}
                  >
                    Resolve
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
