"use client";

import { Minus, Plus } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useAdjustInventory } from "@/hooks/use-admin-inventory";
import { cn } from "@/lib/utils";
import type { InventoryWithProduct } from "@/lib/api-types";

interface Props {
  item: InventoryWithProduct | null;
  onClose: () => void;
}

export function InventoryAdjustDialog({ item, onClose }: Props) {
  const [delta, setDelta] = useState("");
  const [reason, setReason] = useState("");

  const adjust = useAdjustInventory();
  const deltaNum = Number(delta);
  const valid =
    delta.trim() !== "" &&
    Number.isInteger(deltaNum) &&
    deltaNum !== 0 &&
    item !== null &&
    item.quantity + deltaNum >= 0;

  // Reset form when dialog opens with new item
  useEffect(() => {
    if (item) {
      setDelta("");
      setReason("");
    }
  }, [item]);

  const handleSubmit = () => {
    if (!item || !valid) return;
    adjust.mutate(
      {
        product_id: item.product_id,
        location: item.location,
        delta: deltaNum,
        reason: reason.trim() || null,
      },
      { onSuccess: onClose },
    );
  };

  const preview = item && Number.isInteger(deltaNum) ? item.quantity + deltaNum : item?.quantity ?? 0;
  const previewColor =
    preview < 0
      ? "text-destructive"
      : preview === 0
        ? "text-red-600 dark:text-red-400"
        : preview <= (item?.low_stock_threshold ?? 0)
          ? "text-amber-600 dark:text-amber-400"
          : "text-green-600 dark:text-green-400";

  return (
    <Dialog open={item !== null} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Adjust stock</DialogTitle>
          <DialogDescription>
            {item?.product.name} at <span className="font-mono">{item?.location}</span>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Current state */}
          {item && (
            <div className="rounded-md border bg-muted/30 p-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Current quantity</span>
                <span className="font-semibold tabular-nums">{item.quantity}</span>
              </div>
              <div className="mt-1 flex items-center justify-between">
                <span className="text-muted-foreground">Low-stock threshold</span>
                <span className="tabular-nums">{item.low_stock_threshold}</span>
              </div>
            </div>
          )}

          {/* Delta input */}
          <div className="space-y-2">
            <Label htmlFor="adjust-delta">Adjustment</Label>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="icon"
                onClick={() => setDelta(String((Number(delta) || 0) - 1))}
                disabled={adjust.isPending}
                aria-label="Decrease"
              >
                <Minus className="h-4 w-4" />
              </Button>
              <Input
                id="adjust-delta"
                type="number"
                step={1}
                value={delta}
                onChange={(e) => setDelta(e.target.value)}
                placeholder="e.g. 10 or -5"
                className="text-center tabular-nums"
                disabled={adjust.isPending}
                autoFocus
              />
              <Button
                type="button"
                variant="outline"
                size="icon"
                onClick={() => setDelta(String((Number(delta) || 0) + 1))}
                disabled={adjust.isPending}
                aria-label="Increase"
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Positive adds stock, negative removes. Cannot go below 0.
            </p>
          </div>

          {/* Preview */}
          {item && delta.trim() !== "" && (
            <div className="rounded-md border p-3 text-sm">
              <span className="text-muted-foreground">New quantity: </span>
              <span className={cn("font-semibold tabular-nums", previewColor)}>
                {preview}
              </span>
              {preview < 0 && (
                <p className="mt-1 text-xs text-destructive">
                  ❌ Would reduce stock below 0 — invalid.
                </p>
              )}
            </div>
          )}

          {/* Reason */}
          <div className="space-y-2">
            <Label htmlFor="adjust-reason">Reason (optional)</Label>
            <Textarea
              id="adjust-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Restock from supplier, damage write-off…"
              rows={2}
              disabled={adjust.isPending}
            />
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={onClose}
            disabled={adjust.isPending}
          >
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!valid || adjust.isPending}>
            {adjust.isPending ? "Saving…" : "Apply adjustment"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
