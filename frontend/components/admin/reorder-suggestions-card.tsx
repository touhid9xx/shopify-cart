"use client";

import { Package, Sparkles, TrendingUp } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useReorderSuggestions } from "@/hooks/use-admin-inventory";

export function ReorderSuggestionsCard() {
  const { data, isLoading } = useReorderSuggestions({
    low_stock_only: true,
    limit: 5,
  });
  const items = data?.items ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Sparkles className="h-5 w-5 text-primary" />
          Reorder Suggestions
        </CardTitle>
        <CardDescription>
          ML-based reorder quantities using a 30-day moving average of
          demand.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-20 w-full" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-6 text-center">
            <Package className="h-8 w-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              No reorders needed right now.
            </p>
          </div>
        ) : (
          <ul className="space-y-3">
            {items.map((s) => (
              <li
                key={`${s.product_id}-${s.location}`}
                className="rounded-md border p-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{s.name}</p>
                    <p className="mt-0.5 font-mono text-xs text-muted-foreground">
                      {s.sku} · {s.location}
                    </p>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="text-lg font-bold tabular-nums text-primary">
                      {s.suggested_reorder_qty}
                    </p>
                    <p className="text-xs text-muted-foreground">units</p>
                  </div>
                </div>

                <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
                  <div>
                    <p className="text-muted-foreground">Current</p>
                    <p className="font-medium tabular-nums">
                      {s.current_quantity}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Avg daily</p>
                    <p className="font-medium tabular-nums">
                      {s.avg_daily_demand.toFixed(2)}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Target</p>
                    <p className="font-medium tabular-nums">{s.target_stock}</p>
                  </div>
                </div>

                <p className="mt-2 flex items-start gap-1 text-xs text-muted-foreground">
                  <TrendingUp className="mt-0.5 h-3 w-3 shrink-0" />
                  {s.reason}
                </p>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
