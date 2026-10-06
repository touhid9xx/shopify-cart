"use client";

import {
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  ImageOff,
  Activity,
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
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAnomalies } from "@/hooks/use-admin-ml";
import { cn, resolveImageUrl } from "@/lib/utils";
import type { AnomalyItem, AnomalySeverity } from "@/lib/api-types";

const PAGE_SIZE = 15;

function severityBadge(s: AnomalySeverity) {
  const styles = {
    high: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
    medium:
      "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400",
    low: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
  }[s];
  return (
    <span
      className={cn(
        "rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize",
        styles,
      )}
    >
      {s}
    </span>
  );
}

function fmtDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  if (!y || !m || !d) return iso;
  return new Date(y, m - 1, d).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function MlAnomaliesTable() {
  const [page, setPage] = useState(1);
  const [zThreshold, setZThreshold] = useState(2.0);

  const { data, isLoading, isFetching } = useAnomalies({
    page,
    size: PAGE_SIZE,
    z_threshold: zThreshold,
  });

  const items = data?.items ?? [];

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Activity className="h-5 w-5 text-primary" />
              Sales Anomalies
            </CardTitle>
            <CardDescription>
              Days where sales deviated from rolling 7-day baseline by more
              than {zThreshold}σ.
            </CardDescription>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant={zThreshold === 2.0 ? "default" : "outline"}
              size="sm"
              onClick={() => {
                setZThreshold(2.0);
                setPage(1);
              }}
            >
              All (2σ)
            </Button>
            <Button
              variant={zThreshold === 2.5 ? "default" : "outline"}
              size="sm"
              onClick={() => {
                setZThreshold(2.5);
                setPage(1);
              }}
            >
              Severe (2.5σ)
            </Button>
            <Button
              variant={zThreshold === 3.0 ? "default" : "outline"}
              size="sm"
              onClick={() => {
                setZThreshold(3.0);
                setPage(1);
              }}
            >
              Extreme (3σ)
            </Button>
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
                <TableHead>Date</TableHead>
                <TableHead className="text-right">Actual</TableHead>
                <TableHead className="text-right">Expected</TableHead>
                <TableHead className="text-right">Z-score</TableHead>
                <TableHead>Direction</TableHead>
                <TableHead>Severity</TableHead>
              </TableRow>
            </TableHeader>

            <TableBody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell colSpan={8}>
                      <Skeleton className="h-12 w-full" />
                    </TableCell>
                  </TableRow>
                ))
              ) : items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="py-12 text-center">
                    <div className="flex flex-col items-center gap-2">
                      <AlertTriangle className="h-8 w-8 text-muted-foreground" />
                      <p className="text-sm text-muted-foreground">
                        No anomalies detected at this threshold.
                      </p>
                    </div>
                  </TableCell>
                </TableRow>
              ) : (
                items.map((row, idx) => (
                  <AnomalyRow key={`${row.product_id}-${row.sales_date}-${idx}`} row={row} />
                ))
              )}
            </TableBody>
          </Table>
        </div>

        {/* Pagination */}
        {data && data.pages > 1 && (
          <div className="mt-4 flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Page {data.page} of {data.pages} · {data.total} anomalies
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
function AnomalyRow({ row }: { row: AnomalyItem }) {
  const imageUrl = resolveImageUrl(row.image_url);
  const isSpike = row.direction === "spike";

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
        <div className="font-mono text-xs text-muted-foreground">{row.sku}</div>
      </TableCell>

      <TableCell className="text-sm text-muted-foreground">
        {fmtDate(row.sales_date)}
      </TableCell>

      <TableCell className="text-right tabular-nums font-medium">
        {row.quantity}
      </TableCell>

      <TableCell className="text-right tabular-nums text-muted-foreground">
        {row.expected_quantity.toFixed(2)}
      </TableCell>

      <TableCell
        className={cn(
          "text-right tabular-nums font-mono",
          isSpike
            ? "text-green-600 dark:text-green-400"
            : "text-red-600 dark:text-red-400",
        )}
      >
        {row.z_score > 0 ? "+" : ""}
        {row.z_score.toFixed(2)}
      </TableCell>

      <TableCell>
        <Badge
          variant="outline"
          className={cn(
            "gap-1 text-xs",
            isSpike
              ? "border-green-500/50 text-green-700 dark:text-green-400"
              : "border-red-500/50 text-red-700 dark:text-red-400",
          )}
        >
          {isSpike ? (
            <ArrowUp className="h-3 w-3" />
          ) : (
            <ArrowDown className="h-3 w-3" />
          )}
          {row.direction}
        </Badge>
      </TableCell>

      <TableCell>{severityBadge(row.severity)}</TableCell>
    </TableRow>
  );
}
