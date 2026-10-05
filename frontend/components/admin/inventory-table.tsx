"use client";

import { ImageOff, Package, Plus } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAdminInventory } from "@/hooks/use-admin-inventory";
import { formatMoney } from "@/lib/formatters";
import { cn, resolveImageUrl } from "@/lib/utils";
import type { InventoryWithProduct, ListInventoryParams } from "@/lib/api-types";

interface Props {
  params: ListInventoryParams;
  onAdjust: (item: InventoryWithProduct) => void;
}

export function InventoryTable({ params, onAdjust }: Props) {
  const { data, isLoading } = useAdminInventory(params);
  const items = data?.items ?? [];

  return (
    <div className="rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[60px]">Image</TableHead>
            <TableHead>Product</TableHead>
            <TableHead>SKU</TableHead>
            <TableHead>Location</TableHead>
            <TableHead className="text-right">Quantity</TableHead>
            <TableHead className="text-right">Threshold</TableHead>
            <TableHead className="text-right">Price</TableHead>
            <TableHead className="w-[100px] text-right">Actions</TableHead>
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
                  <Package className="h-8 w-8 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">
                    No inventory rows match your filters.
                  </p>
                </div>
              </TableCell>
            </TableRow>
          ) : (
            items.map((row) => (
              <InventoryRow key={row.id} row={row} onAdjust={onAdjust} />
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );
}

function InventoryRow({
  row,
  onAdjust,
}: {
  row: InventoryWithProduct;
  onAdjust: (item: InventoryWithProduct) => void;
}) {
  const imageUrl = resolveImageUrl(row.product.image_url);

  return (
    <TableRow>
      <TableCell>
        <div className="h-10 w-10 overflow-hidden rounded bg-muted">
          {imageUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={imageUrl}
              alt={row.product.name}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full items-center justify-center">
              <ImageOff className="h-4 w-4 text-muted-foreground" />
            </div>
          )}
        </div>
      </TableCell>

      <TableCell className="font-medium">
        {row.product.name}
        {!row.product.is_active && (
          <Badge variant="outline" className="ml-2 text-xs">
            Inactive
          </Badge>
        )}
      </TableCell>

      <TableCell className="font-mono text-xs">{row.product.sku}</TableCell>

      <TableCell className="text-sm text-muted-foreground">
        {row.location}
      </TableCell>

      <TableCell className="text-right">
        <span
          className={cn(
            "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold tabular-nums",
            row.quantity === 0
              ? "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400"
              : row.is_low_stock
                ? "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400"
                : "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
          )}
        >
          {row.quantity}
        </span>
      </TableCell>

      <TableCell className="text-right text-sm text-muted-foreground tabular-nums">
        {row.low_stock_threshold}
      </TableCell>

      <TableCell className="text-right text-sm tabular-nums">
        {formatMoney(row.product.price)}
      </TableCell>

      <TableCell className="text-right">
        <Button size="sm" variant="outline" onClick={() => onAdjust(row)}>
          <Plus className="mr-1 h-3.5 w-3.5" />
          Adjust
        </Button>
      </TableCell>
    </TableRow>
  );
}
