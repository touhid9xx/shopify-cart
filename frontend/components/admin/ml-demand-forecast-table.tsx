"use client";

import {
  ArrowDown,
  ArrowRight,
  ArrowUp,
  AlertTriangle,
  ImageOff,
  TrendingUp,
} from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useDemandForecast } from "@/hooks/use-admin-ml";
import { cn, resolveImageUrl } from "@/lib/utils";
import type { DemandForecastItem, ForecastTrend } from "@/lib/api-types";

const PAGE_SIZE = 15;

function TrendIcon({ trend }: { trend: ForecastTrend }) {
  if (trend === "increasing") {
    return <ArrowUp className="h-3.5 w-3.5 text-green-600 dark:text-green-400" />;
  }
  if (trend === "decreasing") {
    return <ArrowDown className="h-3.5 w-3.5 text-red-600 dark:text-red-400" />;
  }
  return (
    <ArrowRight className="h-3.5 w-3.5 text-muted-foreground" />
  );
}

export function MlDemandForecastTable() {
  const [page, setPage] = useState(1);
  const [onlyLowStock, setOnlyLowStock] = useState(false);

  const { data, isLoading, isFetching } = useDemandForecast({
    page,
    size: PAGE_SIZE,
    only_low_stock: onlyLowStock,
  });

  const items = data?.items ?? [];

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <CardTitle className="flex items-center gap-2 text-lg">
              <TrendingUp className="h-5 w-5 text-primary" />
              Demand Forecast
            </CardTitle>
            <CardDescription>
              Exponential smoothing of last 30 days. Sorted by urgency
              (soonest stockout first).
            </CardDescription>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="low-stock-only"
              checked={onlyLowStock}
              onChange={(e) => {
                setOnlyLowStock(e.target.checked);
                setPage(1);
              }}
              className="h-4 w-4 rounded border-gray-300"
            />
            <Label htmlFor="low-stock-only" className="cursor-pointer text-sm">
              Low stock only
            </Label>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[50px]"></TableHead>
                <TableHead>Product</TableHead>
                <TableHead className="text-right">Stock</TableHead>
                <TableHead className="text-right">Avg/day</TableHead>
                <TableHead className="text-right">7d need</TableHead>
                <TableHead className="text-right">Days left</TableHead>
                <TableHead className="text-center">Trend</TableHead>
              </TableRow>
            </TableHeader>

            <TableBody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell colSpan={7}>
                      <Skeleton className="h-12 w-full" />
                    </TableCell>
                  </TableRow>
                ))
              ) : items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="py-12 text-center">
                    <p className="text-sm text-muted-foreground">
                      No forecast data.
                    </p>
                  </TableCell>
                </TableRow>
              ) : (
                items.map((row) => (
                  <ForecastRow key={row.product_id} row={row} />
                ))
              )}
            </TableBody>
          </Table>
        </div>

        {/* Pagination */}
        {data && data.pages > 1 && (
          <div className="mt-4 flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Page {data.page} of {data.pages} · {data.total} products
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1 || isFetching}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= data.pages || isFetching}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ══════════════════════════════════════════════════════════════
// Row
// ══════════════════════════════════════════════════════════════
function ForecastRow({ row }: { row: DemandForecastItem }) {
  const imageUrl = resolveImageUrl(row.image_url);

  const stockColor =
    row.current_quantity === 0
      ? "text-red-600 dark:text-red-400"
      : row.current_quantity <= row.low_stock_threshold
        ? "text-amber-600 dark:text-amber-400"
        : "text-foreground";

  const daysColor =
    row.will_stockout_7d
      ? "text-red-600 dark:text-red-400 font-semibold"
      : row.days_of_stock !== null && row.days_of_stock < 14
        ? "text-amber-600 dark:text-amber-400"
        : "text-muted-foreground";

  return (
    <TableRow>
      <TableCell>
        <div className="h-9 w-9 overflow-hidden rounded bg-muted">
          {imageUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={imageUrl}
              alt={row.name}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full items-center justify-center">
              <ImageOff className="h-4 w-4 text-muted-foreground" />
            </div>
          )}
        </div>
      </TableCell>

      <TableCell>
        <div className="font-medium">{row.name}</div>
        <div className="font-mono text-xs text-muted-foreground">
          {row.sku}
        </div>
      </TableCell>

      <TableCell className={cn("text-right tabular-nums", stockColor)}>
        {row.current_quantity}
        {row.will_stockout_7d && (
          <AlertTriangle className="ml-1 inline h-3.5 w-3.5 text-red-500" />
        )}
      </TableCell>

      <TableCell className="text-right tabular-nums">
        {row.avg_daily_demand.toFixed(2)}
      </TableCell>

      <TableCell className="text-right tabular-nums">
        {row.forecast_7d}
      </TableCell>

      <TableCell className={cn("text-right tabular-nums", daysColor)}>
        {row.days_of_stock === null
          ? "—"
          : row.days_of_stock === 0
            ? "0"
            : row.days_of_stock.toFixed(1)}
      </TableCell>

      <TableCell className="text-center">
        <div className="flex justify-center">
          <Badge
            variant="outline"
            className="gap-1 px-2 py-0.5 text-xs capitalize"
          >
            <TrendIcon trend={row.trend} />
            {row.trend}
          </Badge>
        </div>
      </TableCell>
    </TableRow>
  );
}
