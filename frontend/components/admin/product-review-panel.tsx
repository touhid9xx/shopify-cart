"use client";

import { useState } from "react";
import { Check, ChevronDown, ShieldAlert, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

import {
  useApproveProduct,
  useRecategorizeProduct,
  useRejectProduct,
} from "@/hooks/use-admin-products";
import { useCategoryTree } from "@/hooks/use-categories";
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
export function ProductReviewPanel({
  product,
}: {
  product: ProductReadWithReview;
}) {
  const [approveOpen, setApproveOpen] = useState(false);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [recatOpen, setRecatOpen] = useState(false);

  // Only show actions when PENDING — otherwise render a locked info card
  if (product.review_status !== "pending") {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <ShieldAlert className="h-5 w-5 text-muted-foreground" />
            Review Actions
          </CardTitle>
          <CardDescription>
            No actions available — this product has already been{" "}
            <span className="font-medium">{product.review_status}</span>.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Review Actions</CardTitle>
          <CardDescription>
            This product is awaiting your decision. Choose an action below.
          </CardDescription>
        </CardHeader>

        <CardContent className="flex flex-col gap-2">
          <Button
            className="w-full justify-start"
            onClick={() => setApproveOpen(true)}
          >
            <Check className="mr-2 h-4 w-4" />
            Approve as-is
          </Button>

          <Button
            variant="outline"
            className="w-full justify-start"
            onClick={() => setRecatOpen(true)}
          >
            <ChevronDown className="mr-2 h-4 w-4" />
            Recategorize &amp; approve
          </Button>

          <Button
            variant="outline"
            className="w-full justify-start text-destructive hover:text-destructive"
            onClick={() => setRejectOpen(true)}
          >
            <X className="mr-2 h-4 w-4" />
            Reject with reason
          </Button>
        </CardContent>
      </Card>

      <ApproveDialog
        product={product}
        open={approveOpen}
        onOpenChange={setApproveOpen}
      />
      <RejectDialog
        product={product}
        open={rejectOpen}
        onOpenChange={setRejectOpen}
      />
      <RecategorizeDialog
        product={product}
        open={recatOpen}
        onOpenChange={setRecatOpen}
      />
    </>
  );
}

// ══════════════════════════════════════════════════════════════
// Approve Dialog
// ══════════════════════════════════════════════════════════════
function ApproveDialog({
  product,
  open,
  onOpenChange,
}: {
  product: ProductReadWithReview;
  open: boolean;
  onOpenChange: (o: boolean) => void;
}) {
  const [notes, setNotes] = useState("");
  const approve = useApproveProduct();

  const handleSubmit = () => {
    approve.mutate(
      { id: product.id, payload: { notes: notes.trim() || null } },
      {
        onSuccess: () => {
          setNotes("");
          onOpenChange(false);
        },
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Approve product?</DialogTitle>
          <DialogDescription>
            &ldquo;{product.name}&rdquo; will be published to customers with
            its current category assignment.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2 py-2">
          <Label htmlFor="approve-notes">Notes (optional)</Label>
          <Textarea
            id="approve-notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="e.g., Verified against supplier catalog"
            rows={2}
            disabled={approve.isPending}
          />
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={approve.isPending}
          >
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={approve.isPending}>
            {approve.isPending ? "Approving…" : "Approve"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ══════════════════════════════════════════════════════════════
// Reject Dialog
// ══════════════════════════════════════════════════════════════
function RejectDialog({
  product,
  open,
  onOpenChange,
}: {
  product: ProductReadWithReview;
  open: boolean;
  onOpenChange: (o: boolean) => void;
}) {
  const [reason, setReason] = useState("");
  const reject = useRejectProduct();

  const handleSubmit = () => {
    if (reason.trim().length < 3) return;
    reject.mutate(
      { id: product.id, payload: { reason: reason.trim() } },
      {
        onSuccess: () => {
          setReason("");
          onOpenChange(false);
        },
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Reject product</DialogTitle>
          <DialogDescription>
            &ldquo;{product.name}&rdquo; will be hidden from customers. The
            reason is stored in the audit trail.
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
            onClick={() => onOpenChange(false)}
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
  open,
  onOpenChange,
}: {
  product: ProductReadWithReview;
  open: boolean;
  onOpenChange: (o: boolean) => void;
}) {
  const [categoryId, setCategoryId] = useState<number | null>(null);
  const [notes, setNotes] = useState("");
  const recat = useRecategorizeProduct();
  const { data: tree } = useCategoryTree();
  const flatCats = tree ? flattenCategories(tree) : [];

  const handleSubmit = () => {
    if (!categoryId) return;
    recat.mutate(
      {
        id: product.id,
        payload: { category_id: categoryId, notes: notes.trim() || null },
      },
      {
        onSuccess: () => {
          setCategoryId(null);
          setNotes("");
          onOpenChange(false);
        },
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Recategorize &amp; approve</DialogTitle>
          <DialogDescription>
            Override the current category for &ldquo;{product.name}&rdquo; and
            publish it.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* ML prediction hint */}
          {product.ml_category_slug && (
            <div className="rounded-md border bg-muted/30 p-3 text-sm">
              ML predicted{" "}
              <span className="font-medium">{product.ml_category_slug}</span>{" "}
              <span className="text-xs text-muted-foreground">
                ({confidencePct(product.ml_confidence)})
              </span>
            </div>
          )}

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
            onClick={() => onOpenChange(false)}
            disabled={recat.isPending}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!categoryId || recat.isPending}
          >
            {recat.isPending ? "Saving…" : "Save & approve"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
