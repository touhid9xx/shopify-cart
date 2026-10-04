"use client";

import { Brain, Clock, Sparkles, UserCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { ProductReviewStatus, ProductReadWithReview } from "@/lib/api-types";
import { cn } from "@/lib/utils";

// ══════════════════════════════════════════════════════════════
// Helpers
// ══════════════════════════════════════════════════════════════
function confidencePct(raw: string | null): string {
  if (!raw) return "—";
  const v = parseFloat(raw);
  if (Number.isNaN(v)) return "—";
  return `${Math.round(v * 100)}%`;
}

function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

const STATUS_STYLES: Record<
  ProductReviewStatus,
  { label: string; className: string }
> = {
  pending: {
    label: "Pending review",
    className:
      "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400",
  },
  approved: {
    label: "Approved",
    className:
      "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  },
  rejected: {
    label: "Rejected",
    className:
      "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  },
};

// ══════════════════════════════════════════════════════════════
// Component
// ══════════════════════════════════════════════════════════════
export function ProductMLMetadata({
  product,
}: {
  product: ProductReadWithReview;
}) {
  const status = STATUS_STYLES[product.review_status];
  const hasML =
    product.ml_category_slug !== null || product.ml_confidence !== null;
  const hasReview =
    product.reviewed_by !== null ||
    product.reviewed_at !== null ||
    product.review_notes !== null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Brain className="h-5 w-5 text-primary" />
          ML &amp; Review Metadata
        </CardTitle>
        <CardDescription>
          Classifier prediction and human-in-the-loop audit trail.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Review status badge */}
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-muted-foreground">
            Review status
          </span>
          <span
            className={cn(
              "rounded-full px-2.5 py-0.5 text-xs font-semibold",
              status.className,
            )}
          >
            {status.label}
          </span>
        </div>

        <Separator />

        {/* ML prediction section */}
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            ML Prediction
          </p>
          {hasML ? (
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <p className="text-muted-foreground">Predicted slug</p>
                <p className="mt-0.5 flex items-center gap-1.5 font-medium">
                  <Sparkles className="h-3.5 w-3.5 text-primary" />
                  {product.ml_category_slug ?? "—"}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">Confidence</p>
                <p className="mt-0.5 font-medium">
                  {confidencePct(product.ml_confidence)}
                </p>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              This product was created manually — no ML prediction on record.
            </p>
          )}
        </div>

        <Separator />

        {/* Human review section */}
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Human Review
          </p>
          {hasReview ? (
            <div className="space-y-3 text-sm">
              <div className="flex items-start justify-between gap-3">
                <span className="flex items-center gap-1.5 text-muted-foreground">
                  <UserCheck className="h-3.5 w-3.5" />
                  Reviewed by
                </span>
                <span className="font-medium">
                  {product.reviewed_by !== null
                    ? `Admin #${product.reviewed_by}`
                    : "—"}
                </span>
              </div>
              <div className="flex items-start justify-between gap-3">
                <span className="flex items-center gap-1.5 text-muted-foreground">
                  <Clock className="h-3.5 w-3.5" />
                  Reviewed at
                </span>
                <span className="font-medium">
                  {formatDateTime(product.reviewed_at)}
                </span>
              </div>
              {product.review_notes && (
                <div className="rounded-md border bg-muted/30 p-3">
                  <p className="mb-1 text-xs font-medium text-muted-foreground">
                    Notes
                  </p>
                  <p className="whitespace-pre-wrap text-sm">
                    {product.review_notes}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Not yet reviewed.
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
