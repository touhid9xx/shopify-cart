"use client";

import { Tag } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { CategoryCount } from "@/lib/api-types";

interface Props {
  categories: CategoryCount[];
  isLoading: boolean;
}

function humanize(slug: string): string {
  return slug
    .split("-")
    .map((s) => s.charAt(0).toUpperCase() + s.slice(1))
    .join(" ");
}

export function MlCategoryBars({ categories, isLoading }: Props) {
  const max = categories.length
    ? Math.max(...categories.map((c) => c.product_count))
    : 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Tag className="h-5 w-5 text-primary" />
          Top Categories by ML
        </CardTitle>
        <CardDescription>
          Categories with the most classified products (top 10).
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : categories.length === 0 ? (
          <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">
            No category data.
          </div>
        ) : (
          <ul className="space-y-3">
            {categories.map((cat) => {
              const widthPct = max > 0 ? (cat.product_count / max) * 100 : 0;
              return (
                <li key={cat.category_slug}>
                  <div className="mb-1 flex items-center justify-between text-sm">
                    <span className="font-medium">
                      {humanize(cat.category_slug)}
                    </span>
                    <span className="text-muted-foreground tabular-nums">
                      {cat.product_count}
                    </span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full bg-primary transition-all"
                      style={{ width: `${widthPct}%` }}
                    />
                  </div>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    avg confidence {Math.round(cat.avg_confidence * 100)}%
                  </p>
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
