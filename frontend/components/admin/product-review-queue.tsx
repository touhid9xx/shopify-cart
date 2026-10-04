"use client";

import Link from "next/link";
import { useState } from "react";
import {
  Check,
  ChevronDown,
  ImageOff,
  Package,
  Sparkles,
  X,
} from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import {
  usePendingReviewProducts,
  useApproveProduct,
  useRejectProduct,
  useRecategorizeProduct,
} from "@/hooks/use-admin-products";
import { useCategoryTree } from "@/hooks/use-categories";
import { formatMoney } from "@/lib/formatters";
import { resolveImageUrl } from "@/lib/utils";
import { cn } from "@/lib/utils";
import type { ProductReadWithReview } from "@/lib/api-types";

// ══════════════════════════════════════════════════════════════
// Helpers
// ══════════════════════════════════════════════════════════════
interface CategoryNode {
  id: number;
  name: string;
  children?: CategoryNode[];
}

function flattenCategories(
  nodes: CategoryNode[],
  depth = 0,
): { id: number; name: string; depth: number }[] {
  const out: { id: number; name: string; depth: number }[] = [];
  for (const n of nodes) {
    out.push({ id: n.id, name: n.name, depth });
    if (n.children?.length) {
      out.push(...flattenCategories(n.children, depth + 1));
    }
  }
  return out;
}

function confidencePct(raw: string | null): string {
  if (!raw) return "—";
  const v = parseFloat(raw);
  if (Number.isNaN(v)) return "—";
  return `${Math.round(v * 100)}%`;
}

// ══════════════════════════════════════════════════════════════
// Main Component
// ══════════════════════════════════════════════════════════════
export function ProductReviewQueue() {
  const [page, setPage] = useState(1);

  // Action dialogs
  const [rejectTarget, setRejectTarget] =
    useState<ProductReadWithReview | null>(null);
  const [recatTarget, setRecatTarget] =
    useState<ProductReadWithReview | null>(null);

  const PAGE_SIZE = 20;
  const { data, isLoading, isFetching } = usePendingReviewProducts({
    page,
    size: PAGE_SIZE,
  });

  const products = data?.items ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-primary" />
            Review Queue
          </h1>
          <p className="text-sm text-muted-foreground">
            ML-classified products awaiting your approval.
            {data ? ` ${data.total} pending.` : ""}
          </p>
        </div>
        <Link
          href="/dashboard/products"
          className={cn(buttonVariants({ variant: "outline" }))}
        >
          View all products
        </Link>
      </div>

      {/* Empty state */}
      {!isLoading && products.length === 0 && (
        <div className="rounded-lg border border-dashed p-12 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30">
            <Check className="h-7 w-7 text-green-600 dark:text-green-400" />
          </div>
          <h2 className="text-lg font-semibold">All caught up!</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            No products pending review right now.
          </p>
        </div>
      )}

      {/* Cards list */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-32 w-full rounded-lg" />
          ))}
        </div>
      ) : (
        <div className="space-y-4">
          {products.map((p) => (
            <ReviewCard
              key={p.id}
              product={p}
              onReject={() => setRejectTarget(p)}
              onRecategorize={() => setRecatTarget(p)}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {data && data.pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Page {data.page} of {data.pages} · {data.total} pending
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

      {/* Reject dialog */}
      <RejectDialog
        product={rejectTarget}
        onClose={() => setRejectTarget(null)}
      />

      {/* Recategorize dialog */}
      <RecategorizeDialog
        product={recatTarget}
        onClose={() => setRecatTarget(null)}
      />
    </div>
  );
}

// ══════════════════════════════════════════════════════════════
// Review Card
// ══════════════════════════════════════════════════════════════
function ReviewCard({
  product,
  onReject,
  onRecategorize,
}: {
  product: ProductReadWithReview;
  onReject: () => void;
  onRecategorize: () => void;
}) {
  const approve = useApproveProduct();
  const imageUrl = resolveImageUrl(product.image_url);
  const [approveOpen, setApproveOpen] = useState(false);

  return (
    <div className="rounded-lg border p-4 md:p-5">
      <div className="flex flex-col gap-4 md:flex-row md:items-start">
        {/* Thumbnail */}
        <div className="h-24 w-24 shrink-0 overflow-hidden rounded bg-muted">
          {imageUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={imageUrl}
              alt={product.name}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full items-center justify-center">
              <ImageOff className="h-8 w-8 text-muted-foreground" />
            </div>
          )}
        </div>

        {/* Info */}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <Link
                href={`/dashboard/products/${product.id}/edit`}
                className="font-semibold hover:underline"
              >
                {product.name}
              </Link>
              <p className="mt-0.5 text-xs font-mono text-muted-foreground">
                {product.sku}
              </p>
            </div>
            <Badge variant="secondary">{formatMoney(product.price)}</Badge>
          </div>

          <Separator className="my-3" />

          {/* ML vs current category */}
          <div className="grid gap-3 text-sm md:grid-cols-2">
            <div>
              <p className="text-xs uppercase text-muted-foreground">
                ML Prediction
              </p>
              <p className="mt-1 flex items-center gap-2">
                <Sparkles className="h-3.5 w-3.5 text-primary" />
                <span className="font-medium">
                  {product.ml_category_slug ?? "—"}
                </span>
                <span className="text-xs text-muted-foreground">
                  ({confidencePct(product.ml_confidence)})
                </span>
              </p>
            </div>
            <div>
              <p className="text-xs uppercase text-muted-foreground">
                Assigned Category
              </p>
              <p className="mt-1 font-medium">
                {product.category?.name ?? "—"}
              </p>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex shrink-0 flex-col gap-2 md:w-40">
          <Button
            size="sm"
            onClick={() => setApproveOpen(true)}
            disabled={approve.isPending}
          >
            <Check className="mr-1 h-4 w-4" />
            Approve
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={onRecategorize}
          >
            <ChevronDown className="mr-1 h-4 w-4" />
            Recategorize
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="text-destructive hover:text-destructive"
            onClick={onReject}
          >
            <X className="mr-1 h-4 w-4" />
            Reject
          </Button>
        </div>
      </div>

      {/* Approve confirm dialog */}
      <Dialog open={approveOpen} onOpenChange={setApproveOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Approve product?</DialogTitle>
            <DialogDescription>
              This will publish the product to customers with the current
              category assignment.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setApproveOpen(false)}
              disabled={approve.isPending}
            >
              Cancel
            </Button>
            <Button
              onClick={() =>
                approve.mutate(
                  { id: product.id, payload: {} },
                  { onSuccess: () => setApproveOpen(false) },
                )
              }
              disabled={approve.isPending}
            >
              {approve.isPending ? "Approving…" : "Approve"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════
// Reject Dialog
// ══════════════════════════════════════════════════════════════
function RejectDialog({
  product,
  onClose,
}: {
  product: ProductReadWithReview | null;
  onClose: () => void;
}) {
  const [reason, setReason] = useState("");
  const reject = useRejectProduct();

  const handleClose = () => {
    setReason("");
    onClose();
  };

  const handleSubmit = () => {
    if (!product || reason.trim().length < 3) return;
    reject.mutate(
      { id: product.id, payload: { reason: reason.trim() } },
      { onSuccess: handleClose },
    );
  };

  return (
    <Dialog open={product !== null} onOpenChange={(o) => !o && handleClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Reject product</DialogTitle>
          <DialogDescription>
            {product?.name} will be hidden from customers. Please provide a
            reason (stored in audit log).
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2 py-2">
          <Label htmlFor="reject-reason">Reason</Label>
          <Textarea
            id="reject-reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="e.g., Blurry image, wrong ML prediction, duplicate SKU"
            rows={3}
            disabled={reject.isPending}
          />
          <p className="text-xs text-muted-foreground">
            Minimum 3 characters.
          </p>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={reject.isPending}
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleSubmit}
            disabled={reason.trim().length < 3 || reject.isPending}
          >
            {reject.isPending ? "Rejecting…" : "Reject product"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ══════════════════════════════════════════════════════════════
// Recategorize Dialog
// ══════════════════════════════════════════════════════════════
function RecategorizeDialog({
  product,
  onClose,
}: {
  product: ProductReadWithReview | null;
  onClose: () => void;
}) {
  const [categoryId, setCategoryId] = useState<number | null>(null);
  const [notes, setNotes] = useState("");
  const recat = useRecategorizeProduct();
  const { data: tree } = useCategoryTree();
  const flatCats = tree ? flattenCategories(tree) : [];

  const handleClose = () => {
    setCategoryId(null);
    setNotes("");
    onClose();
  };

  const handleSubmit = () => {
    if (!product || !categoryId) return;
    recat.mutate(
      {
        id: product.id,
        payload: {
          category_id: categoryId,
          notes: notes.trim() || null,
        },
      },
      { onSuccess: handleClose },
    );
  };

  return (
    <Dialog open={product !== null} onOpenChange={(o) => !o && handleClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Recategorize and approve</DialogTitle>
          <DialogDescription>
            Override the ML category for {product?.name} and publish.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* ML prediction display */}
          {product?.ml_category_slug && (
            <div className="rounded-md border bg-muted/30 p-3 text-sm">
              <p className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-primary" />
                ML predicted{" "}
                <span className="font-medium">
                  {product.ml_category_slug}
                </span>
                <span className="text-xs text-muted-foreground">
                  ({confidencePct(product.ml_confidence)})
                </span>
              </p>
            </div>
          )}

          {/* Category select */}
          <div className="space-y-2">
            <Label>New category</Label>
            <Select
              value={categoryId ? String(categoryId) : ""}
              onValueChange={(v) => setCategoryId(Number(v))}
              disabled={recat.isPending}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select a category" />
              </SelectTrigger>
              <SelectContent>
                {flatCats.map((c) => (
                  <SelectItem key={c.id} value={String(c.id)}>
                    {"\u00A0".repeat(c.depth * 2)}
                    {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Notes */}
          <div className="space-y-2">
            <Label htmlFor="recat-notes">Notes (optional)</Label>
            <Textarea
              id="recat-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g., ML confused accessory with clothing"
              rows={2}
              disabled={recat.isPending}
            />
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={recat.isPending}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!categoryId || recat.isPending}
          >
            {recat.isPending ? "Saving…" : "Save and approve"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
